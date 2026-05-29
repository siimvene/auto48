"""Saved-search CRUD and alert-dispatch service.

Pure async functions; session and adapters injected by callers (no global state).
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from auto48.models.listing import Listing, ListingStatus
from auto48.models.saved_search import Alert, SavedSearch
from auto48.models.vehicle import BodyType, FuelType, Transmission
from auto48.services.search import build_filters, build_listing_query

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from auto48.ports.notify import NotifyPort


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


async def create_saved_search(
    db: AsyncSession,
    *,
    user_id: int,
    name: str,
    query: dict[str, Any],
) -> SavedSearch:
    """Persist a new SavedSearch for *user_id* and return it."""
    saved_search = SavedSearch(user_id=user_id, name=name, query=query)
    db.add(saved_search)
    await db.flush()
    return saved_search


async def list_saved_searches(
    db: AsyncSession,
    *,
    user_id: int,
) -> list[SavedSearch]:
    """Return all saved searches owned by *user_id*, newest first."""
    rows = await db.scalars(
        select(SavedSearch)
        .where(SavedSearch.user_id == user_id)
        .order_by(SavedSearch.created_at.desc(), SavedSearch.id.desc())
    )
    return list(rows.all())


async def get_saved_search(
    db: AsyncSession,
    *,
    saved_search_id: int,
) -> SavedSearch | None:
    """Return a single SavedSearch by primary key, or None."""
    result: SavedSearch | None = await db.scalar(
        select(SavedSearch).where(SavedSearch.id == saved_search_id)
    )
    return result


async def delete_saved_search(
    db: AsyncSession,
    *,
    saved_search: SavedSearch,
) -> None:
    """Hard-delete *saved_search* (cascades to Alert rows via FK)."""
    await db.delete(saved_search)
    await db.flush()


# ---------------------------------------------------------------------------
# Filter-bridge helpers
# ---------------------------------------------------------------------------


def _coerce_enum(value: str | None, enum_cls: type[enum.Enum]) -> Any:
    """Convert a plain string from the JSON query blob to the matching enum member.

    Returns None if *value* is None or does not match any member value.
    """
    if value is None:
        return None
    for member in enum_cls:
        if member.value == value:
            return member
    return None


def _query_to_filter_kwargs(query: dict[str, Any]) -> dict[str, Any]:
    """Map a saved-search query dict to keyword arguments accepted by build_filters."""
    return {
        "make": query.get("make"),
        "model": query.get("model"),
        "year_min": query.get("year_min"),
        "year_max": query.get("year_max"),
        "price_min": query.get("price_min"),
        "price_max": query.get("price_max"),
        "fuel": _coerce_enum(query.get("fuel"), FuelType),
        "body": _coerce_enum(query.get("body"), BodyType),
        "transmission": _coerce_enum(query.get("transmission"), Transmission),
        "location": query.get("location"),
        # Always restrict to ACTIVE listings for alert matching.
        "status": ListingStatus.ACTIVE,
    }


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


async def find_matches(
    db: AsyncSession,
    saved_search: SavedSearch,
) -> list[Listing]:
    """Return ACTIVE listings that match *saved_search.query*.

    Reuses build_filters from services.search so the facet logic stays in one place.
    """
    kwargs = _query_to_filter_kwargs(saved_search.query)
    filters = build_filters(**kwargs)
    stmt = build_listing_query(filters, sort="newest", limit=200, offset=0)
    rows = await db.scalars(stmt)
    return list(rows.all())


# ---------------------------------------------------------------------------
# Alert dispatch
# ---------------------------------------------------------------------------


async def run_alerts(
    db: AsyncSession,
    notify_adapter: NotifyPort,
) -> None:
    """For every active SavedSearch find new matching listings and send alerts.

    Algorithm (per saved search):
      1. Load all listing ids already alerted (via Alert table) to deduplicate.
      2. Run find_matches to get current matching ACTIVE listings.
      3. Filter to those not already alerted.
      4. Insert Alert rows for new matches.
      5. If any new matches exist, send a single summary email and mark them
         notified=True; update last_notified_at.
    """
    active_searches = await db.scalars(
        select(SavedSearch)
        .where(SavedSearch.active.is_(True))
        .options(selectinload(SavedSearch.alerts))
    )

    for saved_search in active_searches.all():
        # Set of listing ids already recorded for this search.
        already_alerted: set[int] = {a.listing_id for a in saved_search.alerts}

        matches = await find_matches(db, saved_search)
        new_matches = [m for m in matches if m.id not in already_alerted]

        if not new_matches:
            continue

        # Persist Alert rows.
        alert_rows: list[Alert] = []
        for listing in new_matches:
            alert = Alert(
                saved_search_id=saved_search.id,
                listing_id=listing.id,
                notified=False,
            )
            db.add(alert)
            alert_rows.append(alert)

        await db.flush()

        # Fetch the owner's email via the relationship (already loaded on User
        # side; user_id is available directly).
        user_result = await db.scalar(
            select(SavedSearch)
            .where(SavedSearch.id == saved_search.id)
            .options(selectinload(SavedSearch.user))
        )
        owner_email = user_result.user.email if user_result is not None else None
        if owner_email is None:
            continue

        subject = (
            f"auto48: {len(new_matches)} new match(es) for '{saved_search.name}'"
        )
        lines = [
            f"Your saved search '{saved_search.name}' has {len(new_matches)} new listing(s):",
            "",
        ]
        for listing in new_matches:
            lines.append(f"  • Listing #{listing.id}: {listing.title}")
        body = "\n".join(lines)

        await notify_adapter.send_email(to=owner_email, subject=subject, body=body)

        # Mark all new alert rows as notified.
        for alert in alert_rows:
            alert.notified = True

        saved_search.last_notified_at = datetime.now(tz=UTC)

    await db.flush()
