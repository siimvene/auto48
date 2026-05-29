"""Geo proximity tests.

Structure mirrors tests/test_search.py:
- Private sqlite file + private engine + dependency_overrides for full isolation.
- Unit tests for pure math helpers (haversine, bbox_deltas).
- Integration tests via an ASGI client that only mounts the geo router.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Temp file must be created before any module-level import that reads env vars.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="auto48-geo-test-")
os.close(_db_fd)

os.environ["AUTO48_ENVIRONMENT"] = "local"
os.environ["AUTO48_DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"

import auto48.models  # noqa: F401, E402 — registers all ORM metadata
from auto48.api.routers import geo  # noqa: E402
from auto48.db import Base, get_db  # noqa: E402
from auto48.models.listing import Listing, ListingStatus  # noqa: E402
from auto48.models.seller import SellerProfile, SellerType  # noqa: E402
from auto48.models.user import User  # noqa: E402
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle  # noqa: E402
from auto48.services.geo import EARTH_RADIUS_KM, bbox_deltas, haversine  # noqa: E402

# ── Private engine ───────────────────────────────────────────────────────────

_engine = create_async_engine(f"sqlite+aiosqlite:///{_db_path}", echo=False)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def _override_get_db():
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def _lifespan(app: FastAPI):
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await _engine.dispose()


def _make_geo_app() -> FastAPI:
    app = FastAPI(lifespan=_lifespan)
    app.include_router(geo.router)
    app.dependency_overrides[get_db] = _override_get_db
    return app


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def geo_client():
    """Single ASGI client for the module; schema created once via lifespan."""
    app = _make_geo_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


# Real Estonian coordinates used for seeding.
# Tallinn city centre ≈ (59.437, 24.754)
# Tartu city centre   ≈ (58.378, 26.729) — ~161 km from Tallinn
# Narva city centre   ≈ (59.377, 28.179) — ~170 km from Tallinn
_TALLINN = (59.437, 24.754)
_TARTU   = (58.378, 26.729)
_NARVA   = (59.377, 28.179)
# A point very close to Tallinn (~1 km off) — inside any reasonable radius.
_NEAR_TALLINN = (59.444, 24.762)


@pytest.fixture(scope="module")
async def seeded_data(geo_client):  # noqa: ARG001 — client drives lifespan
    """Seed listings with known coordinates; return label→listing_id mapping."""
    async with _session_factory() as session:
        user = User(email="geo-test@example.com", display_name="Geo Tester")
        session.add(user)
        await session.flush()
        seller = SellerProfile(user_id=user.id, type=SellerType.PRIVATE)
        session.add(seller)
        await session.flush()
        sid = seller.id

        def _vehicle(make: str, model: str) -> Vehicle:
            return Vehicle(
                make=make,
                model=model,
                year=2020,
                fuel=FuelType.PETROL,
                body=BodyType.SEDAN,
                transmission=Transmission.MANUAL,
            )

        ids: dict[str, int] = {}

        rows: list[tuple[str, float | None, float | None, ListingStatus]] = [
            # label,          lat,               lon,               status
            ("near_tallinn",  _NEAR_TALLINN[0],  _NEAR_TALLINN[1], ListingStatus.ACTIVE),
            ("tartu",         _TARTU[0],         _TARTU[1],        ListingStatus.ACTIVE),
            ("narva",         _NARVA[0],         _NARVA[1],        ListingStatus.ACTIVE),
            # Active but null coords — must be excluded from nearby results.
            ("no_coords",     None,              None,             ListingStatus.ACTIVE),
            # Draft inside radius — must be excluded because not ACTIVE.
            ("draft_inside",  _NEAR_TALLINN[0],  _NEAR_TALLINN[1], ListingStatus.DRAFT),
        ]

        for label, lat, lon, lst_status in rows:
            # Use UNIQUE make+model per row so conftest's DB never interferes.
            v = _vehicle(f"GeoMake-{label}", f"GeoModel-{label}")
            session.add(v)
            await session.flush()

            listing = Listing(
                seller_id=sid,
                vehicle_id=v.id,
                title=f"Geo listing {label}",
                price_eur_cents=100_000,
                lat=lat,
                lon=lon,
                status=lst_status,
            )
            session.add(listing)
            await session.flush()
            ids[label] = listing.id

        await session.commit()
        return ids


# ── Unit tests: pure math ─────────────────────────────────────────────────────

def test_haversine_tallinn_tartu():
    """Tallinn ↔ Tartu is ~161 km (tolerance ±3 km)."""
    dist = haversine(_TALLINN[0], _TALLINN[1], _TARTU[0], _TARTU[1])
    assert abs(dist - 161.0) < 3.0, f"Expected ~161 km, got {dist:.1f} km"


def test_haversine_symmetry():
    """haversine(A, B) == haversine(B, A)."""
    d1 = haversine(_TALLINN[0], _TALLINN[1], _TARTU[0], _TARTU[1])
    d2 = haversine(_TARTU[0], _TARTU[1], _TALLINN[0], _TALLINN[1])
    assert abs(d1 - d2) < 1e-9


def test_haversine_zero():
    """Distance from a point to itself is 0."""
    assert haversine(59.437, 24.754, 59.437, 24.754) == pytest.approx(0.0, abs=1e-9)


def test_bbox_deltas_positive():
    """bbox_deltas returns positive values for a reasonable radius and latitude."""
    d_lat, d_lon = bbox_deltas(50.0, 59.0)
    assert d_lat > 0.0
    assert d_lon > 0.0


def test_bbox_deltas_lon_wider_than_lat_at_estonian_lat():
    """At ~58–59°N, cos≈0.52, so Δlon > Δlat (cos in denominator shrinks it)."""
    d_lat, d_lon = bbox_deltas(50.0, 59.0)
    # cos(59°) ≈ 0.515 → d_lon ≈ d_lat / 0.515 > d_lat
    assert d_lon > d_lat, f"Expected d_lon > d_lat, got d_lon={d_lon:.4f} d_lat={d_lat:.4f}"


def test_bbox_deltas_scales_with_radius():
    """Doubling the radius doubles both deltas."""
    d_lat_1, d_lon_1 = bbox_deltas(50.0, 59.0)
    d_lat_2, d_lon_2 = bbox_deltas(100.0, 59.0)
    assert d_lat_2 == pytest.approx(d_lat_1 * 2, rel=1e-6)
    assert d_lon_2 == pytest.approx(d_lon_1 * 2, rel=1e-6)


def test_earth_radius_constant():
    """EARTH_RADIUS_KM is the standard value."""
    assert pytest.approx(6371.0, rel=1e-3) == EARTH_RADIUS_KM


# ── Integration tests: GET /v1/listings/nearby ────────────────────────────────

async def test_nearby_returns_only_inside_radius(geo_client, seeded_data):
    """With radius=10 km centred on Tallinn, only near_tallinn is returned."""
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": _TALLINN[0], "lon": _TALLINN[1], "radius_km": 10},
    )
    assert resp.status_code == 200
    items = resp.json()
    labels = {item["listing"]["title"].split()[-1] for item in items}
    assert "near_tallinn" in labels
    assert "tartu" not in labels
    assert "narva" not in labels


async def test_nearby_excludes_null_coords(geo_client, seeded_data):
    """Listings with null lat/lon are never returned regardless of radius."""
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": _TALLINN[0], "lon": _TALLINN[1], "radius_km": 99999},
    )
    assert resp.status_code == 200
    items = resp.json()
    titles = [item["listing"]["title"] for item in items]
    assert all("no_coords" not in t for t in titles)


async def test_nearby_excludes_draft_inside_radius(geo_client, seeded_data):
    """DRAFT listing at same coords as near_tallinn must not appear."""
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": _TALLINN[0], "lon": _TALLINN[1], "radius_km": 10},
    )
    assert resp.status_code == 200
    items = resp.json()
    titles = [item["listing"]["title"] for item in items]
    assert all("draft_inside" not in t for t in titles)


async def test_nearby_sorted_nearest_first(geo_client, seeded_data):
    """All active listings in a large radius come back sorted ascending by distance_km."""
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": _TALLINN[0], "lon": _TALLINN[1], "radius_km": 99999},
    )
    assert resp.status_code == 200
    items = resp.json()
    distances = [item["distance_km"] for item in items]
    assert distances == sorted(distances)


async def test_nearby_distance_km_field_present(geo_client, seeded_data):
    """Each result has a positive distance_km field."""
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": _TALLINN[0], "lon": _TALLINN[1], "radius_km": 99999},
    )
    assert resp.status_code == 200
    for item in resp.json():
        assert "distance_km" in item
        assert item["distance_km"] >= 0.0


async def test_nearby_listing_response_shape(geo_client, seeded_data):
    """Each nearby item wraps a full ListingResponse under the 'listing' key."""
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": _TALLINN[0], "lon": _TALLINN[1], "radius_km": 99999},
    )
    assert resp.status_code == 200
    for item in resp.json():
        lst = item["listing"]
        assert "id" in lst
        assert "vehicle" in lst
        assert "price_eur_cents" in lst
        assert "status" in lst


async def test_nearby_empty_when_nothing_in_radius(geo_client, seeded_data):
    """A radius of 0.001 km from a spot with no listing returns an empty list."""
    resp = await geo_client.get(
        "/v1/listings/nearby",
        # Middle of the Baltic Sea
        params={"lat": 57.0, "lon": 20.0, "radius_km": 0.001},
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Validation / 400 tests ────────────────────────────────────────────────────

async def test_nearby_invalid_lat_too_high(geo_client):
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": 91.0, "lon": 24.0, "radius_km": 50},
    )
    assert resp.status_code == 400


async def test_nearby_invalid_lat_too_low(geo_client):
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": -91.0, "lon": 24.0, "radius_km": 50},
    )
    assert resp.status_code == 400


async def test_nearby_invalid_lon_too_high(geo_client):
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": 59.0, "lon": 181.0, "radius_km": 50},
    )
    assert resp.status_code == 400


async def test_nearby_invalid_lon_too_low(geo_client):
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": 59.0, "lon": -181.0, "radius_km": 50},
    )
    assert resp.status_code == 400


async def test_nearby_invalid_radius_zero(geo_client):
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": 59.0, "lon": 24.0, "radius_km": 0},
    )
    assert resp.status_code == 400


async def test_nearby_invalid_radius_negative(geo_client):
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": 59.0, "lon": 24.0, "radius_km": -10},
    )
    assert resp.status_code == 400


async def test_nearby_limit_respected(geo_client, seeded_data):
    """limit=1 returns at most one result even if more are in radius."""
    resp = await geo_client.get(
        "/v1/listings/nearby",
        params={"lat": _TALLINN[0], "lon": _TALLINN[1], "radius_km": 99999, "limit": 1},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    if os.path.exists(_db_path):
        os.remove(_db_path)
