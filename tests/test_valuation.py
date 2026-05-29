"""Tests for ComparablesValuationAdapter (direct) + GET /v1/valuations (HTTP).

Schema setup: a session-scoped autouse fixture runs ``create_all`` once before
any test in this module — this ensures both the direct-adapter tests (which use
``async_session_factory`` naked) and the HTTP fixture tests share the same
already-initialised SQLite database pointed at by conftest's env vars.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import auto48.models  # noqa: F401 — register all ORM metadata on Base
from auto48.adapters.valuation.comparables import ComparablesValuationAdapter
from auto48.api.routers.valuations import router
from auto48.db import Base, async_session_factory, engine
from auto48.models.listing import Listing, ListingStatus
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.user import User
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle
from auto48.ports.valuation import DealScore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Unique sentinel make/model so comparables are isolated from other test
# modules that share the same SQLite database (e.g. test_health, test_feeds).
_MAKE = "Valuatestmark"
_MODEL = "Compcarmodel"
_YEAR = 2019

# Prices of 5 comparable listings (EUR cents).
# Sorted: 800_000, 1_000_000, 1_200_000, 1_400_000, 1_600_000
# Median = 1_200_000  (middle of 5 elements)
# statistics.quantiles(..., n=4) exclusive (default): p25=900_000, p75=1_500_000
_COMP_PRICES = [1_000_000, 800_000, 1_400_000, 1_200_000, 1_600_000]
_MEDIAN = 1_200_000

# Subjects well clear of thresholds to avoid boundary flips.
# great: <= -15% of median → <= 1_020_000; use 700_000 (≈ -41.7 %)
_GREAT_PRICE = 700_000
# high: > +10% of median → > 1_320_000; use 1_600_000 (≈ +33.3 %)
_HIGH_PRICE = 1_600_000
# fair: in (-5%, +10%]; use 1_200_000 (= 0 %, exactly median)
_FAIR_PRICE = 1_200_000


async def _seed_listings(seller_id: int) -> None:
    """Insert comparable Listing+Vehicle rows into the test DB."""
    async with async_session_factory() as session:
        for i, price in enumerate(_COMP_PRICES):
            vehicle = Vehicle(
                make=_MAKE,
                model=_MODEL,
                year=_YEAR,
                fuel=FuelType.PETROL,
                body=BodyType.SEDAN,
                transmission=Transmission.MANUAL,
            )
            session.add(vehicle)
            await session.flush()
            listing = Listing(
                seller_id=seller_id,
                vehicle_id=vehicle.id,
                title=f"Comparable {i}",
                price_eur_cents=price,
                mileage_km=80_000 + i * 5_000,
                status=ListingStatus.ACTIVE,  # MUST be ACTIVE — default is DRAFT
            )
            session.add(listing)
        await session.commit()


async def _make_seller(email: str = "val-seller@example.com") -> int:
    """Create a User + SellerProfile and return the profile id."""
    async with async_session_factory() as session:
        user = User(email=email, display_name="Val Seller")
        session.add(user)
        await session.flush()
        profile = SellerProfile(user_id=user.id, type=SellerType.PRIVATE)
        session.add(profile)
        await session.flush()
        await session.commit()
        return int(profile.id)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
async def ensure_schema() -> None:
    """Create all tables once for this test module.

    Module scope matches anyio's ``anyio_backend`` scope (also module), so
    pytest-asyncio can manage the same event loop throughout.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="module")
async def seeded_seller_id(ensure_schema: None) -> int:  # noqa: ARG001
    """Insert a seller once per module and return the profile id."""
    return await _make_seller()


@pytest.fixture(scope="module")
async def seeded_db(seeded_seller_id: int) -> int:
    """Seed 5 comparable ACTIVE listings once per module; return seller id."""
    await _seed_listings(seeded_seller_id)
    return seeded_seller_id


@asynccontextmanager
async def _val_lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    # Schema already created by ensure_schema; this is a no-op guard.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def val_client(seeded_db: int) -> AsyncClient:  # noqa: ARG001
    """Standalone FastAPI app with only the valuations router."""
    app = FastAPI(lifespan=_val_lifespan)
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


