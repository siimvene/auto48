"""Billing endpoint tests: subscriptions and listing promotions.

Mounts ONLY the billing router on a local FastAPI app (does not call create_app).
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
import auto48.models.billing  # noqa: F401 — registers billing tables on Base
from auto48.api.routers.billing import router as billing_router
from auto48.core.security import create_access_token
from auto48.db import Base, async_session_factory, engine
from auto48.models.listing import Listing
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.user import User
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle

# ---------------------------------------------------------------------------
# App fixture (billing router only)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(app: FastAPI):  # type: ignore[misc]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


def _make_app() -> FastAPI:
    app = FastAPI(lifespan=_lifespan)
    app.include_router(billing_router)
    return app


@pytest.fixture
async def billing_client():
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


async def _create_seller(user_id: int, seller_type: SellerType) -> SellerProfile:
    async with async_session_factory() as session:
        profile = SellerProfile(user_id=user_id, type=seller_type)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile


async def _create_listing(seller_id: int) -> Listing:
    async with async_session_factory() as session:
        vehicle = Vehicle(
            make="Toyota",
            model="Corolla",
            year=2020,
            fuel=FuelType.PETROL,
            body=BodyType.SEDAN,
            transmission=Transmission.MANUAL,
        )
        session.add(vehicle)
        await session.flush()

        listing = Listing(
            seller_id=seller_id,
            vehicle_id=vehicle.id,
            title="Test Listing",
            price_eur_cents=10000_00,
        )
        session.add(listing)
        await session.commit()
        await session.refresh(listing)
        return listing


def _auth_header(user_id: int) -> dict[str, str]:
    token = create_access_token(sub=str(user_id))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Subscription tests
# ---------------------------------------------------------------------------


async def test_dealer_can_subscribe(billing_client: AsyncClient) -> None:
    """A DEALER seller can subscribe to the basic plan and receive a 201 response."""
    user = await _create_user("dealer1@example.com")
    await _create_seller(user.id, SellerType.DEALER)

    resp = await billing_client.post(
        "/v1/billing/subscribe",
        json={"plan": "basic"},
        headers=_auth_header(user.id),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["plan"] == "basic"
    assert body["status"] == "active"
    assert body["stripe_subscription_id"].startswith("stub_sub_")


async def test_private_seller_subscribe_returns_403(billing_client: AsyncClient) -> None:
    """A PRIVATE seller cannot subscribe — must receive 403."""
    user = await _create_user("private1@example.com")
    await _create_seller(user.id, SellerType.PRIVATE)

    resp = await billing_client.post(
        "/v1/billing/subscribe",
        json={"plan": "basic"},
        headers=_auth_header(user.id),
    )
    assert resp.status_code == 403, resp.text


async def test_get_subscription_after_subscribe(billing_client: AsyncClient) -> None:
    """After subscribing, GET /v1/billing/subscription returns the subscription."""
    user = await _create_user("dealer2@example.com")
    await _create_seller(user.id, SellerType.DEALER)

    await billing_client.post(
        "/v1/billing/subscribe",
        json={"plan": "pro"},
        headers=_auth_header(user.id),
    )

    resp = await billing_client.get(
        "/v1/billing/subscription",
        headers=_auth_header(user.id),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["plan"] == "pro"
    assert body["status"] == "active"


async def test_get_subscription_no_sub_returns_404(billing_client: AsyncClient) -> None:
    """GET /v1/billing/subscription returns 404 when the user has no subscription."""
    user = await _create_user("dealer3@example.com")
    await _create_seller(user.id, SellerType.DEALER)

    resp = await billing_client.get(
        "/v1/billing/subscription",
        headers=_auth_header(user.id),
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Promotion tests
# ---------------------------------------------------------------------------


async def test_listing_owner_can_create_promotion(billing_client: AsyncClient) -> None:
    """The owner of a listing can create a promotion and receive a 201 response."""
    user = await _create_user("owner1@example.com")
    seller = await _create_seller(user.id, SellerType.PRIVATE)
    listing = await _create_listing(seller.id)

    resp = await billing_client.post(
        f"/v1/listings/{listing.id}/promotions",
        json={"kind": "bump", "duration_days": 7},
        headers=_auth_header(user.id),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["kind"] == "bump"
    assert body["listing_id"] == listing.id
    assert body["stripe_payment_id"].startswith("stub_pi_")


async def test_non_owner_cannot_create_promotion(billing_client: AsyncClient) -> None:
    """A user who does not own the listing receives 403 when creating a promotion."""
    owner = await _create_user("owner2@example.com")
    owner_seller = await _create_seller(owner.id, SellerType.PRIVATE)
    listing = await _create_listing(owner_seller.id)

    other_user = await _create_user("other1@example.com")
    await _create_seller(other_user.id, SellerType.PRIVATE)

    resp = await billing_client.post(
        f"/v1/listings/{listing.id}/promotions",
        json={"kind": "featured", "duration_days": 14},
        headers=_auth_header(other_user.id),
    )
    assert resp.status_code == 403, resp.text


async def test_get_promotions_returns_list(billing_client: AsyncClient) -> None:
    """GET /v1/listings/{id}/promotions returns a list of promotions."""
    user = await _create_user("owner3@example.com")
    seller = await _create_seller(user.id, SellerType.PRIVATE)
    listing = await _create_listing(seller.id)

    # Create two promotions.
    for kind in ("bump", "spotlight"):
        resp = await billing_client.post(
            f"/v1/listings/{listing.id}/promotions",
            json={"kind": kind, "duration_days": 3},
            headers=_auth_header(user.id),
        )
        assert resp.status_code == 201, resp.text

    resp = await billing_client.get(
        f"/v1/listings/{listing.id}/promotions",
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) == 2
    kinds = {item["kind"] for item in items}
    assert kinds == {"bump", "spotlight"}


async def test_promotion_on_missing_listing_returns_404(billing_client: AsyncClient) -> None:
    """POST /v1/listings/9999/promotions returns 404 when listing does not exist."""
    user = await _create_user("owner4@example.com")
    await _create_seller(user.id, SellerType.PRIVATE)

    resp = await billing_client.post(
        "/v1/listings/9999/promotions",
        json={"kind": "bump", "duration_days": 7},
        headers=_auth_header(user.id),
    )
    assert resp.status_code == 404, resp.text
