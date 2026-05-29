"""Tests for the test-drive scheduling feature.

Mirrors the sqlite-file + lifespan pattern from test_messaging.py.
Mounts ONLY the test_drives router on a local FastAPI app.
"""

from __future__ import annotations

import os
import tempfile

# Must be set before any auto48 imports so the engine is created with this URL.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="auto48-td-test-")
os.close(_db_fd)
os.environ.setdefault("AUTO48_ENVIRONMENT", "local")
os.environ["AUTO48_DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

import auto48.models  # noqa: E402, F401 — registers all ORM metadata on Base
import auto48.models.test_drive  # noqa: E402, F401 — registers TestDriveBooking table
from auto48.api.routers.test_drives import router as test_drives_router  # noqa: E402
from auto48.core.security import create_access_token  # noqa: E402
from auto48.db import Base, async_session_factory, engine  # noqa: E402
from auto48.models.listing import Listing  # noqa: E402
from auto48.models.seller import SellerProfile, SellerType  # noqa: E402
from auto48.models.user import User  # noqa: E402
from auto48.models.vehicle import (  # noqa: E402
    BodyType,
    Drivetrain,
    FuelType,
    Transmission,
    Vehicle,
)


def create_test_drive_app() -> FastAPI:
    from contextlib import asynccontextmanager

    from auto48.config import get_settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[misc]
        settings = get_settings()
        if settings.environment == "local":
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        yield
        await engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.include_router(test_drives_router)
    return app


@pytest.fixture(scope="module")
async def td_client():
    """Module-scoped client so lifespan/engine teardown happens only once."""
    app = create_test_drive_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


_seed_counter = 0


@pytest.fixture
async def seeded_ids(td_client):  # noqa: ARG001 — need lifespan to have run first
    """Seed: seller user + profile + vehicle + listing + buyer user.

    Uses a unique sentinel make/model ("Sentinel/TestDrive{n}") to guarantee
    uniqueness across test invocations.
    Returns (listing_id, buyer_user_id, seller_user_id).
    """
    global _seed_counter
    _seed_counter += 1
    suffix = _seed_counter

    async with async_session_factory() as session:
        seller_user = User(
            email=f"td_seller_{suffix}@example.com", display_name="TD Seller"
        )
        session.add(seller_user)
        await session.flush()

        profile = SellerProfile(user_id=seller_user.id, type=SellerType.PRIVATE)
        session.add(profile)
        await session.flush()

        vehicle = Vehicle(
            make="Sentinel",
            model=f"TestDrive{suffix}",
            year=2024,
            fuel=FuelType.ELECTRIC,
            body=BodyType.SEDAN,
            transmission=Transmission.AUTOMATIC,
            drivetrain=Drivetrain.AWD,
        )
        session.add(vehicle)
        await session.flush()

        listing = Listing(
            seller_id=profile.id,
            vehicle_id=vehicle.id,
            title=f"Sentinel TestDrive{suffix}",
            price_eur_cents=3000000,
        )
        session.add(listing)
        await session.flush()

        buyer = User(
            email=f"td_buyer_{suffix}@example.com", display_name="TD Buyer"
        )
        session.add(buyer)
        await session.flush()

        await session.commit()
        return listing.id, buyer.id, seller_user.id


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    if os.path.exists(_db_path):
        os.remove(_db_path)


def _auth(user_id: int) -> dict[str, str]:
    """Bearer auth header for user_id."""
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_request_test_drive_201(td_client, seeded_ids):
    listing_id, buyer_id, _ = seeded_ids

    resp = await td_client.post(
        f"/v1/listings/{listing_id}/test-drives",
        json={"slot_at": "2026-07-01T10:00:00Z", "note": "I'll be there at 10"},
        headers=_auth(buyer_id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["listing_id"] == listing_id
    assert body["requester_id"] == buyer_id
    assert body["status"] == "requested"
    assert body["note"] == "I'll be there at 10"
    assert "id" in body
    assert "created_at" in body


async def test_request_test_drive_no_note(td_client, seeded_ids):
    listing_id, buyer_id, _ = seeded_ids

    resp = await td_client.post(
        f"/v1/listings/{listing_id}/test-drives",
        json={"slot_at": "2026-07-02T14:00:00Z"},
        headers=_auth(buyer_id),
    )
    assert resp.status_code == 201
    assert resp.json()["note"] is None


async def test_request_test_drive_missing_listing(td_client, seeded_ids):
    _, buyer_id, _ = seeded_ids

    resp = await td_client.post(
        "/v1/listings/999999/test-drives",
        json={"slot_at": "2026-07-01T10:00:00Z"},
        headers=_auth(buyer_id),
    )
    assert resp.status_code == 404


async def test_request_test_drive_requires_auth(td_client, seeded_ids):
    listing_id, _, _ = seeded_ids

    resp = await td_client.post(
        f"/v1/listings/{listing_id}/test-drives",
        json={"slot_at": "2026-07-01T10:00:00Z"},
    )
    assert resp.status_code in (401, 403)


async def test_seller_confirms_booking(td_client, seeded_ids):
    listing_id, buyer_id, seller_user_id = seeded_ids

    # Buyer requests
    req_resp = await td_client.post(
        f"/v1/listings/{listing_id}/test-drives",
        json={"slot_at": "2026-07-03T09:00:00Z"},
        headers=_auth(buyer_id),
    )
    assert req_resp.status_code == 201
    booking_id = req_resp.json()["id"]

    # Seller confirms
    conf_resp = await td_client.post(
        f"/v1/test-drives/{booking_id}/confirm",
        headers=_auth(seller_user_id),
    )
    assert conf_resp.status_code == 200
    assert conf_resp.json()["status"] == "confirmed"


async def test_seller_declines_booking(td_client, seeded_ids):
    listing_id, buyer_id, seller_user_id = seeded_ids

    req_resp = await td_client.post(
        f"/v1/listings/{listing_id}/test-drives",
        json={"slot_at": "2026-07-04T11:00:00Z"},
        headers=_auth(buyer_id),
    )
    booking_id = req_resp.json()["id"]

    dec_resp = await td_client.post(
        f"/v1/test-drives/{booking_id}/decline",
        headers=_auth(seller_user_id),
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "declined"


async def test_non_seller_confirm_is_403(td_client, seeded_ids):
    """A different user (not the listing's seller) must get 403 when confirming."""
    listing_id, buyer_id, _ = seeded_ids

    req_resp = await td_client.post(
        f"/v1/listings/{listing_id}/test-drives",
        json={"slot_at": "2026-07-05T12:00:00Z"},
        headers=_auth(buyer_id),
    )
    booking_id = req_resp.json()["id"]

    # The buyer tries to confirm — must be 403
    resp = await td_client.post(
        f"/v1/test-drives/{booking_id}/confirm",
        headers=_auth(buyer_id),
    )
    assert resp.status_code == 403


async def test_non_requester_cancel_is_403(td_client, seeded_ids):
    """The seller must not be able to cancel (only the requester can)."""
    listing_id, buyer_id, seller_user_id = seeded_ids

    req_resp = await td_client.post(
        f"/v1/listings/{listing_id}/test-drives",
        json={"slot_at": "2026-07-06T15:00:00Z"},
        headers=_auth(buyer_id),
    )
    booking_id = req_resp.json()["id"]

    resp = await td_client.post(
        f"/v1/test-drives/{booking_id}/cancel",
        headers=_auth(seller_user_id),
    )
    assert resp.status_code == 403


async def test_requester_cancels_booking(td_client, seeded_ids):
    listing_id, buyer_id, _ = seeded_ids

    req_resp = await td_client.post(
        f"/v1/listings/{listing_id}/test-drives",
        json={"slot_at": "2026-07-07T16:00:00Z"},
        headers=_auth(buyer_id),
    )
    booking_id = req_resp.json()["id"]

    cancel_resp = await td_client.post(
        f"/v1/test-drives/{booking_id}/cancel",
        headers=_auth(buyer_id),
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


async def test_list_for_buyer(td_client, seeded_ids):
    listing_id, buyer_id, _ = seeded_ids

    await td_client.post(
        f"/v1/listings/{listing_id}/test-drives",
        json={"slot_at": "2026-07-08T09:00:00Z"},
        headers=_auth(buyer_id),
    )

    resp = await td_client.get("/v1/test-drives", headers=_auth(buyer_id))
    assert resp.status_code == 200
    ids = [b["requester_id"] for b in resp.json()]
    assert buyer_id in ids


async def test_list_for_seller(td_client, seeded_ids):
    listing_id, buyer_id, seller_user_id = seeded_ids

    await td_client.post(
        f"/v1/listings/{listing_id}/test-drives",
        json={"slot_at": "2026-07-09T10:00:00Z"},
        headers=_auth(buyer_id),
    )

    resp = await td_client.get("/v1/test-drives", headers=_auth(seller_user_id))
    assert resp.status_code == 200
    listing_ids = [b["listing_id"] for b in resp.json()]
    assert listing_id in listing_ids


async def test_list_requires_auth(td_client):
    resp = await td_client.get("/v1/test-drives")
    assert resp.status_code in (401, 403)


async def test_confirm_requires_auth(td_client, seeded_ids):
    listing_id, buyer_id, _ = seeded_ids

    req_resp = await td_client.post(
        f"/v1/listings/{listing_id}/test-drives",
        json={"slot_at": "2026-07-10T11:00:00Z"},
        headers=_auth(buyer_id),
    )
    booking_id = req_resp.json()["id"]

    resp = await td_client.post(f"/v1/test-drives/{booking_id}/confirm")
    assert resp.status_code in (401, 403)
