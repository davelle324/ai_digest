"""API endpoint tests — no real data stored, no real emails sent."""
from unittest.mock import AsyncMock, patch

import pytest

from app.models import Article, Source, Subscriber


# ── Helpers ──────────────────────────────────────────────────────────────────


def _source(db, name="Test Feed", url="https://test.com/feed", source_type="rss"):
    s = Source(name=name, url=url, source_type=source_type, enabled=True)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _article(db, source, title="Test Article", url="https://test.com/1", excerpt="Excerpt."):
    a = Article(source_id=source.id, title=title, url=url, excerpt=excerpt)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


# ── Health ────────────────────────────────────────────────────────────────────


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── Sources ───────────────────────────────────────────────────────────────────


def test_list_sources_empty(client):
    resp = client.get("/sources")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_sources(client, db):
    _source(db)
    resp = client.get("/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Feed"


def test_list_sources_only_enabled(client, db):
    _source(db, name="Enabled", url="https://a.com")
    disabled = Source(name="Disabled", url="https://b.com", source_type="rss", enabled=False)
    db.add(disabled)
    db.commit()
    resp = client.get("/sources")
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Enabled"


# ── Articles ──────────────────────────────────────────────────────────────────


def test_list_articles_empty(client):
    resp = client.get("/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1
    assert data["pages"] == 1


def test_list_articles(client, db):
    src = _source(db)
    _article(db, src)
    resp = client.get("/articles")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Test Article"
    assert data["items"][0]["source"]["name"] == "Test Feed"


def test_list_articles_filter_by_source(client, db):
    src1 = _source(db, name="A", url="https://a.com")
    src2 = _source(db, name="B", url="https://b.com")
    _article(db, src1, title="From A", url="https://a.com/1")
    _article(db, src2, title="From B", url="https://b.com/1")
    resp = client.get(f"/articles?source_id={src1.id}")
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "From A"


def test_list_articles_pagination(client, db):
    src = _source(db)
    for i in range(25):
        _article(db, src, title=f"Article {i}", url=f"https://test.com/{i}")
    resp = client.get("/articles?page=1&limit=10")
    data = resp.json()
    assert data["total"] == 25
    assert len(data["items"]) == 10
    assert data["pages"] == 3

    resp2 = client.get("/articles?page=3&limit=10")
    assert len(resp2.json()["items"]) == 5


def test_get_article(client, db):
    src = _source(db)
    art = _article(db, src)
    resp = client.get(f"/articles/{art.id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Test Article"


def test_get_article_not_found(client):
    resp = client.get("/articles/99999")
    assert resp.status_code == 404


# ── Subscribe ─────────────────────────────────────────────────────────────────


def test_subscribe_daily(client):
    resp = client.post("/subscribe", json={"email": "daily@example.com", "cadence": "daily"})
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_subscribe_weekly(client):
    resp = client.post("/subscribe", json={"email": "weekly@example.com", "cadence": "weekly"})
    assert resp.status_code == 200


def test_subscribe_invalid_email(client):
    resp = client.post("/subscribe", json={"email": "not-an-email", "cadence": "daily"})
    assert resp.status_code == 422


def test_subscribe_invalid_cadence(client):
    resp = client.post("/subscribe", json={"email": "user@example.com", "cadence": "monthly"})
    assert resp.status_code == 422


def test_subscribe_duplicate(client):
    client.post("/subscribe", json={"email": "dup@example.com", "cadence": "daily"})
    resp = client.post("/subscribe", json={"email": "dup@example.com", "cadence": "daily"})
    assert resp.status_code == 409


def test_subscribe_does_not_send_email_without_resend_key(client, db):
    """RESEND_API_KEY is empty in tests so no email should be attempted."""
    with patch("app.main.resend.Emails.send") as mock_send:
        client.post("/subscribe", json={"email": "nosend@example.com", "cadence": "daily"})
    mock_send.assert_not_called()


# ── Confirm ───────────────────────────────────────────────────────────────────


def test_confirm_subscription(client, db):
    # Insert subscriber directly to avoid hitting the rate-limited /subscribe endpoint.
    sub = Subscriber(email="confirm@example.com", cadence="daily", confirmation_token="confirm-tok")
    db.add(sub)
    db.commit()
    assert sub.confirmed is False

    resp = client.get(f"/confirm/{sub.confirmation_token}", follow_redirects=False)
    assert resp.status_code in (302, 307)

    db.refresh(sub)
    assert sub.confirmed is True


def test_confirm_invalid_token(client):
    resp = client.get("/confirm/totally-fake-token")
    assert resp.status_code == 404


# ── Unsubscribe ───────────────────────────────────────────────────────────────


def test_unsubscribe(client, db):
    sub = Subscriber(email="unsub@example.com", cadence="daily", confirmation_token="unsub-tok-1")
    db.add(sub)
    db.commit()

    resp = client.get(f"/unsubscribe/{sub.confirmation_token}")
    assert resp.status_code == 200

    db.refresh(sub)
    assert sub.unsubscribed_at is not None


def test_unsubscribe_idempotent(client, db):
    sub = Subscriber(email="unsub2@example.com", cadence="weekly", confirmation_token="unsub-tok-2")
    db.add(sub)
    db.commit()

    client.get(f"/unsubscribe/{sub.confirmation_token}")
    resp = client.get(f"/unsubscribe/{sub.confirmation_token}")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Already unsubscribed"


def test_unsubscribe_invalid_token(client):
    resp = client.get("/unsubscribe/bad-token-xyz")
    assert resp.status_code == 404


# ── Admin endpoints ───────────────────────────────────────────────────────────


def test_admin_fetch_no_auth(client):
    resp = client.post("/admin/fetch")
    assert resp.status_code == 401


def test_admin_fetch_wrong_key(client):
    resp = client.post("/admin/fetch", headers={"X-Admin-Key": "wrong-key"})
    assert resp.status_code == 401


def test_admin_fetch_authorized(client):
    with patch("app.main.fetch_all_sources", new_callable=AsyncMock, return_value=3):
        resp = client.post("/admin/fetch", headers={"X-Admin-Key": "test-admin-secret"})
    assert resp.status_code == 200
    assert resp.json()["new_articles"] == 3


def test_admin_summarize_no_auth(client):
    assert client.post("/admin/summarize").status_code == 401


def test_admin_summarize_authorized(client):
    resp = client.post("/admin/summarize", headers={"X-Admin-Key": "test-admin-secret"})
    assert resp.status_code == 200
    assert resp.json()["processed"] == 0  # no articles to summarize


def test_admin_digest_daily_no_auth(client):
    assert client.post("/admin/digest/daily").status_code == 401


def test_admin_digest_daily_authorized(client):
    with patch("app.main.run_daily_digest", new_callable=AsyncMock):
        resp = client.post("/admin/digest/daily", headers={"X-Admin-Key": "test-admin-secret"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_admin_digest_weekly_no_auth(client):
    assert client.post("/admin/digest/weekly").status_code == 401


def test_admin_digest_weekly_authorized(client):
    with patch("app.main.run_weekly_digest", new_callable=AsyncMock):
        resp = client.post("/admin/digest/weekly", headers={"X-Admin-Key": "test-admin-secret"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
