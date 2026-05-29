"""Test-drive scheduling service functions.

All functions accept an AsyncSession and return ORM objects. Callers are
responsible for committing the session.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto48.models.listing import Listing
from auto48.models.seller import SellerProfile
from auto48.models.test_drive import TestDriveBooking, TestDriveStatus


class PermissionError(Exception):
    """Raised when an actor is not authorised to change a booking's status."""


async def request_test_drive(
    db: AsyncSession,
    listing_id: int,
    requester_id: int,
    slot_at: datetime,
    note: str | None,
) -> TestDriveBooking:
    """Create a new test-drive booking for *requester_id* on *listing_id*.

    Raises ``ValueError`` if the listing does not exist.
    """
    listing = await db.get(Listing, listing_id)
    if listing is None:
        raise ValueError(f"Listing {listing_id} not found")

    booking = TestDriveBooking(
        listing_id=listing_id,
        requester_id=requester_id,
        slot_at=slot_at,
        note=note,
        status=TestDriveStatus.REQUESTED,
    )
    db.add(booking)
    await db.flush()
    await db.refresh(booking)
    return booking


async def set_status(
    db: AsyncSession,
    booking_id: int,
    actor_user_id: int,
    new_status: TestDriveStatus,
) -> TestDriveBooking:
    """Transition a booking to *new_status*.

    Rules:
    - ``CONFIRMED`` / ``DECLINED`` — only the listing's seller user (resolved via
      ``Listing.seller_id → SellerProfile.user_id``).
    - ``CANCELLED`` — only the requester.

    Raises:
        ``ValueError`` if the booking does not exist.
        ``PermissionError`` if *actor_user_id* is not authorised.
    """
    booking = await db.get(TestDriveBooking, booking_id)
    if booking is None:
        raise ValueError(f"TestDriveBooking {booking_id} not found")

    if new_status in (TestDriveStatus.CONFIRMED, TestDriveStatus.DECLINED):
        # Resolve listing → seller_profile → user
        listing = await db.get(Listing, booking.listing_id)
        if listing is None:
            raise ValueError(f"Listing {booking.listing_id} not found")
        profile = await db.get(SellerProfile, listing.seller_id)
        if profile is None:
            raise ValueError(f"SellerProfile {listing.seller_id} not found")
        if actor_user_id != profile.user_id:
            raise PermissionError(
                "Only the listing's seller may confirm or decline a test-drive booking"
            )
    elif new_status == TestDriveStatus.CANCELLED:
        if actor_user_id != booking.requester_id:
            raise PermissionError(
                "Only the requester may cancel a test-drive booking"
            )

    booking.status = new_status
    await db.flush()
    await db.refresh(booking)
    return booking


async def list_for_user(
    db: AsyncSession,
    user_id: int,
) -> list[TestDriveBooking]:
    """Return all bookings where *user_id* is the requester OR the listing's seller.

    The seller side is determined by joining through SellerProfile.
    """
    # Subquery: listing_ids where user is the seller
    seller_listing_subq = (
        select(Listing.id)
        .join(SellerProfile, Listing.seller_id == SellerProfile.id)
        .where(SellerProfile.user_id == user_id)
        .scalar_subquery()
    )

    rows = await db.scalars(
        select(TestDriveBooking).where(
            or_(
                TestDriveBooking.requester_id == user_id,
                TestDriveBooking.listing_id.in_(seller_listing_subq),
            )
        )
    )
    return list(rows.all())


async def list_for_listing(
    db: AsyncSession,
    listing_id: int,
) -> list[TestDriveBooking]:
    """Return all bookings for *listing_id*."""
    rows = await db.scalars(
        select(TestDriveBooking).where(TestDriveBooking.listing_id == listing_id)
    )
    return list(rows.all())
