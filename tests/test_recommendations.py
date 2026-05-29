"""Tests for the recommendations service and API router.

Uses an isolated sqlite file + local FastAPI app that only mounts the
recommendations router — no shared state with conftest.py's database.

Sentinel make/model "Zephyron"/"ZX9" is unique to this module so that even if
the sqlite file is shared between test runs the assertions stay stable.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Must be set before any auto48 import that touches db.py / config.py.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="auto48-reco-test-")
os.close(_db_fd)
os.environ.setdefault("AUTO48_ENVIRONMENT", "local")
os.environ["AUTO48_DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"

import auto48.models  # noqa: F401, E402 — register all ORM metadata
from auto48.api.routers import recommendations  # noqa: E402
from auto48.db import Base, get_db  # noqa: E402
from auto48.models.listing import Listing, ListingStatus  # noqa: E402
from auto48.models.seller import SellerProfile, SellerType  # noqa: E402
from auto48.models.user import User  # noqa: E402
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle  # noqa: E402

# ── Private engine / session factory ─────────────────────────────────────────

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
async def _lifespan(app: FastAPI):  # type: ignore[type-arg]
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await _engine.dispose()


def _make_reco_app() -> FastAPI:
    app = FastAPI(lifespan=_lifespan)
    app.include_router(recommendations.router)
    app.dependency_overrides[get_db] = _override_get_db
    return app


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
async def reco_client():
    app = _make_reco_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


@pytest.fixture(scope="module")
async def seeded(reco_client):  # noqa: ARG001 — client ensures lifespan ran
    """Seed deterministic listings; returns label→listing_id mapping.

    Sentinel make: "Zephyron" / model: "ZX9" — unique so the DB can be shared.

    Layout:
      seed        – SUV, 2020, petrol, 2 000 000 c (Zephyron ZX9)
      close_a     – SUV, 2020, petrol, 2 100 000 c (Zephyron ZX9) ← similar
      close_b     – SUV, 2019, diesel, 1 800 000 c (Zephyron ZX9) ← similar
      close_c     – SUV, 2021, petrol, 2 400 000 c (Zephyron ZX9) ← similar
      far_price   – SUV, 2020, petrol, 5 000 000 c (Zephyron ZX9) ← price too far
      far_year    – SUV, 2013, petrol, 2 000 000 c (Zephyron ZX9) ← year too far
      diff_body   – SEDAN, 2020, petrol, 2 000 000 c (Zephyron ZX9) ← body mismatch
      inactive    – SUV, 2020, petrol, 2 000 000 c (Zephyron ZX9) ← sold/inactive
    """
    async with _session_factory() as session:
        user = User(email="reco-test@example.com", display_name="Reco Tester")
        session.add(user)
        await session.flush()
        seller = SellerProfile(user_id=user.id, type=SellerType.PRIVATE)
        session.add(seller)
        await session.flush()
        sid = seller.id

        # (label, year, fuel, body, price_cents, status)
        SV = ListingStatus.ACTIVE
        SOLD = ListingStatus.SOLD
        rows: list[tuple[str, int, FuelType, BodyType, int, ListingStatus]] = [
            ("seed",      2020, FuelType.PETROL, BodyType.SUV,   2_000_000, SV),
            ("close_a",   2020, FuelType.PETROL, BodyType.SUV,   2_100_000, SV),
            ("close_b",   2019, FuelType.DIESEL, BodyType.SUV,   1_800_000, SV),
            ("close_c",   2021, FuelType.PETROL, BodyType.SUV,   2_400_000, SV),
            ("far_price", 2020, FuelType.PETROL, BodyType.SUV,   5_000_000, SV),
            ("far_year",  2013, FuelType.PETROL, BodyType.SUV,   2_000_000, SV),
            ("diff_body", 2020, FuelType.PETROL, BodyType.SEDAN, 2_000_000, SV),
            ("inactive",  2020, FuelType.PETROL, BodyType.SUV,   2_000_000, SOLD),
        ]

        ids: dict[str, int] = {}
        for label, year, fuel, body, price, lst_status in rows:
            vehicle = Vehicle(
                make="Zephyron", model="ZX9", year=year,
                fuel=fuel, body=body, transmission=Transmission.MANUAL,
            )
            session.add(vehicle)
            await session.flush()

            listing = Listing(
                seller_id=sid,
                vehicle_id=vehicle.id,
                title=f"Reco test {label}",
                price_eur_cents=price,
                status=lst_status,
            )
            session.add(listing)
            await session.flush()
            ids[label] = listing.id

        await session.commit()
        return ids


# ── similar_to endpoint ───────────────────────────────────────────────────────

async def test_similar_returns_close_listings(reco_client, seeded):
    """The three close-* listings appear; seed itself must be absent."""
    seed_id = seeded["seed"]
    resp = await reco_client.get(f"/v1/listings/{seed_id}/similar")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert seeded["close_a"] in ids
    assert seeded["close_b"] in ids
    assert seeded["close_c"] in ids


async def test_similar_excludes_seed(reco_client, seeded):
    seed_id = seeded["seed"]
    resp = await reco_client.get(f"/v1/listings/{seed_id}/similar")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert seed_id not in ids


async def test_similar_excludes_far_price(reco_client, seeded):
    seed_id = seeded["seed"]
    resp = await reco_client.get(f"/v1/listings/{seed_id}/similar")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert seeded["far_price"] not in ids


async def test_similar_excludes_far_year(reco_client, seeded):
    seed_id = seeded["seed"]
    resp = await reco_client.get(f"/v1/listings/{seed_id}/similar")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert seeded["far_year"] not in ids


async def test_similar_excludes_diff_body(reco_client, seeded):
    seed_id = seeded["seed"]
    resp = await reco_client.get(f"/v1/listings/{seed_id}/similar")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert seeded["diff_body"] not in ids


async def test_similar_excludes_inactive(reco_client, seeded):
    seed_id = seeded["seed"]
    resp = await reco_client.get(f"/v1/listings/{seed_id}/similar")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert seeded["inactive"] not in ids


async def test_similar_respects_limit(reco_client, seeded):
    seed_id = seeded["seed"]
    resp = await reco_client.get(f"/v1/listings/{seed_id}/similar", params={"limit": 1})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_similar_returns_list_response_shape(reco_client, seeded):
    seed_id = seeded["seed"]
    resp = await reco_client.get(f"/v1/listings/{seed_id}/similar")
    assert resp.status_code == 200
    for item in resp.json():
        assert "id" in item
        assert "vehicle" in item
        assert "price_eur_cents" in item


async def test_similar_404_for_missing_seed(reco_client, seeded):  # noqa: ARG001
    resp = await reco_client.get("/v1/listings/999999999/similar")
    assert resp.status_code == 404


async def test_similar_limit_validation(reco_client, seeded):  # noqa: ARG001
    """limit > 50 must be rejected."""
    seed_id = seeded["seed"]
    resp = await reco_client.get(f"/v1/listings/{seed_id}/similar", params={"limit": 51})
    assert resp.status_code == 422


# ── recommend endpoint ────────────────────────────────────────────────────────

async def test_recommend_no_filter_returns_active(reco_client, seeded):  # noqa: ARG001
    """Without filters only active Zephyron listings should appear (plus possibly
    listings from other test modules — we only assert the Zephyron ones behave)."""
    resp = await reco_client.get("/v1/recommendations", params={"make": "Zephyron"})
    assert resp.status_code == 200
    items = resp.json()
    statuses = {item["status"] for item in items}
    # Sold listing must not appear; all returned must be active
    assert "sold" not in statuses
    assert "draft" not in statuses


async def test_recommend_filters_by_make(reco_client, seeded):  # noqa: ARG001
    resp = await reco_client.get("/v1/recommendations", params={"make": "Zephyron"})
    assert resp.status_code == 200
    items = resp.json()
    assert all(item["vehicle"]["make"] == "Zephyron" for item in items)


async def test_recommend_filters_by_body(reco_client, seeded):
    resp = await reco_client.get(
        "/v1/recommendations",
        params={"make": "Zephyron", "body": "suv"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert all(item["vehicle"]["body"] == "suv" for item in items)
    # diff_body (sedan) must NOT appear
    assert seeded["diff_body"] not in {item["id"] for item in items}


async def test_recommend_filters_by_fuel(reco_client, seeded):
    resp = await reco_client.get(
        "/v1/recommendations",
        params={"make": "Zephyron", "fuel": "diesel"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert all(item["vehicle"]["fuel"] == "diesel" for item in items)
    # Only close_b is diesel
    assert seeded["close_b"] in {item["id"] for item in items}


async def test_recommend_filters_by_max_price(reco_client, seeded):
    resp = await reco_client.get(
        "/v1/recommendations",
        params={"make": "Zephyron", "max_price_eur_cents": 2_000_000},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert all(item["price_eur_cents"] <= 2_000_000 for item in items)
    assert seeded["far_price"] not in {item["id"] for item in items}


async def test_recommend_respects_limit(reco_client, seeded):  # noqa: ARG001
    resp = await reco_client.get(
        "/v1/recommendations",
        params={"make": "Zephyron", "limit": 2},
    )
    assert resp.status_code == 200
    assert len(resp.json()) <= 2


async def test_recommend_limit_validation(reco_client, seeded):  # noqa: ARG001
    resp = await reco_client.get("/v1/recommendations", params={"limit": 0})
    assert resp.status_code == 422


async def test_recommend_newest_first(reco_client, seeded):  # noqa: ARG001
    """Results should be ordered newest first (descending created_at)."""
    resp = await reco_client.get(
        "/v1/recommendations", params={"make": "Zephyron"}
    )
    assert resp.status_code == 200
    items = resp.json()
    # created_at is ISO string; lexicographic comparison is equivalent for UTC
    timestamps = [item["created_at"] for item in items]
    assert timestamps == sorted(timestamps, reverse=True)


# ── cleanup ───────────────────────────────────────────────────────────────────

def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    if os.path.exists(_db_path):
        os.remove(_db_path)
