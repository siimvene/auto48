"""Geo/proximity router: map-based listing discovery.

Endpoint:
    GET /v1/listings/nearby?lat=&lon=&radius_km=&limit=

Validation errors are explicit 400s (not FastAPI's 422) to match the project's
RFC 7807 contract.  Thin handler: parameter validation only, then delegates to
the geo service.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from auto48.api.dependencies import DbSession
from auto48.models.geo_schemas import NearbyListing
from auto48.models.schemas import ListingResponse
from auto48.services.geo import nearby

router = APIRouter(prefix="/v1/listings", tags=["geo"])


@router.get("/nearby", response_model=list[NearbyListing])
async def get_nearby_listings(
    db: DbSession,
    lat: Annotated[float, Query(description="Centre latitude in decimal degrees")],
    lon: Annotated[float, Query(description="Centre longitude in decimal degrees")],
    radius_km: Annotated[float, Query(description="Search radius in kilometres")],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[NearbyListing]:
    """Return active listings within *radius_km* of the given coordinates.

    Coordinates are validated explicitly to return 400 (not 422) on bad input.
    Results are sorted nearest-first and capped at *limit*.
    """
    if not (-90.0 <= lat <= 90.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lat must be in range [-90, 90]",
        )
    if not (-180.0 <= lon <= 180.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lon must be in range [-180, 180]",
        )
    if radius_km <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="radius_km must be greater than 0",
        )

    hits = await nearby(db, lat=lat, lon=lon, radius_km=radius_km, limit=limit)

    return [
        NearbyListing(
            listing=ListingResponse.model_validate(listing),
            distance_km=round(dist_km, 3),
        )
        for listing, dist_km in hits
    ]
