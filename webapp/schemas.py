"""Pydantic request/response models for the web API."""
from pydantic import BaseModel, Field


class Trend(BaseModel):
    category: str
    keywords: list[str] = Field(default_factory=list)
    aesthetic: str = ""
    surfaces: list[str] = Field(default_factory=list)
    lighting: str = ""
    background_elements: list[str] = Field(default_factory=list)
    audience: str = ""


class TrendsPayload(BaseModel):
    trends: list[Trend]


class FeedPreviewRequest(BaseModel):
    feed_path: str
    trend: str | None = None
    limit: int = 10


class RunRequest(BaseModel):
    feed_path: str
    trend: str | None = None       # backward-compatible single trend
    trends: list[str] | None = None  # multi-select — takes priority over `trend` if set
    limit: int = 3
    post: bool = False


class SettingsPayload(BaseModel):
    ANTHROPIC_API_KEY: str | None = None
    PINTEREST_ACCESS_TOKEN: str | None = None
    PINTEREST_APP_ID: str | None = None
    PINTEREST_APP_SECRET: str | None = None
