"""Pydantic request/response schemas for the escrow (deposit) domain (RORO pattern)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from auto48.models.escrow import DepositStatus


class PlaceDepositRequest(BaseModel):
    """Body for POST /v1/listings/{listing_id}/deposit."""

    amount_eur_cents: int = Field(gt=0, description="Deposit amount in EUR cents.")


class DepositResponse(BaseModel):
    """Response envelope for a single Deposit record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    listing_id: int
    buyer_id: int
    amount_eur_cents: int
    status: DepositStatus
    provider_ref: str | None = None
    created_at: datetime
    updated_at: datetime
