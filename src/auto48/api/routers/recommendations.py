"""Recommendations resource: similar listings and personalised feed.

Thin handlers: parameter validation → service call → schema serialisation.
No business logic here — all ranking/filtering lives in the service layer.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from auto48.api.dependencies import DbSession
from auto48.models.listing import Listing
from auto48.models.schemas import ListingResponse
from auto48.models.vehicle import BodyType, FuelType
from auto48.services.recommendations import recommend, similar_to

router = APIRouter(tags=["recommendations"])


def _to_response(record: Listing) -> ListingResponse:
    """Build a ListingResponse, populating thumbnail_url from the first photo."""
    resp = ListingResponse.model_validate(record)
    resp.thumbnail_url = record.photos[0].url if record.photos else None
    return resp


@router.get(
    "/v1/listings/{listing_id}/similar",
    response_model=list[ListingResponse],
)
async def get_similar_listings(
    listing_id: int,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 6,
) -> list[ListingResponse]:
    """Return listings similar to the given listing (same body, close price & year)."""
    record = await db.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.vehicle), selectinload(Listing.photos))
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found",
        )

    results = await similar_to(db, record, limit=limit)
    return [_to_response(r) for r in results]


@router.get(
    "/v1/recommendations",
    response_model=list[ListingResponse],
)
async def get_recommendations(
    db: DbSession,
    make: Annotated[
        str | None,
        Query(description="Substring match on vehicle make (case-insensitive)"),
    ] = None,
    body: Annotated[BodyType | None, Query(description="Body type filter")] = None,
    fuel: Annotated[FuelType | None, Query(description="Fuel type filter")] = None,
    max_price_eur_cents: Annotated[
        int | None, Query(ge=0, description="Maximum price in EUR cents")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
) -> list[ListingResponse]:
    """Return personalised active listings, newest first, filtered by attributes."""
    # Only active listings make sense for personalised recommendations.
    results = await recommend(
        db,
        make=make,
        body=body,
        fuel=fuel,
        max_price_eur_cents=max_price_eur_cents,
        limit=limit,
    )
    return [_to_response(r) for r in results]
