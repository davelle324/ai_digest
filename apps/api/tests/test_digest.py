"""Digest and email tests — no real emails are sent."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.digest import build_html_email, run_daily_digest, run_weekly_digest, send_digest
from app.models import Article, DigestLog, Source, Subscriber


# ── Helpers ──────────────────────────────────────────────────────────────────


def _source(db):
    s = Source(name="Test Feed", url="https://test.com", source_type="rss", enabled=True)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _article(db, source, title="AI News", url="https://test.com/1", with_summary=True, age_hours=1):
    a = Article(
        source_id=source.id,
        title=title,
        url=url,
        excerpt="Short excerpt.",
        summary="Full AI summary." if with_summary else None,
        fetched_at=datetime.now(timezone.utc) - timedelta(hours=age_hours),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _subscriber(db, email="reader@example.com", cadence="daily", confirmed=True, token="tok-abc"):
    s = Subscriber(
        email=email,
        cadence=cadence,
        confirmed=confirmed,
        confirmation_token=token,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ── build_html_email ──────────────────────────────────────────────────────────


def test_build_html_contains_period(db):
    src = _source(db)
    art = _article(db, src)
    html = build_html_email([art], "Daily")
    assert "AI Digest — Daily" in html


def test_build_html_contains_title_and_link(db):
    src = _source(db)
    art = _article(db, src)
    html = build_html_email([art], "Weekly")
    assert "AI News" in html
    assert "https://test.com/1" in html


def test_build_html_shows_summary_over_excerpt(db):
    src = _source(db)
    art = _article(db, src, with_summary=True)
    html = build_html_email([art], "Daily")
    assert "Full AI summary." in html
    assert "Short excerpt." not in html


def test_build_html_falls_back_to_excerpt(db):
    src = _source(db)
    art = _article(db, src, with_summary=False)
    html = build_html_email([art], "Daily")
    assert "Short excerpt." in html


def test_build_html_escapes_xss_in_title(db):
    src = _source(db)
    art = Article(
        source_id=src.id,
        title='<script>alert("xss")</script>',
        url="https://test.com/xss",
        excerpt="Normal content",
    )
    db.add(art)
    db.commit()
    db.refresh(art)

    html = build_html_email([art], "Daily")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_build_html_escapes_quotes_in_url(db):
    """html.escape prevents attribute injection via unescaped quotes in the URL."""
    src = _source(db)
    art = Article(
        source_id=src.id,
        title="Normal Title",
        url='https://test.com/?x=1" onclick="evil()',
        excerpt="content",
    )
    db.add(art)
    db.commit()
    db.refresh(art)

    html = build_html_email([art], "Daily")
    # The injected quote must be escaped so it cannot break out of the href attribute.
    assert 'onclick="evil()' not in html
    assert "&quot;" in html


def test_build_html_has_unsubscribe_placeholder(db):
    src = _source(db)
    art = _article(db, src)
    html = build_html_email([art], "Daily")
    assert "{token}" in html  # replaced later in send_digest


def test_build_html_empty_articles(db):
    html = build_html_email([], "Daily")
    assert "AI Digest — Daily" in html
    assert "Unsubscribe" in html


# ── send_digest ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_digest_no_resend_key_logs_failure(db):
    """When RESEND_API_KEY is empty, no email is sent and DigestLog records failure."""
    src = _source(db)
    art = _article(db, src)
    sub = _subscriber(db)

    # RESEND_API_KEY is "" from conftest — the function should skip sending
    await send_digest(sub, [art], db)

    log = db.query(DigestLog).filter(DigestLog.subscriber_id == sub.id).first()
    assert log is not None
    assert log.status == "failed"
    assert "RESEND_API_KEY" in (log.error or "")
    assert log.article_count == 1


@pytest.mark.asyncio
async def test_send_digest_with_mocked_resend(db):
    """With a mocked Resend, digest is marked sent and the email content is correct."""
    src = _source(db)
    art = _article(db, src)
    sub = _subscriber(db, token="my-unsub-token")

    mock_send = MagicMock(return_value={"id": "mock-email-id"})
    with (
        patch("app.digest.RESEND_API_KEY", "test-key"),
        patch("app.digest.resend.Emails.send", mock_send),
    ):
        await send_digest(sub, [art], db)

    mock_send.assert_called_once()
    payload = mock_send.call_args[0][0]
    assert payload["to"] == "reader@example.com"
    assert "AI Digest" in payload["subject"]
    # Token must be substituted in the HTML
    assert "my-unsub-token" in payload["html"]
    assert "{token}" not in payload["html"]

    log = db.query(DigestLog).filter(DigestLog.subscriber_id == sub.id).first()
    assert log.status == "sent"


@pytest.mark.asyncio
async def test_send_digest_handles_resend_error(db):
    """If Resend throws, DigestLog records the failure without crashing."""
    src = _source(db)
    art = _article(db, src)
    sub = _subscriber(db, email="err@example.com", token="err-token")

    with (
        patch("app.digest.RESEND_API_KEY", "test-key"),
        patch("app.digest.resend.Emails.send", side_effect=Exception("API error")),
    ):
        await send_digest(sub, [art], db)  # must not raise

    log = db.query(DigestLog).filter(DigestLog.subscriber_id == sub.id).first()
    assert log.status == "failed"
    assert "API error" in (log.error or "")


# ── run_daily_digest ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_daily_digest_no_articles(db):
    _subscriber(db)
    with patch("app.digest.resend.Emails.send") as mock_send:
        await run_daily_digest(db)
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_run_daily_digest_no_subscribers(db):
    src = _source(db)
    _article(db, src)
    with patch("app.digest.resend.Emails.send") as mock_send:
        await run_daily_digest(db)
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_run_daily_digest_only_confirmed(db):
    src = _source(db)
    _article(db, src)
    confirmed = _subscriber(db, email="yes@example.com", cadence="daily", confirmed=True, token="t1")
    _subscriber(db, email="no@example.com", cadence="daily", confirmed=False, token="t2")

    sent_to = []

    async def fake_send(subscriber, articles, session):
        sent_to.append(subscriber.email)

    with patch("app.digest.send_digest", side_effect=fake_send):
        await run_daily_digest(db)

    assert confirmed.email in sent_to
    assert "no@example.com" not in sent_to


@pytest.mark.asyncio
async def test_run_daily_digest_skips_unsubscribed(db):
    src = _source(db)
    _article(db, src)
    sub = _subscriber(db, token="tok-unsub")
    sub.unsubscribed_at = datetime.now(timezone.utc)
    db.commit()

    with patch("app.digest.resend.Emails.send") as mock_send:
        await run_daily_digest(db)

    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_run_daily_digest_skips_old_articles(db):
    src = _source(db)
    _article(db, src, age_hours=48)  # older than 24h cutoff
    _subscriber(db, cadence="daily", token="tok-old")

    with patch("app.digest.resend.Emails.send") as mock_send:
        await run_daily_digest(db)

    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_run_weekly_digest_only_weekly_subscribers(db):
    src = _source(db)
    _article(db, src)
    _subscriber(db, email="daily@example.com", cadence="daily", token="t-daily")
    _subscriber(db, email="weekly@example.com", cadence="weekly", token="t-weekly")

    sent_to = []

    async def fake_send(subscriber, articles, session):
        sent_to.append(subscriber.email)

    with patch("app.digest.send_digest", side_effect=fake_send):
        await run_weekly_digest(db)

    assert "weekly@example.com" in sent_to
    assert "daily@example.com" not in sent_to
