"""Car-listings resource: contract-first, paginated, async SQLAlchemy.

Thin handlers, Annotated DI, early returns, limit/offset pagination with a
separate count query, and RFC 7807 errors. Create accepts a nested vehicle and
persists Vehicle + Listing together.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from auto48.api.dependencies import DbSession
from auto48.models.listing import Listing, ListingStatus
from auto48.models.schemas import ListingCreate, ListingResponse, Page
from auto48.models.seller import SellerProfile
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle
from auto48.services.search import build_count_query, build_filters, build_listing_query

router = APIRouter(prefix="/v1/listings", tags=["listings"])


def _to_response(record: Listing) -> ListingResponse:
    """ListingResponse with thumbnail_url from the first photo (photos must be loaded)."""
    resp = ListingResponse.model_validate(record)
    resp.thumbnail_url = record.photos[0].url if record.photos else None
    return resp


@router.get("", response_model=Page)
async def list_listings(
    db: DbSession,
    # text / substring filters
    make: Annotated[
        str | None,
        Query(description="Substring match on vehicle make (case-insensitive)"),
    ] = None,
    model: Annotated[
        str | None,
        Query(description="Substring match on vehicle model (case-insensitive)"),
    ] = None,
    q: Annotated[
        str | None,
        Query(description="Free-text over title and vehicle make/model/variant"),
    ] = None,
    location: Annotated[
        str | None,
        Query(description="Substring match on location_county (case-insensitive)"),
    ] = None,
    # year range
    year_min: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    year_max: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    # price range (in EUR cents)
    price_min: Annotated[
        int | None, Query(ge=0, description="Minimum price in EUR cents")
    ] = None,
    price_max: Annotated[
        int | None, Query(ge=0, description="Maximum price in EUR cents")
    ] = None,
    # mileage cap
    mileage_max: Annotated[
        int | None, Query(ge=0, description="Maximum mileage in km")
    ] = None,
    # enum equality filters
    fuel: Annotated[FuelType | None, Query(description="Fuel type filter")] = None,
    body: Annotated[BodyType | None, Query(description="Body type filter")] = None,
    transmission: Annotated[
        Transmission | None, Query(description="Transmission type filter")
    ] = None,
    # optional status filter — all statuses returned by default
    status: Annotated[
        ListingStatus | None,
        Query(description="Filter by listing status; returns all statuses if omitted"),
    ] = None,
    # sort and pagination
    sort: Annotated[
        str,
        Query(
            description=(
                "Sort order: newest (default), price_asc, price_desc,"
                " year_desc, mileage_asc"
            )
        ),
    ] = "newest",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page:
    filters = build_filters(
        make=make,
        model=model,
        year_min=year_min,
        year_max=year_max,
        price_min=price_min,
        price_max=price_max,
        mileage_max=mileage_max,
        fuel=fuel,
        body=body,
        transmission=transmission,
        location=location,
        q=q,
        status=status,
    )

    total = await db.scalar(build_count_query(filters))
    rows = (await db.scalars(build_listing_query(filters, sort, limit, offset))).all()

    return Page(
        items=[_to_response(r) for r in rows],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: int, db: DbSession) -> ListingResponse:
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
    return _to_response(record)


@router.post("", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(payload: ListingCreate, db: DbSession) -> ListingResponse:
    seller = await db.get(SellerProfile, payload.seller_id)
    if seller is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Seller {payload.seller_id} not found",
        )

    vehicle = Vehicle(**payload.vehicle.model_dump())
    db.add(vehicle)
    await db.flush()

    listing = Listing(
        seller_id=payload.seller_id,
        vehicle_id=vehicle.id,
        title=payload.title,
        description=payload.description,
        price_eur_cents=payload.price_eur_cents,
        mileage_km=payload.mileage_km,
        location_county=payload.location_county,
        lat=payload.lat,
        lon=payload.lon,
    )
    db.add(listing)
    await db.flush()
    await db.refresh(listing, attribute_names=["vehicle"])
    return ListingResponse.model_validate(listing)
