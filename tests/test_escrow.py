"""Escrow endpoint tests: buyer deposits, release, refund, and list.

Mounts ONLY the escrow router on a local FastAPI app (does not call create_app).
Uses StubPaymentAdapter (default when stripe_secret_key is empty).
Tables are created via the lifespan fixture below.

The global conftest.py has already set AUTO48_DATABASE_URL to a temp sqlite file
before this module is imported.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import auto48.models  # noqa: F401 — registers all ORM metadata on Base
import auto48.models.escrow  # noqa: F401 — registers deposits table on Base
from auto48.api.routers.escrow import router as escrow_router
from auto48.core.security import create_access_token
from auto48.db import Base, async_session_factory, engine
from auto48.models.listing import Listing
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.user import User
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle

# ---------------------------------------------------------------------------
# App fixture (escrow router only)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(app: FastAPI):  # type: ignore[misc]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


def _make_app() -> FastAPI:
    app = FastAPI(lifespan=_lifespan)
    app.include_router(escrow_router)
    return app


@pytest.fixture
async def escrow_client():
    app = _make_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


# ---------------------------------------------------------------------------
# DB seed helpers
# ---------------------------------------------------------------------------


async def _create_user(email: str) -> User:
    async with async_session_factory() as session:
        user = User(email=email, display_name=email.split("@")[0])
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _create_seller(user_id: int) -> SellerProfile:
    async with async_session_factory() as session:
        profile = SellerProfile(user_id=user_id, type=SellerType.PRIVATE)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile


async def _create_listing(seller_id: int) -> Listing:
    """Create a listing with a unique sentinel make/model so rows don't collide."""
    async with async_session_factory() as session:
        vehicle = Vehicle(
            make="EscrowMake",
            model="EscrowModel",
            year=2024,
            fuel=FuelType.ELECTRIC,
            body=BodyType.HATCHBACK,
            transmission=Transmission.AUTOMATIC,
        )
        session.add(vehicle)
        await session.flush()

        listing = Listing(
            seller_id=seller_id,
            vehicle_id=vehicle.id,
            title="Escrow Test Listing",
            price_eur_cents=5000_00,
        )
        session.add(listing)
        await session.commit()
        await session.refresh(listing)
        return listing


