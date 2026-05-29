"""Pydantic schemas for SavedSearch and Alert resources (RORO)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SavedSearchQuery(BaseModel):
    """Facet parameters stored inside a SavedSearch.

    All fields are optional — omitted facets match any value.
    """

    make: str | None = None
    model: str | None = None
    year_min: int | None = Field(default=None, ge=1900, le=2100)
    year_max: int | None = Field(default=None, ge=1900, le=2100)
    # Price in EUR cents (matches Listing.price_eur_cents convention).
    price_min: int | None = Field(default=None, ge=0)
    price_max: int | None = Field(default=None, ge=0)
    fuel: str | None = None
    body: str | None = None
    transmission: str | None = None
    location: str | None = None


class SavedSearchCreate(BaseModel):
    """Request body for POST /v1/saved-searches."""

    name: str = Field(min_length=1, max_length=255)
    query: SavedSearchQuery = Field(default_factory=SavedSearchQuery)


class SavedSearchResponse(BaseModel):
    """Response payload for a single saved search."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    query: dict[str, Any]
    active: bool
    last_notified_at: datetime | None = None
    created_at: datetime


class AlertResponse(BaseModel):
    """Response payload for an alert row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    saved_search_id: int
    listing_id: int
    notified: bool
    created_at: datetime
