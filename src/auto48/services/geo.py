"""Geo proximity service: bounding-box prefilter in SQL + haversine in Python.

Design:
- `bbox_deltas` and `haversine` are pure, unit-testable helpers.
- `nearby` performs the bounding-box SQL query, then filters/sorts in Python
  by precise haversine distance.  The SQL limit() is intentionally omitted so
  that the Python sort can pick the true nearest rows (not just the first N in
  storage order).
"""

from __future__ import annotations

import math

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from auto48.models.listing import Listing, ListingStatus

# ── Constants ────────────────────────────────────────────────────────────────

EARTH_RADIUS_KM: float = 6371.0
# 1 degree of latitude in km (true at all latitudes).
KM_PER_DEG_LAT: float = math.pi * EARTH_RADIUS_KM / 180.0
# Smallest cosine we allow when computing Δlon — prevents division by zero near
# geographic poles (cos(lat) → 0).  Estonia sits at ~57–59°N so this is never
# reached in practice; it keeps the helper honest.
_MIN_COS: float = 1e-6


# ── Pure math helpers ────────────────────────────────────────────────────────


def bbox_deltas(radius_km: float, lat: float) -> tuple[float, float]:
    """Return (delta_lat_deg, delta_lon_deg) for the bounding-box prefilter.

    Arguments:
        radius_km: search radius in kilometres (must be > 0).
        lat: centre latitude in decimal degrees.

    Returns:
        (d_lat, d_lon) — half-widths of the bounding box in degrees.
    """
    d_lat = radius_km / KM_PER_DEG_LAT
    cos_lat = max(abs(math.cos(math.radians(lat))), _MIN_COS)
    d_lon = radius_km / (KM_PER_DEG_LAT * cos_lat)
    return d_lat, d_lon


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance between two points in kilometres.

    Uses the haversine formula, accurate to within a fraction of a percent for
    distances up to a few thousand kilometres.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


# ── Async service function ───────────────────────────────────────────────────


async def nearby(
    db: AsyncSession,
    *,
    lat: float,
    lon: float,
    radius_km: float,
    limit: int = 50,
) -> list[tuple[Listing, float]]:
    """Return active listings within *radius_km* of (*lat*, *lon*), nearest-first.

    Strategy:
    1. Bounding-box WHERE clause in SQL reduces the candidate set to only rows
       that could possibly be within the radius (uses existing lat/lon indexes).
    2. Precise haversine distance is computed in Python; rows outside the true
       circle are discarded.
    3. Results are sorted ascending by distance; the *limit* nearest are returned.

    Only listings with status ACTIVE and non-null lat/lon are considered.

    Returns:
        List of (Listing, distance_km) tuples, sorted nearest-first.
    """
    d_lat, d_lon = bbox_deltas(radius_km, lat)

    lat_min = lat - d_lat
    lat_max = lat + d_lat
    lon_min = lon - d_lon
    lon_max = lon + d_lon

    stmt = (
        select(Listing)
        .where(
            and_(
                Listing.status == ListingStatus.ACTIVE,
                Listing.lat.is_not(None),
                Listing.lon.is_not(None),
                Listing.lat >= lat_min,
                Listing.lat <= lat_max,
                Listing.lon >= lon_min,
                Listing.lon <= lon_max,
            )
        )
        .options(selectinload(Listing.vehicle))
    )

    rows = (await db.scalars(stmt)).all()

    results: list[tuple[Listing, float]] = []
    for row in rows:
        # Narrow Optional[float] → float (mypy strict + runtime double-safety).
        if row.lat is None or row.lon is None:
            continue
        dist = haversine(lat, lon, row.lat, row.lon)
        if dist <= radius_km:
            results.append((row, dist))

    results.sort(key=lambda t: t[1])
    return results[:limit]