# ---------------------------------------------------------------------------
# Unit tests: ComparablesValuationAdapter directly
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_adapter_median_correct(seeded_db: int) -> None:
    """Median over the 5 seeded prices must equal 1_200_000; band verified."""
    async with async_session_factory() as session:
        adapter = ComparablesValuationAdapter()
        result = await adapter.estimate(
            session,
            make=_MAKE,
            model=_MODEL,
            year=_YEAR,
            mileage_km=None,
            price_eur_cents=_FAIR_PRICE,
        )
    assert result.sample_size == 5
    assert result.estimate_eur_cents == _MEDIAN
    # statistics.quantiles(prices, n=4) exclusive default → p25=900_000, p75=1_500_000
    assert result.low_eur_cents == 900_000
    assert result.high_eur_cents == 1_500_000
    assert result.low_eur_cents is not None
    assert result.high_eur_cents is not None
    assert result.low_eur_cents <= result.estimate_eur_cents <= result.high_eur_cents


@pytest.mark.anyio
async def test_adapter_great_deal(seeded_db: int) -> None:
    """Subject at 700_000 is ~41 % below median → deal_score GREAT."""
    async with async_session_factory() as session:
        adapter = ComparablesValuationAdapter()
        result = await adapter.estimate(
            session,
            make=_MAKE,
            model=_MODEL,
            year=_YEAR,
            mileage_km=None,
            price_eur_cents=_GREAT_PRICE,
        )
    assert result.deal_score == DealScore.GREAT
    assert result.pct_vs_market is not None
    assert result.pct_vs_market < -0.15


@pytest.mark.anyio
async def test_adapter_high_price(seeded_db: int) -> None:
    """Subject at 1_600_000 is ~33 % above median → deal_score HIGH."""
    async with async_session_factory() as session:
        adapter = ComparablesValuationAdapter()
        result = await adapter.estimate(
            session,
            make=_MAKE,
            model=_MODEL,
            year=_YEAR,
            mileage_km=None,
            price_eur_cents=_HIGH_PRICE,
        )
    assert result.deal_score == DealScore.HIGH
    assert result.pct_vs_market is not None
    assert result.pct_vs_market > 0.10


@pytest.mark.anyio
async def test_adapter_fair_deal(seeded_db: int) -> None:
    """Subject at median → pct 0.0 → deal_score FAIR."""
    async with async_session_factory() as session:
        adapter = ComparablesValuationAdapter()
        result = await adapter.estimate(
            session,
            make=_MAKE,
            model=_MODEL,
            year=_YEAR,
            mileage_km=None,
            price_eur_cents=_FAIR_PRICE,
        )
    assert result.deal_score == DealScore.FAIR


@pytest.mark.anyio
async def test_adapter_unknown_when_no_comps(ensure_schema: None) -> None:  # noqa: ARG001
    """A make/model with zero comparables → sample_size=0, deal_score=UNKNOWN."""
    async with async_session_factory() as session:
        adapter = ComparablesValuationAdapter()
        result = await adapter.estimate(
            session,
            make="Nonexistent",
            model="Ghost",
            year=2020,
            mileage_km=None,
            price_eur_cents=500_000,
        )
    assert result.sample_size == 0
    assert result.deal_score == DealScore.UNKNOWN
    assert result.estimate_eur_cents is None


@pytest.mark.anyio
async def test_adapter_no_price_returns_unknown(seeded_db: int) -> None:
    """Omitting price_eur_cents → deal_score UNKNOWN even with enough comps."""
    async with async_session_factory() as session:
        adapter = ComparablesValuationAdapter()
        result = await adapter.estimate(
            session,
            make=_MAKE,
            model=_MODEL,
            year=_YEAR,
            mileage_km=None,
            price_eur_cents=None,
        )
    assert result.deal_score == DealScore.UNKNOWN
    assert result.sample_size == 5
    assert result.estimate_eur_cents == _MEDIAN
    assert result.low_eur_cents is not None
    assert result.high_eur_cents is not None
    assert result.low_eur_cents <= result.estimate_eur_cents <= result.high_eur_cents


