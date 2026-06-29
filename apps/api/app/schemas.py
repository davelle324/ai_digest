from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    source_type: str
    category: str | None
    enabled: bool


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    excerpt: str | None
    summary: str | None
    published_at: datetime | None
    fetched_at: datetime
    source: SourceOut


class ArticleListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ArticleOut]
    total: int
    page: int
    pages: int


class StatsOut(BaseModel):
    total_articles: int
    total_sources: int
    total_subscribers: int
    articles_per_source: list[dict]
    articles_per_category: list[dict]
    articles_per_day: list[dict]


class SubscribeIn(BaseModel):
    email: EmailStr
    cadence: Literal["daily", "weekly"]


class SubscribeOut(BaseModel):
    message: str
