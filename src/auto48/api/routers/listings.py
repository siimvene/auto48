"""Car-listings resource: contract-first, paginated, async SQLAlchemy.

Thin handlers, Annotated DI, early returns, limit/offset pagination with a
separate count query, and RFC 7807 errors. Create accepts a nested vehicle and
persists Vehicle + Listing together.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from auto48.api.dependencies import DbSession
from auto48.models.listing import Listing
from auto48.models.schemas import ListingCreate, ListingResponse, Page
from auto48.models.seller import SellerProfile
from auto48.models.vehicle import Vehicle

router = APIRouter(prefix="/v1/listings", tags=["listings"])


@router.get("", response_model=Page)
async def list_listings(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    make: str | None = None,
) -> Page:
    where = [Vehicle.make == make] if make else []

    count_stmt = select(func.count()).select_from(Listing).join(Listing.vehicle)
    total = await db.scalar(count_stmt.where(*where))

    rows = (
        await db.scalars(
            select(Listing)
            .join(Listing.vehicle)
            .where(*where)
            .options(selectinload(Listing.vehicle))
            .order_by(Listing.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    return Page(
        items=[ListingResponse.model_validate(r) for r in rows],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: int, db: DbSession) -> ListingResponse:
    record = await db.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.vehicle))
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found",
        )
    return ListingResponse.model_validate(record)


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