@pytest.mark.anyio
async def test_adapter_draft_listings_excluded(ensure_schema: None) -> None:  # noqa: ARG001
    """DRAFT listings must not be counted as comparables."""
    seller_id = await _make_seller("draft-seller@example.com")
    async with async_session_factory() as session:
        vehicle = Vehicle(
            make="Draftonlymark",
            model="Draftonlymodel",
            year=2020,
            fuel=FuelType.PETROL,
            body=BodyType.HATCHBACK,
            transmission=Transmission.MANUAL,
        )
        session.add(vehicle)
        await session.flush()
        listing = Listing(
            seller_id=seller_id,
            vehicle_id=vehicle.id,
            title="Draft listing",
            price_eur_cents=900_000,
            status=ListingStatus.DRAFT,  # not active
        )
        session.add(listing)
        await session.commit()

    async with async_session_factory() as session:
        adapter = ComparablesValuationAdapter()
        result = await adapter.estimate(
            session,
            make="Draftonlymark",
            model="Draftonlymodel",
            year=2020,
            mileage_km=None,
            price_eur_cents=900_000,
        )
    assert result.sample_size == 0
    assert result.deal_score == DealScore.UNKNOWN


# ---------------------------------------------------------------------------
# HTTP tests: GET /v1/valuations via standalone app
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_http_valuation_great(val_client: AsyncClient) -> None:
    """HTTP endpoint returns great deal for very cheap price."""
    resp = await val_client.get(
        "/v1/valuations",
        params={
            "make": _MAKE,
            "model": _MODEL,
            "year": _YEAR,
            "price_eur_cents": _GREAT_PRICE,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["deal_score"] == "great"
    assert body["sample_size"] == 5
    assert body["estimate_eur_cents"] == _MEDIAN


@pytest.mark.anyio
async def test_http_valuation_high(val_client: AsyncClient) -> None:
    """HTTP endpoint returns high for overpriced subject."""
    resp = await val_client.get(
        "/v1/valuations",
        params={
            "make": _MAKE,
            "model": _MODEL,
            "year": _YEAR,
            "price_eur_cents": _HIGH_PRICE,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["deal_score"] == "high"


@pytest.mark.anyio
async def test_http_valuation_unknown_few_comps(val_client: AsyncClient) -> None:
    """Unknown make/model → sample_size 0, deal_score unknown."""
    resp = await val_client.get(
        "/v1/valuations",
        params={
            "make": "Lada",
            "model": "Niva",
            "year": 2005,
            "price_eur_cents": 200_000,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["deal_score"] == "unknown"
    assert body["sample_size"] == 0
    assert body["estimate_eur_cents"] is None


@pytest.mark.anyio
async def test_http_valuation_missing_make_400(val_client: AsyncClient) -> None:
    """Missing make → HTTP 400."""
    resp = await val_client.get(
        "/v1/valuations",
        params={"model": _MODEL, "year": _YEAR, "price_eur_cents": _FAIR_PRICE},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_http_valuation_missing_model_400(val_client: AsyncClient) -> None:
    """Missing model → HTTP 400."""
    resp = await val_client.get(
        "/v1/valuations",
        params={"make": _MAKE, "year": _YEAR, "price_eur_cents": _FAIR_PRICE},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_http_valuation_missing_year_400(val_client: AsyncClient) -> None:
    """Missing year → HTTP 400."""
    resp = await val_client.get(
        "/v1/valuations",
        params={"make": _MAKE, "model": _MODEL, "price_eur_cents": _FAIR_PRICE},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_http_valuation_no_price_unknown(val_client: AsyncClient) -> None:
    """No price_eur_cents → deal_score unknown, estimate still returned."""
    resp = await val_client.get(
        "/v1/valuations",
        params={"make": _MAKE, "model": _MODEL, "year": _YEAR},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["deal_score"] == "unknown"
    assert body["estimate_eur_cents"] == _MEDIAN
    assert body["sample_size"] == 5
