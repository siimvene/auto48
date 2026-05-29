"""Dealer analytics service: aggregate SQL queries for the dashboard.

All aggregation is performed in the database (grouped func.count/avg/sum) — no
Python-side full-table scans.  The function returns typed dataclass instances
that map 1-to-1 to the Pydantic response schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto48.models.conversation import Conversation
from auto48.models.dealer_feed import DealerFeed, IngestRun
from auto48.models.listing import Listing, ListingStatus
from auto48.models.test_drive import TestDriveBooking
from auto48.models.vehicle import Vehicle

# How many top items to return for the breakdown lists.
_TOP_N = 10


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ListingCounts:
    total: int
    active: int
    sold: int
    draft: int
    expired: int


@dataclass
class InventoryValue:
    total_eur_cents: int
    avg_eur_cents: float


@dataclass
class MakeBreakdownItem:
    make: str
    count: int
    avg_price_eur_cents: float


@dataclass
class BodyBreakdownItem:
    body: str
    count: int
    avg_price_eur_cents: float


@dataclass
class TestDriveByStatus:
    status: str
    count: int


@dataclass
class FeedHealth:
    feed_id: int
    status: str
    created_count: int
    updated_count: int
    error_count: int


@dataclass
class DealerAnalytics:
    listing_counts: ListingCounts
    inventory_value: InventoryValue
    top_makes: list[MakeBreakdownItem]
    top_bodies: list[BodyBreakdownItem]
    total_leads: int
    total_test_drives: int
    test_drives_by_status: list[TestDriveByStatus]
    feed_health: list[FeedHealth] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Private query helpers
# ---------------------------------------------------------------------------


async def _listing_counts(db: AsyncSession, seller_profile_id: int) -> ListingCounts:
    """Return per-status listing counts for the given seller."""
    stmt = (
        select(Listing.status, func.count(Listing.id).label("cnt"))
        .where(Listing.seller_id == seller_profile_id)
        .group_by(Listing.status)
    )
    rows = (await db.execute(stmt)).all()

    by_status: dict[str, int] = {row.status.value: row.cnt for row in rows}
    total = sum(by_status.values())
    return ListingCounts(
        total=total,
        active=by_status.get(ListingStatus.ACTIVE.value, 0),
        sold=by_status.get(ListingStatus.SOLD.value, 0),
        draft=by_status.get(ListingStatus.DRAFT.value, 0),
        expired=by_status.get(ListingStatus.EXPIRED.value, 0),
    )


async def _inventory_value(db: AsyncSession, seller_profile_id: int) -> InventoryValue:
    """Return total + average price of ACTIVE listings."""
    stmt = select(
        func.coalesce(func.sum(Listing.price_eur_cents), 0).label("total"),
        func.coalesce(func.avg(Listing.price_eur_cents), 0.0).label("avg"),
    ).where(
        Listing.seller_id == seller_profile_id,
        Listing.status == ListingStatus.ACTIVE,
    )
    row = (await db.execute(stmt)).one()
    return InventoryValue(
        total_eur_cents=int(row.total),
        avg_eur_cents=float(row.avg),
    )


async def _make_breakdown(
    db: AsyncSession, seller_profile_id: int
) -> list[MakeBreakdownItem]:
    """Return top-N makes by listing count, with avg price."""
    stmt = (
        select(
            Vehicle.make,
            func.count(Listing.id).label("cnt"),
            func.avg(Listing.price_eur_cents).label("avg_price"),
        )
        .join(Vehicle, Listing.vehicle_id == Vehicle.id)
        .where(Listing.seller_id == seller_profile_id)
        .group_by(Vehicle.make)
        .order_by(func.count(Listing.id).desc())
        .limit(_TOP_N)
    )
    rows = (await db.execute(stmt)).all()
    return [
        MakeBreakdownItem(
            make=row.make,
            count=row.cnt,
            avg_price_eur_cents=float(row.avg_price) if row.avg_price is not None else 0.0,
        )
        for row in rows
    ]


async def _body_breakdown(
    db: AsyncSession, seller_profile_id: int
) -> list[BodyBreakdownItem]:
    """Return top-N body types by listing count, with avg price."""
    stmt = (
        select(
            Vehicle.body,
            func.count(Listing.id).label("cnt"),
            func.avg(Listing.price_eur_cents).label("avg_price"),
        )
        .join(Vehicle, Listing.vehicle_id == Vehicle.id)
        .where(Listing.seller_id == seller_profile_id)
        .group_by(Vehicle.body)
        .order_by(func.count(Listing.id).desc())
        .limit(_TOP_N)
    )
    rows = (await db.execute(stmt)).all()
    return [
        BodyBreakdownItem(
            body=row.body.value if hasattr(row.body, "value") else str(row.body),
            count=row.cnt,
            avg_price_eur_cents=float(row.avg_price) if row.avg_price is not None else 0.0,
        )
        for row in rows
    ]


async def _total_leads(db: AsyncSession, seller_profile_id: int) -> int:
    """Count Conversations on this dealer's listings."""
    stmt = (
        select(func.count(Conversation.id))
        .join(Listing, Conversation.listing_id == Listing.id)
        .where(Listing.seller_id == seller_profile_id)
    )
    result = await db.scalar(stmt)
    return int(result) if result is not None else 0


