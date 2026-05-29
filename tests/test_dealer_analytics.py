"""Tests for the dealer analytics dashboard endpoint.

Mirrors the sqlite-file + lifespan pattern from test_test_drives.py.
Mounts ONLY the dealer_analytics router on a local FastAPI app.
Uses UNIQUE sentinel make/model ("DlrSentinel/AnalyticsN") to prevent
data bleed from other test modules that share the same sqlite file.
"""

from __future__ import annotations

import os
import tempfile

# Must be set before any auto48 imports so the engine is created with this URL.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db", prefix="auto48-da-test-")
os.close(_db_fd)
os.environ.setdefault("AUTO48_ENVIRONMENT", "local")
os.environ["AUTO48_DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_path}"

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

import auto48.models  # noqa: E402, F401 — registers all ORM metadata on Base
from auto48.api.routers.dealer_analytics import router as analytics_router  # noqa: E402
from auto48.core.security import create_access_token  # noqa: E402
from auto48.db import Base, async_session_factory, engine  # noqa: E402
from auto48.models.conversation import Conversation  # noqa: E402
from auto48.models.dealer_feed import DealerFeed, FeedFormat, IngestRun, IngestStatus  # noqa: E402
from auto48.models.listing import Listing, ListingStatus  # noqa: E402
from auto48.models.seller import SellerProfile, SellerType  # noqa: E402
from auto48.models.test_drive import TestDriveBooking, TestDriveStatus  # noqa: E402
from auto48.models.user import User  # noqa: E402
from auto48.models.vehicle import (  # noqa: E402
    BodyType,
    Drivetrain,
    FuelType,
    Transmission,
    Vehicle,
)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def _create_analytics_app() -> FastAPI:
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
    app.include_router(analytics_router)
    return app


# ---------------------------------------------------------------------------
# Module-scoped client
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def da_client() -> AsyncClient:  # type: ignore[misc]
    """Module-scoped ASGI client; lifespan/engine teardown happens only once."""
    app = _create_analytics_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


_seed_counter = 0


# ---------------------------------------------------------------------------
# Seed fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def dealer_seed(da_client: AsyncClient) -> dict[str, int]:  # noqa: ARG001
    """Seed a DEALER user with several listings, conversations, bookings, and a feed.

    Returns a dict with ids needed by tests.
    Unique sentinel make "DlrSentinel" / model "Analytics{n}" prevents bleed.
    """
    global _seed_counter
    _seed_counter += 1
    suffix = _seed_counter

    async with async_session_factory() as session:
        # --- dealer user + profile ---
        dealer_user = User(
            email=f"da_dealer_{suffix}@example.com",
            display_name="DA Dealer",
        )
        session.add(dealer_user)
        await session.flush()

        profile = SellerProfile(user_id=dealer_user.id, type=SellerType.DEALER)
        session.add(profile)
        await session.flush()

        # --- vehicles (2 makes × 2 body types) ---
        v_sedan_bmw = Vehicle(
            make="DlrSentinel",
            model=f"Analytics{suffix}BMWSedan",
            year=2022,
            fuel=FuelType.PETROL,
            body=BodyType.SEDAN,
            transmission=Transmission.AUTOMATIC,
            drivetrain=Drivetrain.RWD,
        )
        v_suv_bmw = Vehicle(
            make="DlrSentinel",
            model=f"Analytics{suffix}BMWSUV",
            year=2021,
            fuel=FuelType.DIESEL,
            body=BodyType.SUV,
            transmission=Transmission.AUTOMATIC,
            drivetrain=Drivetrain.AWD,
        )
        v_sedan_vw = Vehicle(
            make="DlrSentinelVW",
            model=f"Analytics{suffix}VWSedan",
            year=2020,
            fuel=FuelType.DIESEL,
            body=BodyType.SEDAN,
            transmission=Transmission.MANUAL,
            drivetrain=Drivetrain.FWD,
        )
        for v in (v_sedan_bmw, v_suv_bmw, v_sedan_vw):
            session.add(v)
        await session.flush()

        # --- listings: 2 active, 1 sold, 1 draft ---
        l_active1 = Listing(
            seller_id=profile.id,
            vehicle_id=v_sedan_bmw.id,
            title=f"Active Sedan {suffix}",
            price_eur_cents=2_000_000,
            status=ListingStatus.ACTIVE,
        )
        l_active2 = Listing(
            seller_id=profile.id,
            vehicle_id=v_suv_bmw.id,
            title=f"Active SUV {suffix}",
            price_eur_cents=3_000_000,
            status=ListingStatus.ACTIVE,
        )
        l_sold = Listing(
            seller_id=profile.id,
            vehicle_id=v_sedan_vw.id,
            title=f"Sold Sedan {suffix}",
            price_eur_cents=1_000_000,
            status=ListingStatus.SOLD,
        )
        l_draft = Listing(
            seller_id=profile.id,
            vehicle_id=v_sedan_bmw.id,
            title=f"Draft Sedan {suffix}",
            price_eur_cents=1_500_000,
            status=ListingStatus.DRAFT,
        )
        for lst in (l_active1, l_active2, l_sold, l_draft):
            session.add(lst)
        await session.flush()

        # --- buyer user for conversations / test drives ---
        buyer = User(
            email=f"da_buyer_{suffix}@example.com",
            display_name="DA Buyer",
        )
        session.add(buyer)
        await session.flush()

        # --- 2 conversations (leads) on active listings ---
        conv1 = Conversation(
            listing_id=l_active1.id,
            buyer_id=buyer.id,
            seller_id=dealer_user.id,
        )
        conv2 = Conversation(
            listing_id=l_active2.id,
            buyer_id=buyer.id,
            seller_id=dealer_user.id,
        )
        session.add(conv1)
        session.add(conv2)

        # --- 3 test-drive bookings ---
        from datetime import UTC, datetime

        slot = datetime(2027, 1, 10, 10, 0, tzinfo=UTC)
        td_requested = TestDriveBooking(
            listing_id=l_active1.id,
            requester_id=buyer.id,
            slot_at=slot,
            status=TestDriveStatus.REQUESTED,
        )
        td_confirmed = TestDriveBooking(
            listing_id=l_active2.id,
            requester_id=buyer.id,
            slot_at=slot,
            status=TestDriveStatus.CONFIRMED,
        )
        td_declined = TestDriveBooking(
            listing_id=l_sold.id,
            requester_id=buyer.id,
            slot_at=slot,
            status=TestDriveStatus.DECLINED,
        )
        for td in (td_requested, td_confirmed, td_declined):
            session.add(td)

        # --- dealer feed + latest ingest run ---
        feed = DealerFeed(
            seller_id=profile.id,
            url="https://example.com/feed.csv",
            format=FeedFormat.CSV,
        )
        session.add(feed)
        await session.flush()

        run = IngestRun(
            feed_id=feed.id,
            status=IngestStatus.SUCCESS,
            created_count=5,
            updated_count=2,
            error_count=0,
        )
        session.add(run)

        await session.flush()
        await session.commit()

        return {
            "dealer_user_id": dealer_user.id,
            "profile_id": profile.id,
            "buyer_user_id": buyer.id,
            "l_active1_id": l_active1.id,
            "l_active2_id": l_active2.id,
            "feed_id": feed.id,
        }


@pytest.fixture
async def private_seller_seed(da_client: AsyncClient) -> dict[str, int]:  # noqa: ARG001
    """Seed a PRIVATE seller (should receive 403 from the analytics endpoint)."""
    global _seed_counter
    _seed_counter += 1
    suffix = _seed_counter

    async with async_session_factory() as session:
        user = User(
            email=f"da_private_{suffix}@example.com",
            display_name="Private Seller",
        )
        session.add(user)
        await session.flush()
        profile = SellerProfile(user_id=user.id, type=SellerType.PRIVATE)
        session.add(profile)
        await session.flush()
        await session.commit()
        return {"user_id": user.id}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_dealer_analytics_200(da_client: AsyncClient, dealer_seed: dict[str, int]) -> None:
    """Full happy-path: assert all aggregate values are correct."""
    resp = await da_client.get(
        "/v1/dealer/analytics",
        headers=_auth(dealer_seed["dealer_user_id"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # --- listing counts ---
    counts = body["listing_counts"]
    assert counts["total"] == 4
    assert counts["active"] == 2
    assert counts["sold"] == 1
    assert counts["draft"] == 1
    assert counts["expired"] == 0

    # --- inventory value (active listings only: 2_000_000 + 3_000_000) ---
    inv = body["inventory_value"]
    assert inv["total_eur_cents"] == 5_000_000
    assert inv["avg_eur_cents"] == pytest.approx(2_500_000.0)

    # --- leads ---
    assert body["total_leads"] == 2

    # --- test-drive totals ---
    assert body["total_test_drives"] == 3

    td_statuses = {item["status"]: item["count"] for item in body["test_drives_by_status"]}
    assert td_statuses.get("requested") == 1
    assert td_statuses.get("confirmed") == 1
    assert td_statuses.get("declined") == 1

    # --- make breakdown: DlrSentinel has 3 listings, DlrSentinelVW has 1 ---
    makes = {m["make"]: m for m in body["top_makes"]}
    assert "DlrSentinel" in makes
    assert makes["DlrSentinel"]["count"] == 3
    # avg of 2_000_000 + 3_000_000 + 1_500_000 = 6_500_000 / 3 ≈ 2_166_666.67
    assert makes["DlrSentinel"]["avg_price_eur_cents"] == pytest.approx(
        (2_000_000 + 3_000_000 + 1_500_000) / 3, rel=1e-3
    )
    assert "DlrSentinelVW" in makes
    assert makes["DlrSentinelVW"]["count"] == 1

    # --- body breakdown ---
    bodies = {b["body"]: b for b in body["top_bodies"]}
    # sedan: l_active1 (2M) + l_sold (1M) + l_draft (1.5M) = 3 listings
    assert bodies["sedan"]["count"] == 3
    # suv: l_active2 (3M) = 1 listing
    assert bodies["suv"]["count"] == 1

    # --- feed health ---
    assert len(body["feed_health"]) == 1
    fh = body["feed_health"][0]
    assert fh["feed_id"] == dealer_seed["feed_id"]
    assert fh["status"] == "success"
    assert fh["created_count"] == 5
    assert fh["updated_count"] == 2
    assert fh["error_count"] == 0


async def test_private_seller_gets_403(
    da_client: AsyncClient, private_seller_seed: dict[str, int]
) -> None:
    """A PRIVATE SellerProfile must receive HTTP 403."""
    resp = await da_client.get(
        "/v1/dealer/analytics",
        headers=_auth(private_seller_seed["user_id"]),
    )
    assert resp.status_code == 403


async def test_no_profile_gets_404(da_client: AsyncClient) -> None:
    """A user with no SellerProfile at all must receive HTTP 404."""
    global _seed_counter
    _seed_counter += 1
    suffix = _seed_counter

    async with async_session_factory() as session:
        user = User(
            email=f"da_noprofile_{suffix}@example.com",
            display_name="No Profile User",
        )
        session.add(user)
        await session.flush()
        await session.commit()
        user_id = user.id

    resp = await da_client.get(
        "/v1/dealer/analytics",
        headers=_auth(user_id),
    )
    assert resp.status_code == 404


async def test_requires_auth(da_client: AsyncClient) -> None:
    """No auth header must yield 401 or 403."""
    resp = await da_client.get("/v1/dealer/analytics")
    assert resp.status_code in (401, 403)


async def test_empty_dealer_returns_zeros(da_client: AsyncClient) -> None:
    """A dealer with no listings/leads/feeds should still get a valid 200 with zeros."""
    global _seed_counter
    _seed_counter += 1
    suffix = _seed_counter

    async with async_session_factory() as session:
        user = User(
            email=f"da_empty_{suffix}@example.com",
            display_name="Empty Dealer",
        )
        session.add(user)
        await session.flush()
        profile = SellerProfile(user_id=user.id, type=SellerType.DEALER)
        session.add(profile)
        await session.flush()
        await session.commit()
        user_id = user.id

    resp = await da_client.get(
        "/v1/dealer/analytics",
        headers=_auth(user_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["listing_counts"]["total"] == 0
    assert body["inventory_value"]["total_eur_cents"] == 0
    assert body["total_leads"] == 0
    assert body["total_test_drives"] == 0
    assert body["top_makes"] == []
    assert body["top_bodies"] == []
    assert body["feed_health"] == []


def pytest_sessionfinish(session: object, exitstatus: object) -> None:  # noqa: ARG001
    if os.path.exists(_db_path):
        os.remove(_db_path)
