"""Tests for the dealer feed API router and ingest service.

Uses a dedicated local FastAPI app (not the full create_app()) that includes
ONLY the feeds router, backed by a StubFeedAdapter (injected via
dependency_overrides) and the same SQLite test database from conftest.py.

Redis is unavailable in tests — the arq enqueue step must degrade gracefully.
"""

from __future__ import annotations

import itertools
import json

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import auto48.models as _models  # noqa: F401 — register all ORM tables
import auto48.models.dealer_feed  # noqa: F401 — register DealerFeed + IngestRun tables
from auto48.adapters.feed.http_fetch import StubFeedAdapter
from auto48.api.routers import feeds as feeds_router
from auto48.core.security import create_access_token
from auto48.db import Base, async_session_factory, engine
from auto48.models.dealer_feed import IngestRun, IngestStatus
from auto48.models.listing import Listing
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.user import User

_user_counter = itertools.count(100)

# ---------------------------------------------------------------------------
# Small canned payloads
# ---------------------------------------------------------------------------

_CSV_PAYLOAD = b"""\
make,model,year,fuel,body,transmission,price_eur_cents,title,mileage_km,vin
Toyota,Corolla,2020,petrol,sedan,manual,1500000,Toyota Corolla 2020,50000,VIN001
Volkswagen,Golf,2019,diesel,hatchback,automatic,1200000,VW Golf 2019,80000,VIN002
"""

_JSON_PAYLOAD = json.dumps(
    [
        {
            "make": "BMW",
            "model": "3 Series",
            "year": 2021,
            "fuel": "petrol",
            "body": "sedan",
            "transmission": "automatic",
            "price_eur_cents": 3000000,
            "title": "BMW 3 Series 2021",
            "mileage_km": 20000,
            "vin": "VIN003",
        },
        {
            "make": "Ford",
            "model": "Focus",
            "year": 2018,
            "fuel": "diesel",
            "body": "hatchback",
            "transmission": "manual",
            "price_eur_cents": 900000,
            "title": "Ford Focus 2018",
            "mileage_km": 110000,
            "vin": None,
        },
    ]
).encode()

# A CSV with one valid row and one invalid row (missing fuel)
_CSV_WITH_BAD_ROW = b"""\
make,model,year,fuel,body,transmission,price_eur_cents,title
Honda,Civic,2022,petrol,sedan,manual,2000000,Honda Civic 2022
BadMake,BadModel,2000,,sedan,manual,999,BadTitle
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _auth(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def _make_feeds_app(stub_payload: bytes = b"") -> tuple[FastAPI, StubFeedAdapter]:
    """Build a minimal FastAPI with only the feeds router + a StubFeedAdapter."""
    app = FastAPI()
    stub = StubFeedAdapter(stub_payload)
    app.dependency_overrides[feeds_router._get_fetch_adapter] = lambda: stub
    app.include_router(feeds_router.router)
    return app, stub


@pytest.fixture
async def schema():
    """Ensure all tables are created once per test session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _seed_user_and_profile(
    seller_type: SellerType,
) -> tuple[int, int]:
    """Insert a User + SellerProfile; return (user_id, profile_id)."""
    uid = next(_user_counter)
    async with async_session_factory() as session:
        user = User(
            email=f"feedtest_{uid}@example.com",
            display_name=f"Feed User {uid}",
        )
        session.add(user)
        await session.flush()

        profile = SellerProfile(user_id=user.id, type=seller_type)
        session.add(profile)
        await session.flush()
        await session.commit()
        return user.id, profile.id


@pytest.fixture
async def dealer(schema):  # noqa: ARG001
    """Seed a DEALER user; yield (user_id, profile_id)."""
    return await _seed_user_and_profile(SellerType.DEALER)


@pytest.fixture
async def private_seller(schema):  # noqa: ARG001
    """Seed a PRIVATE seller user; yield (user_id, profile_id)."""
    return await _seed_user_and_profile(SellerType.PRIVATE)


# ---------------------------------------------------------------------------
# Feed registration tests
# ---------------------------------------------------------------------------


async def test_dealer_can_register_feed(dealer):
    user_id, _profile_id = dealer
    app, _ = _make_feeds_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/v1/dealer/feeds",
            json={"url": "http://example.com/feed.csv", "format": "csv"},
            headers=_auth(user_id),
        )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["format"] == "csv"
    assert body["active"] is True
    assert body["url"] == "http://example.com/feed.csv"


