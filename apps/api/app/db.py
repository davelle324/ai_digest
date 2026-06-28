import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./digest.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DEFAULT_SOURCES = [
    # Top Stories
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "source_type": "rss", "category": "top_stories"},
    {"name": "Anthropic", "url": "https://www.anthropic.com/rss.xml", "source_type": "rss", "category": "top_stories"},
    {"name": "Google AI", "url": "https://blog.google/technology/ai/rss/", "source_type": "rss", "category": "top_stories"},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "source_type": "rss", "category": "top_stories"},
    {"name": "The Batch", "url": "https://www.deeplearning.ai/the-batch/feed/", "source_type": "rss", "category": "top_stories"},
    # Research
    {"name": "arXiv cs.AI", "url": "https://rss.arxiv.org/rss/cs.AI", "source_type": "rss", "category": "research"},
    {"name": "arXiv cs.LG", "url": "https://rss.arxiv.org/rss/cs.LG", "source_type": "rss", "category": "research"},
    {"name": "arXiv cs.CL", "url": "https://rss.arxiv.org/rss/cs.CL", "source_type": "rss", "category": "research"},
    # Open Source
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "source_type": "rss", "category": "open_source"},
    {"name": "Towards Data Science", "url": "https://towardsdatascience.com/feed", "source_type": "rss", "category": "open_source"},
    # Company Releases
    {"name": "NVIDIA Blog", "url": "https://blogs.nvidia.com/blog/category/artificial-intelligence/feed/", "source_type": "rss", "category": "company"},
    {"name": "Meta AI", "url": "https://ai.meta.com/blog/rss/", "source_type": "rss", "category": "company"},
    # Community Buzz
    {"name": "HackerNews AI", "url": "hackernews", "source_type": "hackernews", "category": "community"},
    {"name": "Reddit r/MachineLearning", "url": "https://www.reddit.com/r/MachineLearning/.rss", "source_type": "rss", "category": "community"},
    {"name": "Reddit r/LocalLLaMA", "url": "https://www.reddit.com/r/LocalLLaMA/.rss", "source_type": "rss", "category": "community"},
]

CATEGORY_LABELS: dict[str, str] = {
    "top_stories": "🔥 Top Stories",
    "research": "🧠 Research",
    "open_source": "💻 Open Source",
    "company": "🏢 Company Releases",
    "community": "👥 Community Buzz",
}

CATEGORY_ORDER = list(CATEGORY_LABELS.keys())


def init_db() -> None:
    """Create all tables and seed default sources if not present."""
    from app.models import Source  # noqa: F401

    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        for source_data in DEFAULT_SOURCES:
            existing = db.query(Source).filter(Source.url == source_data["url"]).first()
            if not existing:
                db.add(Source(**source_data))
            elif existing.category != source_data.get("category"):
                existing.category = source_data.get("category")
        db.commit()
    finally:
        db.close()
