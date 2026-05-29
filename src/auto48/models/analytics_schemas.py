"""Pydantic response schemas for the dealer analytics dashboard."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ListingCountsSchema(BaseModel):
    """Listing counts broken down by status."""

    model_config = ConfigDict(from_attributes=True)

    total: int
    active: int
    sold: int
    draft: int
    expired: int


class InventoryValueSchema(BaseModel):
    """Aggregate monetary value of the active inventory."""

    model_config = ConfigDict(from_attributes=True)

    total_eur_cents: int
    avg_eur_cents: float


class MakeBreakdownItemSchema(BaseModel):
    """Per-make aggregate for the dealer's listings."""

    model_config = ConfigDict(from_attributes=True)

    make: str
    count: int
    avg_price_eur_cents: float


class BodyBreakdownItemSchema(BaseModel):
    """Per-body-type aggregate for the dealer's listings."""

    model_config = ConfigDict(from_attributes=True)

    body: str
    count: int
    avg_price_eur_cents: float


class TestDriveByStatusSchema(BaseModel):
    """Test-drive request count for a single booking status."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    count: int


class FeedHealthSchema(BaseModel):
    """Summary of the latest ingest run for one dealer feed."""

    model_config = ConfigDict(from_attributes=True)

    feed_id: int
    status: str
    created_count: int
    updated_count: int
    error_count: int


class DealerAnalyticsSchema(BaseModel):
    """Full analytics dashboard response for an authenticated dealer."""

    model_config = ConfigDict(from_attributes=True)

    listing_counts: ListingCountsSchema
    inventory_value: InventoryValueSchema
    top_makes: list[MakeBreakdownItemSchema]
    top_bodies: list[BodyBreakdownItemSchema]
    total_leads: int
    total_test_drives: int
    test_drives_by_status: list[TestDriveByStatusSchema]
    feed_health: list[FeedHealthSchema]
