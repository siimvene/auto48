"""Recommendation service: similar listings and personalised recommendations.

All ranking logic lives in pure helper functions (_price_proximity_key, etc.)
so it is unit-testable without a database session.
"""

from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import ColumnElement

from auto48.models.listing import Listing, ListingStatus
from auto48.models.vehicle import BodyType, FuelType, Vehicle

# ---------------------------------------------------------------------------
# Pure ranking helpers (no I/O — easy to unit-test)
# ---------------------------------------------------------------------------


def _price_proximity_key(seed_price: int, listing: Listing) -> int:
    """Return absolute price distance from seed; used as primary sort key."""
    return abs(listing.price_eur_cents - seed_price)


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


async def similar_to(
    db: AsyncSession,
    listing: Listing,
    *,
    limit: int = 6,
) -> list[Listing]:
    """Return up to *limit* active listings similar to *listing*.

    Similarity criteria (all must hold):
    - Same body type
    - Price within ±35% of the seed listing's price
    - Year within ±3 of the seed vehicle's year
    - Not the seed listing itself
    - Status ACTIVE

    Results are sorted by price proximity (ascending), then newest first as a
    tie-breaker.  The sort is applied in Python so the ranking key stays a
    pure, testable function rather than a DB expression.
    """
    seed_price = listing.price_eur_cents
    seed_year = listing.vehicle.year
    seed_body = listing.vehicle.body

    price_min = int(seed_price * (1 - 0.35))
    price_max = int(seed_price * (1 + 0.35))
    year_min = seed_year - 3
    year_max = seed_year + 3

    stmt = (
        select(Listing)
        .join(Listing.vehicle)
        .options(selectinload(Listing.vehicle), selectinload(Listing.photos))
        .where(
            and_(
                Listing.id != listing.id,
                Listing.status == ListingStatus.ACTIVE,
                Vehicle.body == seed_body,
                Listing.price_eur_cents >= price_min,
                Listing.price_eur_cents <= price_max,
                Vehicle.year >= year_min,
                Vehicle.year <= year_max,
            )
        )
    )

    rows = list((await db.scalars(stmt)).all())

    # Sort: same make first (stable sub-key = price proximity, then newest).
    seed_make = listing.vehicle.make

    def _sort_key(r: Listing) -> tuple[int, int, int]:
        same_make = 0 if r.vehicle.make == seed_make else 1
        price_dist = _price_proximity_key(seed_price, r)
        # Negate created_at timestamp so larger (newer) sorts earlier.
        recency = -int(r.created_at.timestamp())
        return (same_make, price_dist, recency)

    rows.sort(key=_sort_key)
    return rows[:limit]


async def recommend(
    db: AsyncSession,
    *,
    make: str | None = None,
    body: BodyType | None = None,
    fuel: FuelType | None = None,
    max_price_eur_cents: int | None = None,
    limit: int = 12,
) -> list[Listing]:
    """Return up to *limit* ACTIVE listings matching the supplied attribute filters.

    Results are ordered newest first.  All filters are optional; omitting all
    returns the most recently created active listings.
    """
    conditions: list[ColumnElement[bool]] = [Listing.status == ListingStatus.ACTIVE]

    if make is not None:
        conditions.append(Vehicle.make.ilike(f"%{make}%"))
    if body is not None:
        conditions.append(Vehicle.body == body)
    if fuel is not None:
        conditions.append(Vehicle.fuel == fuel)
    if max_price_eur_cents is not None:
        conditions.append(Listing.price_eur_cents <= max_price_eur_cents)

    stmt = (
        select(Listing)
        .join(Listing.vehicle)
        .options(selectinload(Listing.vehicle), selectinload(Listing.photos))
        .where(and_(*conditions))
        .order_by(Listing.created_at.desc(), Listing.id.desc())
        .limit(limit)
    )

    return list((await db.scalars(stmt)).all())
