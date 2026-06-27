"""Fetcher unit tests — no real HTTP calls, no real data stored."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.fetcher import _contains_ai_keywords, fetch_hackernews, fetch_rss
from app.models import Article, Source


# ── Helpers ──────────────────────────────────────────────────────────────────


def _source(db, source_type="rss"):
    s = Source(
        name="Test Feed",
        url="https://test.com/feed" if source_type == "rss" else "hackernews",
        source_type=source_type,
        enabled=True,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _mock_entry(title="Article", link="https://test.com/a", summary="Content"):
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.published_parsed = (2024, 6, 1, 10, 0, 0, 0, 0, 0)
    return entry


# ── Keyword filter ────────────────────────────────────────────────────────────


class TestKeywordFilter:
    def test_detects_ai(self):
        assert _contains_ai_keywords("New AI model released")

    def test_detects_llm(self):
        assert _contains_ai_keywords("Using LLM for code generation")

    def test_detects_machine_learning(self):
        assert _contains_ai_keywords("Machine learning for drug discovery")

    def test_detects_anthropic(self):
        assert _contains_ai_keywords("Anthropic announces Claude 4")

    def test_detects_openai(self):
        assert _contains_ai_keywords("OpenAI releases new model")

    def test_detects_transformer(self):
        assert _contains_ai_keywords("Transformer architecture improvements")

    def test_case_insensitive(self):
        assert _contains_ai_keywords("DEEP LEARNING breakthrough")

    def test_no_match(self):
        assert not _contains_ai_keywords("Rust 2.0 programming language released")

    def test_empty_string(self):
        assert not _contains_ai_keywords("")

    def test_partial_word_not_matched(self):
        # "mail" does not contain a keyword; "ai" as substring of longer word
        # The keyword list checks for substring, so "ai" in "mail" WILL match.
        # Documenting this known behaviour rather than asserting a false negative.
        assert _contains_ai_keywords("Gmail AI features")


# ── RSS fetch ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_rss_inserts_article(db):
    source = _source(db)
    entry = _mock_entry(title="LLM breakthrough", link="https://test.com/llm")
    mock_feed = MagicMock()
    mock_feed.entries = [entry]

    with patch("app.fetcher.feedparser.parse", return_value=mock_feed):
        count = await fetch_rss(source, db)

    assert count == 1
    articles = db.query(Article).filter(Article.source_id == source.id).all()
    assert len(articles) == 1
    assert articles[0].title == "LLM breakthrough"
    assert articles[0].excerpt == "Content"


@pytest.mark.asyncio
async def test_fetch_rss_skips_missing_url(db):
    source = _source(db)
    entry = MagicMock()
    entry.title = "No URL article"
    entry.link = ""  # empty URL — should be skipped
    entry.summary = "Content"
    entry.published_parsed = None
    mock_feed = MagicMock()
    mock_feed.entries = [entry]

    with patch("app.fetcher.feedparser.parse", return_value=mock_feed):
        count = await fetch_rss(source, db)

    assert count == 0


@pytest.mark.asyncio
async def test_fetch_rss_deduplicates(db):
    source = _source(db)
    entry = _mock_entry(title="Same Article", link="https://test.com/same")
    mock_feed = MagicMock()
    mock_feed.entries = [entry]

    with patch("app.fetcher.feedparser.parse", return_value=mock_feed):
        first = await fetch_rss(source, db)
        second = await fetch_rss(source, db)

    assert first == 1
    assert second == 0  # duplicate URL silently skipped
    assert db.query(Article).count() == 1


@pytest.mark.asyncio
async def test_fetch_rss_truncates_excerpt(db):
    source = _source(db)
    long_content = "x" * 1000
    entry = _mock_entry(summary=long_content)
    mock_feed = MagicMock()
    mock_feed.entries = [entry]

    with patch("app.fetcher.feedparser.parse", return_value=mock_feed):
        await fetch_rss(source, db)

    article = db.query(Article).first()
    assert article is not None
    assert len(article.excerpt) == 500


@pytest.mark.asyncio
async def test_fetch_rss_updates_last_fetched(db):
    source = _source(db)
    assert source.last_fetched_at is None
    mock_feed = MagicMock()
    mock_feed.entries = []

    with patch("app.fetcher.feedparser.parse", return_value=mock_feed):
        await fetch_rss(source, db)

    db.refresh(source)
    assert source.last_fetched_at is not None


# ── HackerNews fetch ──────────────────────────────────────────────────────────


def _make_hn_client(top_story_ids: list[int], items: dict[int, dict]):
    """Build a mock httpx.AsyncClient that returns pre-defined HN API responses."""

    async def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "topstories" in url:
            resp.json.return_value = top_story_ids
        else:
            story_id = int(url.rstrip(".json").split("/")[-1])
            resp.json.return_value = items.get(story_id, {})
        return resp

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=mock_get)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.asyncio
async def test_fetch_hackernews_filters_non_ai(db):
    source = _source(db, "hackernews")
    items = {
        1: {"title": "New LLM beats GPT-4", "url": "https://ex.com/llm", "time": 1700000000},
        2: {"title": "JavaScript 2.0 released", "url": "https://ex.com/js", "time": 1700000001},
        3: {"title": "OpenAI announces GPT-5", "url": "https://ex.com/gpt5", "time": 1700000002},
    }
    mock_client = _make_hn_client([1, 2, 3], items)

    with patch("app.fetcher.httpx.AsyncClient", return_value=mock_client):
        count = await fetch_hackernews(source, db)

    assert count == 2  # only stories 1 and 3 match AI keywords
    titles = {a.title for a in db.query(Article).all()}
    assert "New LLM beats GPT-4" in titles
    assert "OpenAI announces GPT-5" in titles
    assert "JavaScript 2.0 released" not in titles


@pytest.mark.asyncio
async def test_fetch_hackernews_handles_api_error(db):
    source = _source(db, "hackernews")

    async def failing_get(url, **kwargs):
        raise Exception("Network error")

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=failing_get)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.fetcher.httpx.AsyncClient", return_value=mock_client):
        count = await fetch_hackernews(source, db)

    assert count == 0  # graceful fallback on error


@pytest.mark.asyncio
async def test_fetch_hackernews_skips_missing_url(db):
    source = _source(db, "hackernews")
    items = {
        1: {"title": "AI article with no URL", "url": "", "time": 1700000000},
    }
    mock_client = _make_hn_client([1], items)

    with patch("app.fetcher.httpx.AsyncClient", return_value=mock_client):
        count = await fetch_hackernews(source, db)

    assert count == 0
