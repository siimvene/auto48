"""Pydantic schemas for the natural-language search endpoint."""

from pydantic import BaseModel, ConfigDict

from auto48.models.schemas import ListingResponse
from auto48.models.vehicle import BodyType, FuelType, Transmission


class ParsedQueryResponse(BaseModel):
    """Serialisable representation of the facets parsed from the query string."""

    model_config = ConfigDict(use_enum_values=True)

    make: str | None = None
    model: str | None = None
    fuel: FuelType | None = None
    body: BodyType | None = None
    transmission: Transmission | None = None
    year_min: int | None = None
    year_max: int | None = None
    price_max_eur_cents: int | None = None
    price_min_eur_cents: int | None = None
    mileage_max: int | None = None


class NLSearchResponse(BaseModel):
    """Envelope returned by GET /v1/search."""

    parsed: ParsedQueryResponse
    items: list[ListingResponse]
    total: int
    limit: int
    offset: int
