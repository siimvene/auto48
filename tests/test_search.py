"""Faceted search tests for GET /v1/listings.

Uses a local FastAPI app that only mounts the listings router (not the full
create_app). A private engine+session-factory backed by a module-scoped temp
sqlite file is injected via dependency_overrides so these tests are fully
isolated from conftest.py's database — Toyota from test_health never appears.
"""

import os
import tempfile
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Temp file must exist before any module-level imports that trigger db.py loading.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="auto48-search-test-")
os.close(_db_fd)

# Force env vars before importing anything that reads them (db.py / config.py).
os.environ["AUTO48_ENVIRONMENT"] = "local"
os.environ["AUTO48_DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"

import auto48.models  # noqa: F401, E402 — registers all ORM metadata (users table etc.)
from auto48.api.routers import listings  # noqa: E402
from auto48.db import Base, get_db  # noqa: E402
from auto48.models.listing import Listing, ListingStatus  # noqa: E402
from auto48.models.seller import SellerProfile, SellerType  # noqa: E402
from auto48.models.user import User  # noqa: E402
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle  # noqa: E402

# ── Private engine wired to our temp file ────────────────────────────────────
_engine = create_async_engine(f"sqlite+aiosqlite:///{_db_path}", echo=False)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def _override_get_db():
    """Dependency override: yield sessions from the private engine, not the global one."""
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


def _make_search_app() -> FastAPI:
    app = FastAPI(lifespan=_lifespan)
    app.include_router(listings.router)
    # Wire our isolated DB into the listings router's DbSession dependency.
    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture(scope="module")
async def search_client():
    """Single ASGI client for the module; tables created once via lifespan."""
    app = _make_search_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


@pytest.fixture(scope="module")
async def seeded_data(search_client):  # noqa: ARG001 — client drives lifespan first
    """Seed a deterministic set of listings; returns label→listing_id mapping.

    Uses the private _session_factory so rows land in our isolated DB, never
    in the conftest DB.
    """
    async with _session_factory() as session:
        user = User(email="search-test@example.com", display_name="Search Tester")
        session.add(user)
        await session.flush()
        seller = SellerProfile(user_id=user.id, type=SellerType.PRIVATE)
        session.add(seller)
        await session.flush()
        sid = seller.id

        ids: dict[str, int] = {}

        # Build in-order so each vehicle flush happens inside the loop.
        seed_rows = [
            # (label, make, model, variant, year, fuel, body, transmission,
            #  price, mileage, location, status)
            ("octavia", "Skoda", "Octavia", None, 2018, FuelType.PETROL,
             BodyType.WAGON, Transmission.MANUAL, 800000, 120000, "Tartumaa",
             ListingStatus.ACTIVE),
            ("bmw3", "BMW", "3 Series", None, 2020, FuelType.DIESEL,
             BodyType.SEDAN, Transmission.AUTOMATIC, 2500000, 45000, "Harjumaa",
             ListingStatus.ACTIVE),
            ("tesla", "Tesla", "Model 3", None, 2022, FuelType.ELECTRIC,
             BodyType.SEDAN, Transmission.AUTOMATIC, 3800000, 18000, "Harjumaa",
             ListingStatus.ACTIVE),
            ("lada", "Lada", "2107", None, 1995, FuelType.PETROL,
             BodyType.SEDAN, Transmission.MANUAL, 50000, 300000, "Viljandimaa",
             ListingStatus.ACTIVE),
            ("draft_fabia", "Skoda", "Fabia", None, 2017, FuelType.PETROL,
             BodyType.HATCHBACK, Transmission.MANUAL, 600000, None, None,
             ListingStatus.DRAFT),
        ]

        for (
            label, make, model, variant, year, fuel, body, transmission,
            price, mileage, location, lst_status,
        ) in seed_rows:
            vehicle = Vehicle(
                make=make, model=model, variant=variant, year=year,
                fuel=fuel, body=body, transmission=transmission,
            )
            session.add(vehicle)
            await session.flush()  # populate vehicle.id

            listing = Listing(
                seller_id=sid,
                vehicle_id=vehicle.id,
                title=f"Test listing {label}",
                description=f"Description for {label}",
                price_eur_cents=price,
                mileage_km=mileage,
                location_county=location,
                status=lst_status,
            )
            session.add(listing)
            await session.flush()
            ids[label] = listing.id

        await session.commit()
        return ids


# ── Filter tests ─────────────────────────────────────────────────────────────

async def test_make_ilike(search_client, seeded_data):
    """make= is a case-insensitive substring match."""
    resp = await search_client.get("/v1/listings", params={"make": "skoda"})
    assert resp.status_code == 200
    body = resp.json()
    # Two Skodas seeded (active Octavia + draft Fabia); no status filter → both
    assert body["total"] == 2
    makes = {item["vehicle"]["make"] for item in body["items"]}
    assert makes == {"Skoda"}


async def test_model_ilike(search_client, seeded_data):
    resp = await search_client.get("/v1/listings", params={"model": "3 series"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["vehicle"]["model"] == "3 Series"


async def test_year_range(search_client, seeded_data):
    """year_min / year_max filter."""
    resp = await search_client.get(
        "/v1/listings", params={"year_min": 2018, "year_max": 2021}
    )
    assert resp.status_code == 200
    years = [item["vehicle"]["year"] for item in resp.json()["items"]]
    assert all(2018 <= y <= 2021 for y in years)
    # Octavia (2018) + BMW (2020); Lada (1995), Tesla (2022), draft Fabia (2017) excluded
    assert len(years) == 2


async def test_price_range_cents(search_client, seeded_data):
    """price_min / price_max work in EUR cents."""
    resp = await search_client.get(
        "/v1/listings", params={"price_min": 700000, "price_max": 2600000}
    )
    assert resp.status_code == 200
    prices = [item["price_eur_cents"] for item in resp.json()["items"]]
    assert all(700000 <= p <= 2600000 for p in prices)
    # Octavia (800000) + BMW (2500000);
    # draft Fabia (600000) + Lada (50000) + Tesla (3800000) excluded
    assert len(prices) == 2


async def test_mileage_max(search_client, seeded_data):
    resp = await search_client.get("/v1/listings", params={"mileage_max": 50000})
    assert resp.status_code == 200
    items = resp.json()["items"]
    # BMW (45000) + Tesla (18000); draft_fabia NULL excluded, Lada/Octavia too high
    assert all(
        item["mileage_km"] is not None and item["mileage_km"] <= 50000
        for item in items
    )
    assert len(items) == 2


async def test_fuel_enum(search_client, seeded_data):
    resp = await search_client.get("/v1/listings", params={"fuel": "electric"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["vehicle"]["fuel"] == "electric"


async def test_body_enum(search_client, seeded_data):
    resp = await search_client.get("/v1/listings", params={"body": "sedan"})
    assert resp.status_code == 200
    body = resp.json()
    # BMW + Tesla + Lada are sedans
    assert body["total"] == 3


async def test_transmission_enum(search_client, seeded_data):
    resp = await search_client.get("/v1/listings", params={"transmission": "automatic"})
    assert resp.status_code == 200
    body = resp.json()
    # BMW + Tesla
    assert body["total"] == 2


async def test_location_ilike(search_client, seeded_data):
    resp = await search_client.get("/v1/listings", params={"location": "harjumaa"})
    assert resp.status_code == 200
    body = resp.json()
    # BMW + Tesla
    assert body["total"] == 2
    for item in body["items"]:
        assert item["location_county"] is not None
        assert "Harjumaa" in item["location_county"]


async def test_q_freetext(search_client, seeded_data):
    """q matches vehicle model substring."""
    resp = await search_client.get("/v1/listings", params={"q": "octavia"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    models = [item["vehicle"]["model"] for item in body["items"]]
    assert "Octavia" in models


async def test_status_filter(search_client, seeded_data):
    """Explicit status= filter narrows results."""
    resp = await search_client.get("/v1/listings", params={"status": "draft"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "draft"


async def test_status_default_returns_all(search_client, seeded_data):
    """Without status filter all statuses are returned."""
    resp = await search_client.get("/v1/listings")
    assert resp.status_code == 200
    statuses = {item["status"] for item in resp.json()["items"]}
    assert "draft" in statuses
    assert "active" in statuses


async def test_combined_filters(search_client, seeded_data):
    """make + transmission together narrow correctly."""
    resp = await search_client.get(
        "/v1/listings", params={"make": "bmw", "transmission": "automatic"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["vehicle"]["make"] == "BMW"


# ── Sort tests ────────────────────────────────────────────────────────────────

async def test_sort_price_asc(search_client, seeded_data):
    resp = await search_client.get("/v1/listings", params={"sort": "price_asc"})
    assert resp.status_code == 200
    prices = [item["price_eur_cents"] for item in resp.json()["items"]]
    assert prices == sorted(prices)


async def test_sort_price_desc(search_client, seeded_data):
    resp = await search_client.get("/v1/listings", params={"sort": "price_desc"})
    assert resp.status_code == 200
    prices = [item["price_eur_cents"] for item in resp.json()["items"]]
    assert prices == sorted(prices, reverse=True)


async def test_sort_year_desc(search_client, seeded_data):
    resp = await search_client.get("/v1/listings", params={"sort": "year_desc"})
    assert resp.status_code == 200
    years = [item["vehicle"]["year"] for item in resp.json()["items"]]
    assert years == sorted(years, reverse=True)


async def test_sort_newest_default(search_client, seeded_data):
    """Default sort is newest — response is valid and contains all seeded rows."""
    resp = await search_client.get("/v1/listings")
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


# ── Pagination tests ──────────────────────────────────────────────────────────

async def test_pagination_limit(search_client, seeded_data):
    resp = await search_client.get("/v1/listings", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["total"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 0


async def test_pagination_offset(search_client, seeded_data):
    all_resp = await search_client.get(
        "/v1/listings", params={"sort": "price_asc", "limit": 100}
    )
    all_ids = [item["id"] for item in all_resp.json()["items"]]

    page2_resp = await search_client.get(
        "/v1/listings", params={"sort": "price_asc", "limit": 2, "offset": 2}
    )
    page2_ids = [item["id"] for item in page2_resp.json()["items"]]
    assert page2_ids == all_ids[2:4]


async def test_pagination_empty_offset(search_client, seeded_data):
    resp = await search_client.get("/v1/listings", params={"offset": 9999})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 5


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    if os.path.exists(_db_path):
        os.remove(_db_path)