async def test_private_seller_cannot_register_feed(private_seller):
    user_id, _ = private_seller
    app, _ = _make_feeds_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/v1/dealer/feeds",
            json={"url": "http://example.com/feed.csv", "format": "csv"},
            headers=_auth(user_id),
        )
    assert resp.status_code == 403


async def test_unauthenticated_cannot_register_feed(schema):  # noqa: ARG001
    app, _ = _make_feeds_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.post(
            "/v1/dealer/feeds",
            json={"url": "http://example.com/feed.csv", "format": "csv"},
        )
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# CSV ingest tests
# ---------------------------------------------------------------------------


async def test_ingest_csv_creates_listings(dealer):
    user_id, profile_id = dealer
    app, _ = _make_feeds_app(stub_payload=_CSV_PAYLOAD)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Register the feed
        create_resp = await ac.post(
            "/v1/dealer/feeds",
            json={"url": "http://example.com/inv.csv", "format": "csv"},
            headers=_auth(user_id),
        )
        assert create_resp.status_code == 201, create_resp.text
        feed_id = create_resp.json()["id"]

        # Trigger ingest
        ingest_resp = await ac.post(
            f"/v1/dealer/feeds/{feed_id}/ingest",
            headers=_auth(user_id),
        )
    assert ingest_resp.status_code == 200, ingest_resp.text
    result = ingest_resp.json()
    assert result["status"] == "success"
    assert result["created_count"] == 2
    assert result["updated_count"] == 0
    assert result["error_count"] == 0

    # Confirm listings were persisted
    async with async_session_factory() as session:
        rows = (
            await session.scalars(
                select(Listing).where(Listing.seller_id == profile_id)
            )
        ).all()
    assert len(rows) == 2


# ---------------------------------------------------------------------------
# JSON ingest tests
# ---------------------------------------------------------------------------


async def test_ingest_json_creates_listings(dealer):
    user_id, profile_id = dealer
    app, _ = _make_feeds_app(stub_payload=_JSON_PAYLOAD)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_resp = await ac.post(
            "/v1/dealer/feeds",
            json={"url": "http://example.com/inv.json", "format": "json"},
            headers=_auth(user_id),
        )
        assert create_resp.status_code == 201, create_resp.text
        feed_id = create_resp.json()["id"]

        ingest_resp = await ac.post(
            f"/v1/dealer/feeds/{feed_id}/ingest",
            headers=_auth(user_id),
        )
    assert ingest_resp.status_code == 200, ingest_resp.text
    result = ingest_resp.json()
    assert result["status"] == "success"
    assert result["created_count"] == 2
    assert result["error_count"] == 0

    async with async_session_factory() as session:
        rows = (
            await session.scalars(
                select(Listing).where(Listing.seller_id == profile_id)
            )
        ).all()
    assert len(rows) >= 2


# ---------------------------------------------------------------------------
# VIN-based upsert test
# ---------------------------------------------------------------------------


async def test_ingest_updates_existing_listing_by_vin(dealer):
    """Running the same CSV twice must update the first-run listing, not duplicate it."""
    user_id, profile_id = dealer
    # First pass
    app1, _ = _make_feeds_app(stub_payload=_CSV_PAYLOAD)
    async with AsyncClient(
        transport=ASGITransport(app=app1), base_url="http://test"
    ) as ac:
        cr = await ac.post(
            "/v1/dealer/feeds",
            json={"url": "http://example.com/upsert.csv", "format": "csv"},
            headers=_auth(user_id),
        )
        feed_id = cr.json()["id"]
        await ac.post(f"/v1/dealer/feeds/{feed_id}/ingest", headers=_auth(user_id))

    # Second pass — same VIN, higher price
    updated_csv = _CSV_PAYLOAD.replace(b"1500000", b"1600000")
    app2, _ = _make_feeds_app(stub_payload=updated_csv)
    app2.dependency_overrides[feeds_router._get_fetch_adapter] = lambda: StubFeedAdapter(
        updated_csv
    )
    async with AsyncClient(
        transport=ASGITransport(app=app2), base_url="http://test"
    ) as ac:
        ingest_resp = await ac.post(
            f"/v1/dealer/feeds/{feed_id}/ingest",
            headers=_auth(user_id),
        )
    result = ingest_resp.json()
    assert result["status"] == "success"
    # VIN001 and VIN002 already exist → 2 updates, 0 creates
    assert result["updated_count"] == 2
    assert result["created_count"] == 0

    # Confirm updated price
    async with async_session_factory() as session:
        listing = await session.scalar(
            select(Listing)
            .join(
                __import__("auto48.models.vehicle", fromlist=["Vehicle"]).Vehicle,
                Listing.vehicle_id
                == __import__("auto48.models.vehicle", fromlist=["Vehicle"]).Vehicle.id,
            )
            .where(Listing.seller_id == profile_id)
            .where(
                __import__("auto48.models.vehicle", fromlist=["Vehicle"]).Vehicle.vin
                == "VIN001"
            )
        )
    assert listing is not None
    assert listing.price_eur_cents == 1600000