def _auth_header(user_id: int) -> dict[str, str]:
    token = create_access_token(sub=str(user_id))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_buyer_can_place_deposit(escrow_client: AsyncClient) -> None:
    """A buyer can place a deposit on a listing; response is 201 with status 'held'."""
    seller_user = await _create_user("escrow_seller1@example.com")
    seller = await _create_seller(seller_user.id)
    listing = await _create_listing(seller.id)

    buyer_user = await _create_user("escrow_buyer1@example.com")

    resp = await escrow_client.post(
        f"/v1/listings/{listing.id}/deposit",
        json={"amount_eur_cents": 50000},
        headers=_auth_header(buyer_user.id),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "held"
    assert body["listing_id"] == listing.id
    assert body["buyer_id"] == buyer_user.id
    assert body["amount_eur_cents"] == 50000
    assert body["provider_ref"] is not None
    assert body["provider_ref"].startswith("stub_hold_")


async def test_seller_can_release_deposit(escrow_client: AsyncClient) -> None:
    """The listing seller can release a held deposit; status becomes 'released'."""
    seller_user = await _create_user("escrow_seller2@example.com")
    seller = await _create_seller(seller_user.id)
    listing = await _create_listing(seller.id)

    buyer_user = await _create_user("escrow_buyer2@example.com")

    # Place deposit.
    place_resp = await escrow_client.post(
        f"/v1/listings/{listing.id}/deposit",
        json={"amount_eur_cents": 20000},
        headers=_auth_header(buyer_user.id),
    )
    assert place_resp.status_code == 201, place_resp.text
    deposit_id = place_resp.json()["id"]

    # Seller releases.
    release_resp = await escrow_client.post(
        f"/v1/deposits/{deposit_id}/release",
        headers=_auth_header(seller_user.id),
    )
    assert release_resp.status_code == 200, release_resp.text
    body = release_resp.json()
    assert body["status"] == "released"
    assert body["id"] == deposit_id


async def test_non_party_cannot_release_deposit(escrow_client: AsyncClient) -> None:
    """A user who is neither seller nor buyer gets 403 when attempting release."""
    seller_user = await _create_user("escrow_seller3@example.com")
    seller = await _create_seller(seller_user.id)
    listing = await _create_listing(seller.id)

    buyer_user = await _create_user("escrow_buyer3@example.com")
    third_party = await _create_user("escrow_third3@example.com")

    place_resp = await escrow_client.post(
        f"/v1/listings/{listing.id}/deposit",
        json={"amount_eur_cents": 10000},
        headers=_auth_header(buyer_user.id),
    )
    assert place_resp.status_code == 201, place_resp.text
    deposit_id = place_resp.json()["id"]

    release_resp = await escrow_client.post(
        f"/v1/deposits/{deposit_id}/release",
        headers=_auth_header(third_party.id),
    )
    assert release_resp.status_code == 403, release_resp.text


async def test_buyer_can_refund_held_deposit(escrow_client: AsyncClient) -> None:
    """The buyer can refund their own held deposit; status becomes 'refunded'."""
    seller_user = await _create_user("escrow_seller4@example.com")
    seller = await _create_seller(seller_user.id)
    listing = await _create_listing(seller.id)

    buyer_user = await _create_user("escrow_buyer4@example.com")

    place_resp = await escrow_client.post(
        f"/v1/listings/{listing.id}/deposit",
        json={"amount_eur_cents": 15000},
        headers=_auth_header(buyer_user.id),
    )
    assert place_resp.status_code == 201, place_resp.text
    deposit_id = place_resp.json()["id"]

    refund_resp = await escrow_client.post(
        f"/v1/deposits/{deposit_id}/refund",
        headers=_auth_header(buyer_user.id),
    )
    assert refund_resp.status_code == 200, refund_resp.text
    body = refund_resp.json()
    assert body["status"] == "refunded"
    assert body["id"] == deposit_id


async def test_double_settle_returns_409(escrow_client: AsyncClient) -> None:
    """Attempting to release an already-released deposit returns 409."""
    seller_user = await _create_user("escrow_seller5@example.com")
    seller = await _create_seller(seller_user.id)
    listing = await _create_listing(seller.id)

    buyer_user = await _create_user("escrow_buyer5@example.com")

    place_resp = await escrow_client.post(
        f"/v1/listings/{listing.id}/deposit",
        json={"amount_eur_cents": 30000},
        headers=_auth_header(buyer_user.id),
    )
    assert place_resp.status_code == 201, place_resp.text
    deposit_id = place_resp.json()["id"]

    # First release succeeds.
    release_resp = await escrow_client.post(
        f"/v1/deposits/{deposit_id}/release",
        headers=_auth_header(seller_user.id),
    )
    assert release_resp.status_code == 200, release_resp.text

    # Second release is a conflict.
    second_resp = await escrow_client.post(
        f"/v1/deposits/{deposit_id}/release",
        headers=_auth_header(seller_user.id),
    )
    assert second_resp.status_code == 409, second_resp.text


async def test_list_deposits_returns_current_user_deposits(escrow_client: AsyncClient) -> None:
    """GET /v1/deposits returns deposits where the user is buyer or seller."""
    seller_user = await _create_user("escrow_seller6@example.com")
    seller = await _create_seller(seller_user.id)
    listing = await _create_listing(seller.id)

    buyer_user = await _create_user("escrow_buyer6@example.com")
    other_buyer = await _create_user("escrow_other6@example.com")

    # buyer places a deposit
    resp1 = await escrow_client.post(
        f"/v1/listings/{listing.id}/deposit",
        json={"amount_eur_cents": 25000},
        headers=_auth_header(buyer_user.id),
    )
    assert resp1.status_code == 201, resp1.text
    deposit1_id = resp1.json()["id"]

    # other_buyer places a deposit on the same listing
    resp2 = await escrow_client.post(
        f"/v1/listings/{listing.id}/deposit",
        json={"amount_eur_cents": 10000},
        headers=_auth_header(other_buyer.id),
    )
    assert resp2.status_code == 201, resp2.text
    deposit2_id = resp2.json()["id"]

    # buyer sees only their own deposit
    buyer_list_resp = await escrow_client.get(
        "/v1/deposits",
        headers=_auth_header(buyer_user.id),
    )
    assert buyer_list_resp.status_code == 200, buyer_list_resp.text
    buyer_ids = {d["id"] for d in buyer_list_resp.json()}
    assert deposit1_id in buyer_ids
    assert deposit2_id not in buyer_ids

    # seller sees both deposits (they own the listing)
    seller_list_resp = await escrow_client.get(
        "/v1/deposits",
        headers=_auth_header(seller_user.id),
    )
    assert seller_list_resp.status_code == 200, seller_list_resp.text
    seller_ids = {d["id"] for d in seller_list_resp.json()}
    assert deposit1_id in seller_ids
    assert deposit2_id in seller_ids


async def test_auth_required_for_deposit(escrow_client: AsyncClient) -> None:
    """Unauthenticated request to POST /deposit returns 401 (no bearer token)."""
    resp = await escrow_client.post(
        "/v1/listings/1/deposit",
        json={"amount_eur_cents": 10000},
    )
    # HTTPBearer returns 401 when no credentials are provided (FastAPI default)
    assert resp.status_code == 401, resp.text


async def test_deposit_on_missing_listing_returns_404(escrow_client: AsyncClient) -> None:
    """Placing a deposit on a non-existent listing returns 404."""
    buyer_user = await _create_user("escrow_buyer7@example.com")

    resp = await escrow_client.post(
        "/v1/listings/99999/deposit",
        json={"amount_eur_cents": 10000},
        headers=_auth_header(buyer_user.id),
    )
    assert resp.status_code == 404, resp.text
