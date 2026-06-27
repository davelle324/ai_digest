from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'rss' or 'hackernews'
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    articles: Mapped[list["Article"]] = relationship("Article", back_populates="source")

    def __repr__(self) -> str:
        return f"<Source id={self.id} name={self.name!r} type={self.source_type!r}>"


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source: Mapped["Source"] = relationship("Source", back_populates="articles")

    def __repr__(self) -> str:
        return f"<Article id={self.id} title={self.title[:50]!r}>"


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    cadence: Mapped[str] = mapped_column(String(10), nullable=False)  # 'daily' or 'weekly'
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmation_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    digest_logs: Mapped[list["DigestLog"]] = relationship("DigestLog", back_populates="subscriber")

    def __repr__(self) -> str:
        return f"<Subscriber id={self.id} email={self.email!r} cadence={self.cadence!r}>"


class DigestLog(Base):
    __tablename__ = "digest_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    subscriber_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscribers.id"), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    article_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)  # 'sent' or 'failed'
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    subscriber: Mapped["Subscriber"] = relationship("Subscriber", back_populates="digest_logs")

    def __repr__(self) -> str:
        return f"<DigestLog id={self.id} subscriber_id={self.subscriber_id} status={self.status!r}>"
