"""Pydantic request/response schemas for the billing domain (RORO pattern)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from auto48.models.billing import PromotionKind, SubscriptionPlan, SubscriptionStatus

# ---------------------------------------------------------------------------
# Subscription schemas
# ---------------------------------------------------------------------------


class SubscribeRequest(BaseModel):
    """Body for POST /v1/billing/subscribe."""

    plan: SubscriptionPlan


class SubscriptionResponse(BaseModel):
    """Response envelope for a single Subscription record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_id: int
    plan: SubscriptionPlan
    status: SubscriptionStatus
    stripe_subscription_id: str | None = None
    current_period_end: datetime | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Promotion schemas
# ---------------------------------------------------------------------------


class CreatePromotionRequest(BaseModel):
    """Body for POST /v1/listings/{listing_id}/promotions."""

    kind: PromotionKind
    duration_days: int = Field(ge=1, le=365)


class PromotionResponse(BaseModel):
    """Response envelope for a single Promotion record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    kind: PromotionKind
    starts_at: datetime
    ends_at: datetime
    stripe_payment_id: str | None = None
    created_at: datetime
