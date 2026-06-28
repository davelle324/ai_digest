import asyncio
import html
import logging
import re
from datetime import datetime, timezone

import feedparser
import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Article, Source

logger = logging.getLogger(__name__)

HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

AI_ML_KEYWORDS = [
    "ai",
    "ml",
    "llm",
    "gpt",
    "machine learning",
    "neural",
    "deep learning",
    "transformer",
    "openai",
    "anthropic",
    "gemini",
    "mistral",
    "ollama",
    "hugging face",
    "langchain",
    "rag",
    "fine-tun",
]


def _contains_ai_keywords(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in AI_ML_KEYWORDS)


def _strip_html(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_feed(url: str):
    return feedparser.parse(url)


async def fetch_rss(source: Source, db: Session) -> int:
    """Fetch RSS feed and insert new articles. Returns count of new articles added."""
    loop = asyncio.get_event_loop()
    feed = await loop.run_in_executor(None, _parse_feed, source.url)

    count = 0
    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        url = getattr(entry, "link", "").strip()

        if not title or not url:
            continue

        # Extract excerpt from summary/content
        raw_content = getattr(entry, "summary", "") or ""
        if not raw_content:
            content_list = getattr(entry, "content", [])
            if content_list:
                raw_content = content_list[0].get("value", "")
        excerpt = _strip_html(raw_content)[:500] if raw_content else None

        # Parse published date
        published_at: datetime | None = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except Exception:
                pass

        article = Article(
            source_id=source.id,
            title=title,
            url=url,
            excerpt=excerpt,
            published_at=published_at,
        )
        db.add(article)
        try:
            db.commit()
            count += 1
        except IntegrityError:
            db.rollback()  # Duplicate URL — silently skip

    source.last_fetched_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("RSS %s: added %d new articles", source.name, count)
    return count


async def fetch_hackernews(source: Source, db: Session) -> int:
    """Fetch top HN stories filtered by AI/ML keywords. Returns count of new articles added."""
    semaphore = asyncio.Semaphore(10)
    count = 0

    async def fetch_item(client: httpx.AsyncClient, story_id: int) -> dict | None:
        async with semaphore:
            try:
                resp = await client.get(HN_ITEM_URL.format(id=story_id), timeout=10.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                logger.debug("Failed to fetch HN item %d: %s", story_id, exc)
                return None

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(HN_TOP_STORIES_URL, timeout=15.0)
            resp.raise_for_status()
            story_ids: list[int] = resp.json()
        except Exception as exc:
            logger.error("Failed to fetch HN top stories: %s", exc)
            return 0

        # Check up to 200 stories, fetch up to 100 max
        candidate_ids = story_ids[:200]
        tasks = [fetch_item(client, sid) for sid in candidate_ids]
        items = await asyncio.gather(*tasks)

    fetched = 0
    for item in items:
        if item is None:
            continue
        title = item.get("title", "").strip()
        url = item.get("url", "").strip()

        if not title or not url:
            continue

        if not _contains_ai_keywords(title):
            continue

        if fetched >= 100:
            break

        published_at: datetime | None = None
        if item.get("time"):
            try:
                published_at = datetime.fromtimestamp(item["time"], tz=timezone.utc)
            except Exception:
                pass

        article = Article(
            source_id=source.id,
            title=title,
            url=url,
            excerpt=None,
            published_at=published_at,
        )
        db.add(article)
        try:
            db.commit()
            count += 1
            fetched += 1
        except IntegrityError:
            db.rollback()  # Duplicate URL — silently skip

    source.last_fetched_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("HackerNews AI: added %d new articles", count)
    return count


async def fetch_all_sources(db: Session) -> int:
    """Fetch all enabled sources and return total count of new articles added."""
    sources = db.query(Source).filter(Source.enabled.is_(True)).all()
    total = 0
    for source in sources:
        try:
            if source.source_type == "rss":
                total += await fetch_rss(source, db)
            elif source.source_type == "hackernews":
                total += await fetch_hackernews(source, db)
        except Exception as exc:
            logger.error("Error fetching source %s: %s", source.name, exc)
    return total
