"""Pydantic response schemas for the vehicle-data endpoints.

Kept separate from schemas.py (domain listing schemas) to avoid coupling.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from auto48.models.history import HistoryEventType
from auto48.models.vehicle import BodyType, Drivetrain, FuelType, Transmission


class VehicleDataResponse(BaseModel):
    """Decoded vehicle specification returned by GET /v1/vehicles/lookup."""

    make: str
    model: str
    year: int
    fuel: FuelType
    body: BodyType
    transmission: Transmission
    variant: str | None = None
    drivetrain: Drivetrain | None = None
    engine_cc: int | None = None
    power_kw: int | None = None
    color: str | None = None
    first_registered: date | None = None

    model_config = {"from_attributes": True}


class VehicleHistoryRecordResponse(BaseModel):
    """A single history event."""

    event_type: HistoryEventType
    occurred_at: datetime
    source: str
    odometer_km: int | None = None
    detail: dict | None = None

    model_config = {"from_attributes": True}


class VehicleHistoryResponse(BaseModel):
    """History timeline with rollback flag — GET /v1/vehicles/{vin}/history."""

    records: list[VehicleHistoryRecordResponse]
    rollback_suspected: bool