# ---------------------------------------------------------------------------
# Bad-row handling
# ---------------------------------------------------------------------------


async def test_ingest_bad_row_counted_in_error(dealer):
    """A CSV with one invalid row: only the valid row creates a listing."""
    user_id, profile_id = dealer
    app, _ = _make_feeds_app(stub_payload=_CSV_WITH_BAD_ROW)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        cr = await ac.post(
            "/v1/dealer/feeds",
            json={"url": "http://example.com/bad.csv", "format": "csv"},
            headers=_auth(user_id),
        )
        feed_id = cr.json()["id"]
        ingest_resp = await ac.post(
            f"/v1/dealer/feeds/{feed_id}/ingest",
            headers=_auth(user_id),
        )
    result = ingest_resp.json()
    assert result["status"] == "success"
    assert result["created_count"] == 1  # one valid row
    assert result["error_count"] == 1  # one bad row skipped by parser


# ---------------------------------------------------------------------------
# List feeds
# ---------------------------------------------------------------------------


async def test_list_feeds_returns_own_feeds(dealer):
    user_id, _ = dealer
    app, _ = _make_feeds_app()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        for fmt in ("csv", "json"):
            await ac.post(
                "/v1/dealer/feeds",
                json={"url": f"http://example.com/{fmt}.feed", "format": fmt},
                headers=_auth(user_id),
            )
        resp = await ac.get("/v1/dealer/feeds", headers=_auth(user_id))

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 2
    assert len(body["items"]) >= 2


# ---------------------------------------------------------------------------
# List runs
# ---------------------------------------------------------------------------


async def test_list_runs_after_ingest(dealer):
    user_id, _ = dealer
    app, _ = _make_feeds_app(stub_payload=_CSV_PAYLOAD)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        cr = await ac.post(
            "/v1/dealer/feeds",
            json={"url": "http://example.com/runs.csv", "format": "csv"},
            headers=_auth(user_id),
        )
        feed_id = cr.json()["id"]
        await ac.post(f"/v1/dealer/feeds/{feed_id}/ingest", headers=_auth(user_id))
        await ac.post(f"/v1/dealer/feeds/{feed_id}/ingest", headers=_auth(user_id))

        runs_resp = await ac.get(
            f"/v1/dealer/feeds/{feed_id}/runs", headers=_auth(user_id)
        )
    assert runs_resp.status_code == 200, runs_resp.text
    body = runs_resp.json()
    assert body["total"] >= 2
    for run in body["items"]:
        assert run["status"] in ("success", "error", "running")


# ---------------------------------------------------------------------------
# IngestRun DB state
# ---------------------------------------------------------------------------


async def test_ingest_run_row_persisted(dealer):
    user_id, _ = dealer
    app, _ = _make_feeds_app(stub_payload=_CSV_PAYLOAD)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        cr = await ac.post(
            "/v1/dealer/feeds",
            json={"url": "http://example.com/dbcheck.csv", "format": "csv"},
            headers=_auth(user_id),
        )
        feed_id = cr.json()["id"]
        ingest_resp = await ac.post(
            f"/v1/dealer/feeds/{feed_id}/ingest", headers=_auth(user_id)
        )
    run_id = ingest_resp.json()["run_id"]

    async with async_session_factory() as session:
        run = await session.get(IngestRun, run_id)
    assert run is not None
    assert run.status == IngestStatus.SUCCESS
    assert run.finished_at is not None
    assert run.created_count == 2
