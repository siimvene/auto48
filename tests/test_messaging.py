"""Tests for the buyer<->seller messaging feature.

Mirrors conftest.py's sqlite-file + lifespan pattern but mounts ONLY the
conversations router on a local FastAPI app so the test is fully self-contained.
"""

import os
import tempfile

# Must be set before any auto48 imports so the engine is created with this URL.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="auto48-msg-test-")
os.close(_db_fd)
os.environ.setdefault("AUTO48_ENVIRONMENT", "local")
os.environ["AUTO48_DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

import auto48.models  # noqa: E402, F401 — registers all ORM metadata on Base
from auto48.api.routers.conversations import router as conversations_router  # noqa: E402
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


def create_messaging_app() -> FastAPI:
    from contextlib import asynccontextmanager

    from auto48.config import get_settings

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_settings()
        if settings.environment == "local":
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        yield
        await engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.include_router(conversations_router)
    return app


@pytest.fixture(scope="module")
async def msg_client():
    """Module-scoped client so lifespan/engine teardown happens only once."""
    app = create_messaging_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


_seed_counter = 0


@pytest.fixture
async def seeded_ids(msg_client):  # noqa: ARG001 — need lifespan to have run first
    """Seed seller user + profile + vehicle + listing + buyer user.

    Returns (listing_id, buyer_id, seller_user_id).
    Uses a counter suffix to guarantee unique emails across test invocations.
    """
    global _seed_counter
    _seed_counter += 1
    suffix = _seed_counter

    async with async_session_factory() as session:
        # Create seller user first so its id != the seller_profile id.
        seller_user = User(
            email=f"seller_msg_{suffix}@example.com", display_name="Seller Msg"
        )
        session.add(seller_user)
        await session.flush()

        profile = SellerProfile(user_id=seller_user.id, type=SellerType.PRIVATE)
        session.add(profile)
        await session.flush()

        vehicle = Vehicle(
            make="BMW",
            model="3 Series",
            year=2020,
            fuel=FuelType.PETROL,
            body=BodyType.SEDAN,
            transmission=Transmission.AUTOMATIC,
            drivetrain=Drivetrain.RWD,
        )
        session.add(vehicle)
        await session.flush()

        listing = Listing(
            seller_id=profile.id,
            vehicle_id=vehicle.id,
            title="2020 BMW 3 Series",
            price_eur_cents=2500000,
        )
        session.add(listing)
        await session.flush()

        buyer = User(
            email=f"buyer_msg_{suffix}@example.com", display_name="Buyer Msg"
        )
        session.add(buyer)
        await session.flush()

        await session.commit()
        return listing.id, buyer.id, seller_user.id


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    if os.path.exists(_db_path):
        os.remove(_db_path)


def _auth(user_id: int) -> dict[str, str]:
    """Bearer header for a seeded user id (exercises the real CurrentUser dep)."""
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


async def test_start_conversation(msg_client, seeded_ids):
    listing_id, buyer_id, seller_user_id = seeded_ids

    resp = await msg_client.post(
        "/v1/conversations",
        json={"listing_id": listing_id},
        headers=_auth(buyer_id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["listing_id"] == listing_id
    assert body["buyer_id"] == buyer_id
    # seller_id must be the seller's *user* id, not the seller_profile id
    assert body["seller_id"] == seller_user_id
    assert "id" in body
    assert "created_at" in body


async def test_conversation_requires_auth(msg_client, seeded_ids):
    listing_id, _, _ = seeded_ids
    resp = await msg_client.post("/v1/conversations", json={"listing_id": listing_id})
    assert resp.status_code in (401, 403)


async def test_start_conversation_returns_existing(msg_client, seeded_ids):
    """Starting the same (listing, buyer) conversation twice must return the same object."""
    listing_id, buyer_id, _ = seeded_ids

    first = await msg_client.post(
        "/v1/conversations", json={"listing_id": listing_id}, headers=_auth(buyer_id)
    )
    second = await msg_client.post(
        "/v1/conversations", json={"listing_id": listing_id}, headers=_auth(buyer_id)
    )
    assert first.status_code == 201
    # Second call returns existing — still 201 from our handler, same id.
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


async def test_post_and_list_messages_ordered(msg_client, seeded_ids):
    listing_id, buyer_id, _ = seeded_ids

    # Create a conversation.
    conv_resp = await msg_client.post(
        "/v1/conversations", json={"listing_id": listing_id}, headers=_auth(buyer_id)
    )
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["id"]

    # Post two messages with distinct bodies.
    msg1 = await msg_client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"body": "Hello, is it still available?"},
        headers=_auth(buyer_id),
    )
    msg2 = await msg_client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"body": "Can you do 24 000?"},
        headers=_auth(buyer_id),
    )
    assert msg1.status_code == 201
    assert msg2.status_code == 201

    # List messages and verify ordering (id-stable within same timestamp).
    list_resp = await msg_client.get(f"/v1/conversations/{conv_id}/messages")
    assert list_resp.status_code == 200
    messages = list_resp.json()
    assert len(messages) == 2
    assert messages[0]["body"] == "Hello, is it still available?"
    assert messages[1]["body"] == "Can you do 24 000?"
    # Ids must be ascending (ordering guarantee).
    assert messages[0]["id"] < messages[1]["id"]


async def test_list_conversations_for_user(msg_client, seeded_ids):
    listing_id, buyer_id, seller_user_id = seeded_ids

    await msg_client.post(
        "/v1/conversations", json={"listing_id": listing_id}, headers=_auth(buyer_id)
    )

    # Buyer can see their conversation (derived from their token).
    buyer_resp = await msg_client.get("/v1/conversations", headers=_auth(buyer_id))
    assert buyer_resp.status_code == 200
    assert any(c["buyer_id"] == buyer_id for c in buyer_resp.json())

    # Seller can also see it.
    seller_resp = await msg_client.get("/v1/conversations", headers=_auth(seller_user_id))
    assert seller_resp.status_code == 200
    assert any(c["seller_id"] == seller_user_id for c in seller_resp.json())


async def test_post_message_missing_conversation(msg_client, seeded_ids):
    _, buyer_id, _ = seeded_ids
    resp = await msg_client.post(
        "/v1/conversations/999999/messages",
        json={"body": "ghost message"},
        headers=_auth(buyer_id),
    )
    assert resp.status_code == 404


async def test_start_conversation_missing_listing(msg_client, seeded_ids):
    _, buyer_id, _ = seeded_ids
    resp = await msg_client.post(
        "/v1/conversations", json={"listing_id": 999999}, headers=_auth(buyer_id)
    )
    assert resp.status_code == 404


async def test_post_message_blank_body(msg_client, seeded_ids):
    listing_id, buyer_id, _ = seeded_ids

    conv_resp = await msg_client.post(
        "/v1/conversations", json={"listing_id": listing_id}, headers=_auth(buyer_id)
    )
    conv_id = conv_resp.json()["id"]

    resp = await msg_client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"body": "   "},
        headers=_auth(buyer_id),
    )
    assert resp.status_code == 400
