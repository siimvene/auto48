"""Pydantic request/response schemas (RORO: objects in, objects out)."""

from pydantic import BaseModel, ConfigDict, Field


class ListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    make: str
    model: str
    year: int
    price_eur: int
    mileage_km: int | None = None


class ListingCreate(BaseModel):
    make: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=64)
    year: int = Field(ge=1900, le=2100)
    price_eur: int = Field(ge=0)
    mileage_km: int | None = Field(default=None, ge=0)


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
