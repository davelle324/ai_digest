import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db import SessionLocal
from app.fetcher import fetch_all_sources
from app.summarizer import summarize

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _scheduled_fetch() -> None:
    db = SessionLocal()
    try:
        count = await fetch_all_sources(db)
        logger.info("Scheduled fetch complete: %d new articles", count)
    except Exception as exc:
        logger.error("Scheduled fetch failed: %s", exc)
    finally:
        db.close()


async def _scheduled_summarize() -> None:
    from app.models import Article

    db = SessionLocal()
    try:
        articles = (
            db.query(Article)
            .filter(Article.summary.is_(None))
            .filter(Article.excerpt.isnot(None))
            .limit(20)
            .all()
        )
        for article in articles:
            summary = await summarize(article.excerpt or "")
            if summary:
                article.summary = summary
                db.commit()
        logger.info("Scheduled summarize: processed %d articles", len(articles))
    except Exception as exc:
        logger.error("Scheduled summarize failed: %s", exc)
    finally:
        db.close()


async def _scheduled_daily_digest() -> None:
    from app.digest import run_daily_digest

    db = SessionLocal()
    try:
        await run_daily_digest(db)
    except Exception as exc:
        logger.error("Daily digest failed: %s", exc)
    finally:
        db.close()


async def _scheduled_weekly_digest() -> None:
    from app.digest import run_weekly_digest

    db = SessionLocal()
    try:
        await run_weekly_digest(db)
    except Exception as exc:
        logger.error("Weekly digest failed: %s", exc)
    finally:
        db.close()


def setup_scheduler(app) -> None:  # noqa: ANN001
    """Register all scheduled jobs on the APScheduler instance."""
    # Fetch news every 2 hours
    scheduler.add_job(
        _scheduled_fetch,
        trigger="interval",
        hours=2,
        id="fetch_news",
        replace_existing=True,
    )

    # Summarize unsummarized articles every 30 minutes
    scheduler.add_job(
        _scheduled_summarize,
        trigger="interval",
        minutes=30,
        id="summarize_articles",
        replace_existing=True,
    )

    # Daily digest at 08:00 UTC
    scheduler.add_job(
        _scheduled_daily_digest,
        trigger="cron",
        hour=8,
        minute=0,
        id="daily_digest",
        replace_existing=True,
    )

    # Weekly digest on Monday at 08:00 UTC
    scheduler.add_job(
        _scheduled_weekly_digest,
        trigger="cron",
        day_of_week="mon",
        hour=8,
        minute=0,
        id="weekly_digest",
        replace_existing=True,
    )

    logger.info("Scheduler jobs registered")
