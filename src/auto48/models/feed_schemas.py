"""Pydantic request/response schemas for dealer feed endpoints (RORO)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from auto48.models.dealer_feed import FeedFormat, IngestStatus


class FeedCreate(BaseModel):
    """Request body for registering a new dealer feed."""

    url: HttpUrl
    format: FeedFormat


class FeedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_id: int
    url: str
    format: FeedFormat
    active: bool
    created_at: datetime
    last_run_at: datetime | None = None


class IngestRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    feed_id: int
    started_at: datetime
    finished_at: datetime | None = None
    status: IngestStatus
    created_count: int
    updated_count: int
    error_count: int
    error_detail: dict[str, Any] | None = None


class IngestTriggerResponse(BaseModel):
    """Returned from the synchronous ingest endpoint."""

    run_id: int
    status: IngestStatus
    created_count: int
    updated_count: int
    error_count: int


class FeedListResponse(BaseModel):
    items: list[FeedResponse] = Field(default_factory=list)
    total: int


class RunListResponse(BaseModel):
    items: list[IngestRunResponse] = Field(default_factory=list)
    total: int
