"""Feed ingest service: fetch, parse, and upsert Vehicle+Listing rows.

A new IngestRun is created in RUNNING state, the feed is fetched and parsed,
and each ParsedListing is either inserted (new) or used to update an existing
Listing matched by VIN within the same seller.  Counts are updated and the run
is finalised as SUCCESS or ERROR.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auto48.models.dealer_feed import DealerFeed, FeedFormat, IngestRun, IngestStatus
from auto48.models.listing import Listing, ListingStatus
from auto48.models.vehicle import Vehicle
from auto48.ports.feed import FeedPort, ParsedListing

logger = logging.getLogger(__name__)


async def ingest_feed(
    db: AsyncSession,
    feed_id: int,
    fetch_adapter: FeedPort,
) -> IngestRun:
    """Load *feed_id*, fetch + parse its contents, and upsert Vehicle+Listing rows.

    Returns the completed IngestRun row (status SUCCESS or ERROR).
    The session is committed before returning so callers (workers, router) see
    the final state in a separate session.
    """
    # 1. Load the feed --------------------------------------------------------
    feed = await db.get(DealerFeed, feed_id)
    if feed is None:
        raise ValueError(f"DealerFeed {feed_id} not found")

    # 2. Create IngestRun (RUNNING) -------------------------------------------
    run = IngestRun(
        feed_id=feed_id,
        status=IngestStatus.RUNNING,
        started_at=datetime.now(tz=UTC),
    )
    db.add(run)
    await db.flush()  # populate run.id

    try:
        # 3. Fetch raw bytes --------------------------------------------------
        raw = await fetch_adapter.fetch(feed.url)

        # 4. Parse according to format ----------------------------------------
        from auto48.adapters.feed.parsers import parse_csv, parse_json

        if feed.format == FeedFormat.CSV:
            rows, parse_errors = parse_csv(raw)
        else:
            rows, parse_errors = parse_json(raw)

        run.error_count += parse_errors

        # 5. Upsert Vehicle + Listing rows ------------------------------------
        for parsed in rows:
            try:
                async with db.begin_nested():
                    await _upsert_listing(db, feed, parsed, run)
            except Exception as exc:
                run.error_count += 1
                logger.warning(
                    "ingest_feed: row upsert failed feed=%d: %s", feed_id, exc
                )

        # 6. Mark success -----------------------------------------------------
        run.status = IngestStatus.SUCCESS

    except Exception as exc:
        logger.error("ingest_feed: fatal error feed=%d: %s", feed_id, exc)
        run.status = IngestStatus.ERROR
        run.error_detail = {"message": str(exc)}

    finally:
        run.finished_at = datetime.now(tz=UTC)
        feed.last_run_at = run.finished_at
        await db.flush()

    await db.commit()
    return run


async def _upsert_listing(
    db: AsyncSession,
    feed: DealerFeed,
    parsed: ParsedListing,
    run: IngestRun,
) -> None:
    """Insert a new Listing+Vehicle or update an existing one matched by VIN."""
    existing_listing: Listing | None = None

    # Try to match an existing listing for this dealer by VIN
    if parsed.vin:
        existing_listing = await _find_listing_by_vin(db, feed.seller_id, parsed.vin)

    if existing_listing is not None:
        # Update mutable fields on the existing listing
        existing_listing.price_eur_cents = parsed.price_eur_cents
        if parsed.mileage_km is not None:
            existing_listing.mileage_km = parsed.mileage_km
        if parsed.location_county is not None:
            existing_listing.location_county = parsed.location_county
        run.updated_count += 1
    else:
        # Create a new Vehicle + Listing
        vehicle = Vehicle(
            make=parsed.make,
            model=parsed.model,
            year=parsed.year,
            fuel=parsed.fuel,
            body=parsed.body,
            transmission=parsed.transmission,
            variant=parsed.variant,
            drivetrain=parsed.drivetrain,
            vin=parsed.vin,
            plate=parsed.plate,
        )
        db.add(vehicle)
        await db.flush()  # populate vehicle.id

        listing = Listing(
            seller_id=feed.seller_id,
            vehicle_id=vehicle.id,
            title=parsed.title,
            description=parsed.description,
            price_eur_cents=parsed.price_eur_cents,
            mileage_km=parsed.mileage_km,
            location_county=parsed.location_county,
            status=ListingStatus.ACTIVE,
        )
        db.add(listing)
        await db.flush()
        run.created_count += 1


async def _find_listing_by_vin(
    db: AsyncSession,
    seller_id: int,
    vin: str,
) -> Listing | None:
    """Find an existing active listing for *seller_id* whose vehicle has the given VIN."""
    stmt = (
        select(Listing)
        .join(Vehicle, Listing.vehicle_id == Vehicle.id)
        .where(Listing.seller_id == seller_id)
        .where(Vehicle.vin == vin)
        .limit(1)
    )
    return cast("Listing | None", await db.scalar(stmt))
