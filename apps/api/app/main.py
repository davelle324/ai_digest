import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from math import ceil

import resend
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import CATEGORY_LABELS, CATEGORY_ORDER, SessionLocal, get_db, init_db
from app.digest import run_daily_digest, run_weekly_digest
from app.fetcher import fetch_all_sources
from app.models import Article, Source, Subscriber
from app.scheduler import scheduler, setup_scheduler
from app.schemas import ArticleListOut, ArticleOut, SourceOut, SubscribeIn, SubscribeOut, StatsOut
from app.summarizer import summarize

logger = logging.getLogger(__name__)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
SITE_URL = os.getenv("SITE_URL", "http://localhost:3000")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "digest@yourdomain.com")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}"


async def require_admin(x_admin_key: str = Header(default="")):
    if not ADMIN_SECRET or x_admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    setup_scheduler(app)
    scheduler.start()
    logger.info("Scheduler started")
    yield
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


app = FastAPI(title="AI Digest API", version="0.1.0", lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


@app.get("/sources", response_model=list[SourceOut])
async def list_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).filter(Source.enabled.is_(True)).all()
    key = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    return sorted(sources, key=lambda s: key.get(s.category or "", 99))


@app.get("/sources/categories")
async def list_categories():
    return [{"key": k, "label": v} for k, v in CATEGORY_LABELS.items()]


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------


@app.get("/articles", response_model=ArticleListOut)
async def list_articles(
    page: int = 1,
    limit: int = 20,
    source_id: int | None = None,
    category: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Article).join(Article.source)
    if source_id is not None:
        query = query.filter(Article.source_id == source_id)
    if category is not None:
        query = query.filter(Source.category == category)
    if q:
        term = f"%{q}%"
        query = query.filter(Article.title.ilike(term) | Article.excerpt.ilike(term))
    total = query.count()
    pages = max(1, ceil(total / limit))
    items = (
        query.order_by(Article.fetched_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return ArticleListOut(items=items, total=total, page=page, pages=pages)


@app.get("/stats", response_model=StatsOut)
async def get_stats(db: Session = Depends(get_db)):
    total_articles = db.query(Article).count()
    total_sources = db.query(Source).filter(Source.enabled.is_(True)).count()
    total_subscribers = db.query(Subscriber).filter(Subscriber.confirmed.is_(True)).filter(Subscriber.unsubscribed_at.is_(None)).count()

    per_source = (
        db.query(Source.name, func.count(Article.id).label("count"))
        .join(Article, Article.source_id == Source.id)
        .group_by(Source.id)
        .order_by(func.count(Article.id).desc())
        .all()
    )

    per_category = (
        db.query(Source.category, func.count(Article.id).label("count"))
        .join(Article, Article.source_id == Source.id)
        .filter(Source.category.isnot(None))
        .group_by(Source.category)
        .all()
    )

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    daily_rows = (
        db.query(func.date(Article.fetched_at).label("date"), func.count(Article.id).label("count"))
        .filter(Article.fetched_at >= cutoff)
        .group_by(func.date(Article.fetched_at))
        .all()
    )
    daily_map = {str(row.date): row.count for row in daily_rows}
    per_day = [
        {"date": str((datetime.now(timezone.utc) - timedelta(days=i)).date()), "count": 0}
        for i in range(29, -1, -1)
    ]
    for entry in per_day:
        entry["count"] = daily_map.get(entry["date"], 0)

    return StatsOut(
        total_articles=total_articles,
        total_sources=total_sources,
        total_subscribers=total_subscribers,
        articles_per_source=[{"name": r.name, "count": r.count} for r in per_source],
        articles_per_category=[
            {"category": r.category, "label": CATEGORY_LABELS.get(r.category, r.category), "count": r.count}
            for r in per_category
        ],
        articles_per_day=per_day,
    )


@app.get("/articles/{article_id}", response_model=ArticleOut)
async def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------


@app.post("/subscribe", response_model=SubscribeOut)
@limiter.limit("5/minute")
async def subscribe(request: Request, body: SubscribeIn, db: Session = Depends(get_db)):
    token = secrets.token_urlsafe(32)
    subscriber = Subscriber(
        email=body.email,
        cadence=body.cadence,
        confirmation_token=token,
    )
    db.add(subscriber)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already subscribed")

    # Send confirmation email if Resend is configured
    if RESEND_API_KEY:
        confirm_url = f"{SITE_URL}/confirm/{token}"
        resend.api_key = RESEND_API_KEY
        try:
            resend.Emails.send(
                {
                    "from": RESEND_FROM,
                    "to": body.email,
                    "subject": "Confirm your AI Digest subscription",
                    "html": (
                        f"<p>Click below to confirm your subscription:</p>"
                        f'<p><a href="{confirm_url}">{confirm_url}</a></p>'
                    ),
                }
            )
        except Exception as exc:
            logger.warning("Failed to send confirmation email to %s: %s", mask_email(body.email), exc)
    else:
        logger.warning("RESEND_API_KEY not set — skipping confirmation email")

    return SubscribeOut(
        message="Subscription created. Please check your email to confirm."
    )


@app.get("/confirm/{token}")
async def confirm_subscription(token: str, db: Session = Depends(get_db)):
    subscriber = db.query(Subscriber).filter(Subscriber.confirmation_token == token).first()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Invalid confirmation token")
    subscriber.confirmed = True
    db.commit()
    return RedirectResponse(url=f"{SITE_URL}?confirmed=1")


@app.get("/unsubscribe/{token}")
async def unsubscribe(token: str, db: Session = Depends(get_db)):
    subscriber = db.query(Subscriber).filter(Subscriber.confirmation_token == token).first()
    if not subscriber:
        raise HTTPException(status_code=404, detail="Invalid token")
    if subscriber.unsubscribed_at is not None:
        return {"message": "Already unsubscribed"}
    subscriber.unsubscribed_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Successfully unsubscribed"}


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


async def _fetch_in_background():
    db = SessionLocal()
    try:
        await fetch_all_sources(db)
    finally:
        db.close()


@app.post("/admin/fetch", dependencies=[Depends(require_admin)])
async def admin_fetch(background_tasks: BackgroundTasks):
    background_tasks.add_task(_fetch_in_background)
    return {"status": "started"}


@app.post("/admin/summarize", dependencies=[Depends(require_admin)])
async def admin_summarize(db: Session = Depends(get_db)):
    articles = (
        db.query(Article)
        .filter(Article.summary.is_(None))
        .filter(Article.excerpt.isnot(None))
        .limit(20)
        .all()
    )
    processed = 0
    for article in articles:
        summary = await summarize(article.excerpt or "")
        if summary:
            article.summary = summary
            db.commit()
            processed += 1
    return {"processed": processed}


@app.post("/admin/digest/daily", dependencies=[Depends(require_admin)])
async def trigger_daily_digest(db: Session = Depends(get_db)):
    await run_daily_digest(db)
    return {"status": "ok"}


@app.post("/admin/digest/weekly", dependencies=[Depends(require_admin)])
async def trigger_weekly_digest(db: Session = Depends(get_db)):
    await run_weekly_digest(db)
    return {"status": "ok"}