async def _test_drive_counts(
    db: AsyncSession, seller_profile_id: int
) -> tuple[int, list[TestDriveByStatus]]:
    """Return total test-drive count and per-status breakdown."""
    stmt = (
        select(TestDriveBooking.status, func.count(TestDriveBooking.id).label("cnt"))
        .join(Listing, TestDriveBooking.listing_id == Listing.id)
        .where(Listing.seller_id == seller_profile_id)
        .group_by(TestDriveBooking.status)
    )
    rows = (await db.execute(stmt)).all()
    by_status = [
        TestDriveByStatus(
            status=row.status.value if hasattr(row.status, "value") else str(row.status),
            count=row.cnt,
        )
        for row in rows
    ]
    total = sum(item.count for item in by_status)
    return total, by_status


async def _feed_health(db: AsyncSession, seller_profile_id: int) -> list[FeedHealth]:
    """Return the latest IngestRun summary for each of the dealer's feeds.

    Uses a max(started_at)-per-feed self-join to avoid window functions for
    sqlite compatibility.
    """
    # Sub-query: max started_at per feed
    sub = (
        select(
            IngestRun.feed_id.label("feed_id"),
            func.max(IngestRun.started_at).label("max_started"),
        )
        .join(DealerFeed, IngestRun.feed_id == DealerFeed.id)
        .where(DealerFeed.seller_id == seller_profile_id)
        .group_by(IngestRun.feed_id)
        .subquery()
    )

    stmt = (
        select(
            IngestRun.feed_id,
            IngestRun.status,
            IngestRun.created_count,
            IngestRun.updated_count,
            IngestRun.error_count,
        )
        .join(
            sub,
            (IngestRun.feed_id == sub.c.feed_id)
            & (IngestRun.started_at == sub.c.max_started),
        )
    )
    rows = (await db.execute(stmt)).all()
    return [
        FeedHealth(
            feed_id=row.feed_id,
            status=row.status.value if hasattr(row.status, "value") else str(row.status),
            created_count=row.created_count,
            updated_count=row.updated_count,
            error_count=row.error_count,
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def compute_dealer_analytics(
    db: AsyncSession,
    seller_profile_id: int,
) -> DealerAnalytics:
    """Aggregate all dealer dashboard metrics for *seller_profile_id*.

    Performs multiple focused SQL queries — no Python-side full-table scans.
    """
    counts = await _listing_counts(db, seller_profile_id)
    value = await _inventory_value(db, seller_profile_id)
    makes = await _make_breakdown(db, seller_profile_id)
    bodies = await _body_breakdown(db, seller_profile_id)
    leads = await _total_leads(db, seller_profile_id)
    total_td, td_by_status = await _test_drive_counts(db, seller_profile_id)
    feeds = await _feed_health(db, seller_profile_id)

    return DealerAnalytics(
        listing_counts=counts,
        inventory_value=value,
        top_makes=makes,
        top_bodies=bodies,
        total_leads=leads,
        total_test_drives=total_td,
        test_drives_by_status=td_by_status,
        feed_health=feeds,
    )
