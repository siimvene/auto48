"""Example car-listings resource: contract-first, paginated, async SQLAlchemy.

Demonstrates the SMIT conventions: thin handlers, Annotated DI, early returns,
limit/offset pagination with a separate count query, and RFC 7807 errors.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from auto48.api.dependencies import DbSession
from auto48.models.listing import Listing
from auto48.models.schemas import ListingCreate, ListingResponse, Page

router = APIRouter(prefix="/v1/listings", tags=["listings"])


@router.get("", response_model=Page)
async def list_listings(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    make: str | None = None,
) -> Page:
    where = [Listing.make == make] if make else []

    total = await db.scalar(select(func.count()).select_from(Listing).where(*where))
    rows = (
        await db.scalars(
            select(Listing).where(*where).order_by(Listing.created_at.desc()).limit(limit).offset(offset)
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
    record = await db.get(Listing, listing_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found",
        )
    return ListingResponse.model_validate(record)


@router.post("", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
async def create_listing(payload: ListingCreate, db: DbSession) -> ListingResponse:
    record = Listing(**payload.model_dump())
    db.add(record)
    await db.flush()
    return ListingResponse.model_validate(record)
