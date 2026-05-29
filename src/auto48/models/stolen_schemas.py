"""Pydantic response schemas for the stolen-vehicle check endpoint.

Kept separate from schemas.py (domain listing schemas) to avoid coupling.
"""

from __future__ import annotations

from pydantic import BaseModel


class StolenCheckResponse(BaseModel):
    """Stolen-vehicle check result returned by GET /v1/vehicles/{vin}/stolen-check."""

    vin: str
    flagged: bool
    source: str
    detail: str | None = None

    model_config = {"from_attributes": True}
