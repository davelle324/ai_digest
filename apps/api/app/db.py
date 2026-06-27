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
    {
        "name": "arXiv cs.AI",
        "url": "https://rss.arxiv.org/rss/cs.AI",
        "source_type": "rss",
    },
    {
        "name": "arXiv cs.LG",
        "url": "https://rss.arxiv.org/rss/cs.LG",
        "source_type": "rss",
    },
    {
        "name": "The Batch",
        "url": "https://www.deeplearning.ai/the-batch/feed/",
        "source_type": "rss",
    },
    {
        "name": "Towards Data Science",
        "url": "https://towardsdatascience.com/feed",
        "source_type": "rss",
    },
    {
        "name": "HackerNews AI",
        "url": "hackernews",
        "source_type": "hackernews",
    },
]


def init_db() -> None:
    """Create all tables and seed default sources if not present."""
    # Import models here to ensure they are registered with Base
    from app.models import Source  # noqa: F401

    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        for source_data in DEFAULT_SOURCES:
            existing = db.query(Source).filter(Source.url == source_data["url"]).first()
            if not existing:
                source = Source(**source_data)
                db.add(source)
        db.commit()
    finally:
        db.close()
