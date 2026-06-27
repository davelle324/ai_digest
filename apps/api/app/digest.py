import html
import logging
import os
from datetime import datetime, timedelta

import resend
from sqlalchemy.orm import Session

from app.models import Article, DigestLog, Subscriber

logger = logging.getLogger(__name__)


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}"

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "digest@yourdomain.com")
SITE_URL = os.getenv("SITE_URL", "http://localhost:3000")


def build_html_email(articles: list[Article], period: str) -> str:
    """Build an HTML email for the digest."""
    header = f"AI Digest — {period}"

    article_rows = []
    for article in articles:
        content = html.escape(article.summary or article.excerpt or "")
        source_name = html.escape(article.source.name if article.source else "Unknown")
        safe_url = html.escape(article.url, quote=True)
        safe_title = html.escape(article.title)
        article_rows.append(
            f"""
            <div style="margin-bottom: 28px;">
              <h2 style="margin: 0 0 4px;">
                <a href="{safe_url}" style="color: #1a73e8; text-decoration: none;">
                  {safe_title}
                </a>
              </h2>
              <p style="margin: 0 0 8px; font-size: 13px; color: #666;">
                {source_name}
              </p>
              <p style="margin: 0; font-size: 15px; color: #333; line-height: 1.6;">
                {content}
              </p>
              <hr style="margin-top: 24px; border: none; border-top: 1px solid #eee;" />
            </div>
            """
        )

    articles_html = "\n".join(article_rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{header}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
             background: #f9f9f9; margin: 0; padding: 0;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background: #ffffff; border-radius: 8px;
                      box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden;">
          <!-- Header -->
          <tr>
            <td style="background: #111827; padding: 32px 40px;">
              <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">
                {header}
              </h1>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding: 32px 40px;">
              {articles_html}
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding: 24px 40px; background: #f3f4f6;
                       font-size: 13px; color: #6b7280; text-align: center;">
              You are receiving this because you subscribed to AI Digest.<br />
              <a href="{SITE_URL}/unsubscribe/{{token}}"
                 style="color: #6b7280;">Unsubscribe</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


async def send_digest(subscriber: Subscriber, articles: list[Article], db: Session) -> None:
    """Send a digest email to the subscriber and log the result."""
    period = subscriber.cadence.capitalize()
    html = build_html_email(articles, period)
    # Inject the subscriber's confirmation token as the unsubscribe token
    html = html.replace("{token}", subscriber.confirmation_token)

    status = "failed"
    error_msg = None

    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email send for %s", mask_email(subscriber.email))
        status = "failed"
        error_msg = "RESEND_API_KEY not configured"
    else:
        resend.api_key = RESEND_API_KEY
        try:
            resend.Emails.send(
                {
                    "from": RESEND_FROM,
                    "to": subscriber.email,
                    "subject": f"AI Digest — {period} Update",
                    "html": html,
                }
            )
            status = "sent"
        except Exception as exc:
            logger.error("Failed to send digest to %s: %s", mask_email(subscriber.email), exc)
            error_msg = str(exc)

    log = DigestLog(
        subscriber_id=subscriber.id,
        article_count=len(articles),
        status=status,
        error=error_msg,
    )
    db.add(log)
    db.commit()


async def run_daily_digest(db: Session) -> None:
    """Send daily digest to all eligible subscribers."""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    articles = (
        db.query(Article)
        .filter(Article.fetched_at >= cutoff)
        .filter((Article.summary.isnot(None)) | (Article.excerpt.isnot(None)))
        .all()
    )

    if not articles:
        logger.info("Daily digest: no articles to send")
        return

    subscribers = (
        db.query(Subscriber)
        .filter(Subscriber.cadence == "daily")
        .filter(Subscriber.confirmed.is_(True))
        .filter(Subscriber.unsubscribed_at.is_(None))
        .all()
    )

    logger.info(
        "Daily digest: sending %d articles to %d subscribers",
        len(articles),
        len(subscribers),
    )
    for subscriber in subscribers:
        await send_digest(subscriber, articles, db)


async def run_weekly_digest(db: Session) -> None:
    """Send weekly digest to all eligible subscribers."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    articles = (
        db.query(Article)
        .filter(Article.fetched_at >= cutoff)
        .filter((Article.summary.isnot(None)) | (Article.excerpt.isnot(None)))
        .all()
    )

    if not articles:
        logger.info("Weekly digest: no articles to send")
        return

    subscribers = (
        db.query(Subscriber)
        .filter(Subscriber.cadence == "weekly")
        .filter(Subscriber.confirmed.is_(True))
        .filter(Subscriber.unsubscribed_at.is_(None))
        .all()
    )

    logger.info(
        "Weekly digest: sending %d articles to %d subscribers",
        len(articles),
        len(subscribers),
    )
    for subscriber in subscribers:
        await send_digest(subscriber, articles, db)
