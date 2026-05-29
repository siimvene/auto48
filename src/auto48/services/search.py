"""Faceted search service for listings.

Pure, testable functions that build SQLAlchemy select/filter expressions.
No I/O here — callers inject the session and execute queries themselves.
"""

from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import ColumnElement

from auto48.models.listing import Listing, ListingStatus
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle

# Allowlist for sort columns — ORDER BY is built from this dict, never from raw input.
_SORT_COLUMNS: dict[str, list[Any]] = {
    "newest": [Listing.created_at.desc(), Listing.id.desc()],
    "price_asc": [Listing.price_eur_cents.asc(), Listing.id.asc()],
    "price_desc": [Listing.price_eur_cents.desc(), Listing.id.desc()],
    "year_desc": [Vehicle.year.desc(), Listing.id.desc()],
    "mileage_asc": [Listing.mileage_km.asc(), Listing.id.asc()],
}
DEFAULT_SORT = "newest"


def build_filters(  # noqa: PLR0913 – many facets is expected here
    *,
    make: str | None = None,
    model: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    mileage_max: int | None = None,
    fuel: FuelType | None = None,
    body: BodyType | None = None,
    transmission: Transmission | None = None,
    location: str | None = None,
    q: str | None = None,
    status: ListingStatus | None = None,
) -> list[ColumnElement[bool]]:
    """Return a list of SQLAlchemy WHERE clause expressions for faceted listing search.

    All string comparisons use ILIKE (case-insensitive LIKE), portable to Postgres.
    Note: `q` uses simple ILIKE substring matching; Phase 4 replaces this with
    Postgres full-text search (tsvector/tsquery) for performance and ranking.
    """
    filters: list[ColumnElement[bool]] = []

    if make is not None:
        filters.append(Vehicle.make.ilike(f"%{make}%"))
    if model is not None:
        filters.append(Vehicle.model.ilike(f"%{model}%"))

    if year_min is not None:
        filters.append(Vehicle.year >= year_min)
    if year_max is not None:
        filters.append(Vehicle.year <= year_max)

    if price_min is not None:
        filters.append(Listing.price_eur_cents >= price_min)
    if price_max is not None:
        filters.append(Listing.price_eur_cents <= price_max)

    if mileage_max is not None:
        filters.append(Listing.mileage_km <= mileage_max)

    if fuel is not None:
        filters.append(Vehicle.fuel == fuel)
    if body is not None:
        filters.append(Vehicle.body == body)
    if transmission is not None:
        filters.append(Vehicle.transmission == transmission)

    if location is not None:
        filters.append(Listing.location_county.ilike(f"%{location}%"))

    if q is not None:
        # Phase 4: replace with Postgres FTS (tsvector over title + make + model + variant)
        term = f"%{q}%"
        filters.append(
            or_(
                Listing.title.ilike(term),
                Vehicle.make.ilike(term),
                Vehicle.model.ilike(term),
                Vehicle.variant.ilike(term),
            )
        )

    if status is not None:
        filters.append(Listing.status == status)

    return filters


def build_count_query(filters: list[ColumnElement[bool]]) -> Select[tuple[int]]:
    """Return a COUNT query that mirrors the faceted filter set (no order/limit/offset)."""
    stmt = select(func.count()).select_from(Listing).join(Listing.vehicle)
    if filters:
        stmt = stmt.where(and_(*filters))
    return stmt


def build_listing_query(
    filters: list[ColumnElement[bool]],
    sort: str,
    limit: int,
    offset: int,
) -> Select[tuple[Listing]]:
    """Return a SELECT query with vehicle eager-load, sort, and pagination applied."""
    sort_key = sort if sort in _SORT_COLUMNS else DEFAULT_SORT
    order_exprs = _SORT_COLUMNS[sort_key]

    stmt = (
        select(Listing)
        .join(Listing.vehicle)
        .options(selectinload(Listing.vehicle), selectinload(Listing.photos))
        .order_by(*order_exprs)
        .limit(limit)
        .offset(offset)
    )
    if filters:
        stmt = stmt.where(and_(*filters))
    return stmt
