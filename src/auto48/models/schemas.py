"""Pydantic request/response schemas (RORO: objects in, objects out)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from auto48.models.listing import ListingStatus
from auto48.models.vehicle import BodyType, Drivetrain, FuelType, Transmission


class VehicleCreate(BaseModel):
    vin: str | None = Field(default=None, max_length=32)
    plate: str | None = Field(default=None, max_length=16)
    make: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=64)
    variant: str | None = Field(default=None, max_length=128)
    year: int = Field(ge=1900, le=2100)
    fuel: FuelType
    body: BodyType
    transmission: Transmission
    drivetrain: Drivetrain | None = None
    specs: dict[str, Any] | None = None


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vin: str | None = None
    plate: str | None = None
    make: str
    model: str
    variant: str | None = None
    year: int
    fuel: FuelType
    body: BodyType
    transmission: Transmission
    drivetrain: Drivetrain | None = None
    specs: dict[str, Any] | None = None


class ListingCreate(BaseModel):
    seller_id: int
    vehicle: VehicleCreate
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price_eur_cents: int = Field(ge=0)
    mileage_km: int | None = Field(default=None, ge=0)
    location_county: str | None = Field(default=None, max_length=64)
    lat: float | None = None
    lon: float | None = None


class ListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_id: int
    vehicle_id: int
    title: str
    description: str | None = None
    price_eur_cents: int
    mileage_km: int | None = None
    location_county: str | None = None
    lat: float | None = None
    lon: float | None = None
    status: ListingStatus
    vehicle: VehicleResponse
    created_at: datetime
    updated_at: datetime


class Page(BaseModel):
    """Envelope for paginated collection responses (limit/offset)."""

    items: list[ListingResponse]
    total: int
    limit: int
    offset: int


class Problem(BaseModel):
    """RFC 7807 Problem Details for error responses."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
