"""Tests for StubInsuranceAdapter math + TCO/financing HTTP endpoints.

Schema setup: a module-scoped autouse fixture runs ``create_all`` once before
any test in this module.

Sentinel make/model "Tcotestmark"/"Tcocarmodel" is used to keep seeded listings
isolated in the shared SQLite database from other test modules.
"""

from __future__ import annotations

import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import auto48.models  # noqa: F401 — register all ORM metadata on Base
from auto48.adapters.insurance.stub import DEFAULT_APR_PCT, StubInsuranceAdapter
from auto48.api.routers.tco import router
from auto48.db import Base, async_session_factory, engine
from auto48.models.listing import Listing, ListingStatus
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.user import User
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle

# ---------------------------------------------------------------------------
# Sentinel identifiers (unique to this module to prevent cross-test pollution)
# ---------------------------------------------------------------------------

_MAKE = "Tcotestmark"
_MODEL = "Tcocarmodel"
_YEAR = 2020
_PRICE_EUR_CENTS = 15_000_00  # 15 000 EUR

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_tco_seller(email: str = "tco-seller@example.com") -> int:
    """Create a User + SellerProfile and return the profile id."""
    async with async_session_factory() as session:
        user = User(email=email, display_name="TCO Seller")
        session.add(user)
        await session.flush()
        profile = SellerProfile(user_id=user.id, type=SellerType.PRIVATE)
        session.add(profile)
        await session.flush()
        await session.commit()
        return int(profile.id)


async def _seed_tco_listing(seller_id: int) -> int:
    """Insert a Vehicle + Listing and return the listing id."""
    async with async_session_factory() as session:
        vehicle = Vehicle(
            make=_MAKE,
            model=_MODEL,
            year=_YEAR,
            fuel=FuelType.PETROL,
            body=BodyType.SEDAN,
            transmission=Transmission.MANUAL,
            specs={"power_kw": 110.0},
        )
        session.add(vehicle)
        await session.flush()
        listing = Listing(
            seller_id=seller_id,
            vehicle_id=vehicle.id,
            title="TCO test listing",
            price_eur_cents=_PRICE_EUR_CENTS,
            mileage_km=60_000,
            status=ListingStatus.ACTIVE,
        )
        session.add(listing)
        await session.flush()
        await session.commit()
        return int(listing.id)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
async def ensure_schema() -> None:
    """Create all tables once for this test module."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="module")
async def tco_seller_id(ensure_schema: None) -> int:  # noqa: ARG001
    return await _make_tco_seller()


@pytest.fixture(scope="module")
async def tco_listing_id(tco_seller_id: int) -> int:
    return await _seed_tco_listing(tco_seller_id)


@asynccontextmanager
async def _tco_lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def tco_client(tco_listing_id: int) -> AsyncClient:  # noqa: ARG001
    """Standalone FastAPI app with only the TCO router."""
    app = FastAPI(lifespan=_tco_lifespan)
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


# ---------------------------------------------------------------------------
# Unit tests: StubInsuranceAdapter math directly
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_stub_financing_annuity_formula() -> None:
    """Monthly payment must match the standard annuity formula M = P*r/(1-(1+r)^-n)."""
    adapter = StubInsuranceAdapter()
    principal = 10_000_00  # 10 000 EUR in cents
    term = 60

    quote = await adapter.quote_financing(
        price_eur_cents=principal,
        down_payment_eur_cents=0,
        term_months=term,
    )

    # Recompute expected value using the same formula.
    r = DEFAULT_APR_PCT / 100.0 / 12.0
    expected_monthly = principal * r / (1.0 - math.pow(1.0 + r, -term))
    expected_monthly_cents = int(round(expected_monthly))

    assert quote.monthly_eur_cents == expected_monthly_cents
    assert quote.term_months == term
    assert quote.apr_pct == DEFAULT_APR_PCT


@pytest.mark.anyio
async def test_stub_financing_total_payable_invariant() -> None:
    """total_payable must equal monthly × term."""
    adapter = StubInsuranceAdapter()
    quote = await adapter.quote_financing(
        price_eur_cents=20_000_00,
        down_payment_eur_cents=5_000_00,
        term_months=48,
    )
    assert quote.total_payable_eur_cents == quote.monthly_eur_cents * quote.term_months


@pytest.mark.anyio
async def test_stub_financing_total_interest_invariant() -> None:
    """total_interest must equal total_payable − principal."""
    adapter = StubInsuranceAdapter()
    price = 25_000_00
    down = 5_000_00
    principal = price - down

    quote = await adapter.quote_financing(
        price_eur_cents=price,
        down_payment_eur_cents=down,
        term_months=60,
    )
    assert quote.total_interest_eur_cents == quote.total_payable_eur_cents - principal


@pytest.mark.anyio
async def test_stub_financing_zero_principal() -> None:
    """Down payment >= price → all zero payments."""
    adapter = StubInsuranceAdapter()
    price = 5_000_00
    quote = await adapter.quote_financing(
        price_eur_cents=price,
        down_payment_eur_cents=price,  # full down payment
        term_months=60,
    )
    assert quote.monthly_eur_cents == 0
    assert quote.total_payable_eur_cents == 0
    assert quote.total_interest_eur_cents == 0


@pytest.mark.anyio
async def test_stub_financing_monthly_reasonable() -> None:
    """Monthly payment for a typical 15k EUR car over 60 months is roughly 250–400 EUR."""
    adapter = StubInsuranceAdapter()
    quote = await adapter.quote_financing(
        price_eur_cents=15_000_00,
        down_payment_eur_cents=0,
        term_months=60,
    )
    # 250 EUR = 25_000 cents, 400 EUR = 40_000 cents
    assert 25_000 <= quote.monthly_eur_cents <= 40_000


@pytest.mark.anyio
async def test_stub_insurance_quote_positive() -> None:
    """Insurance quote must return positive annual and monthly values."""
    adapter = StubInsuranceAdapter()
    quote = await adapter.quote_insurance(
        make=_MAKE,
        model=_MODEL,
        year=_YEAR,
        fuel="petrol",
        power_kw=110.0,
    )
    assert quote.annual_eur_cents > 0
    assert quote.monthly_eur_cents > 0
    assert quote.kind == "estimate"


@pytest.mark.anyio
async def test_stub_insurance_ev_cheaper_than_petrol() -> None:
    """Electric vehicle insurance should be cheaper than equivalent petrol."""
    adapter = StubInsuranceAdapter()
    petrol = await adapter.quote_insurance(
        make=_MAKE,
        model=_MODEL,
        year=2022,
        fuel="petrol",
        power_kw=150.0,
    )
    electric = await adapter.quote_insurance(
        make=_MAKE,
        model=_MODEL,
        year=2022,
        fuel="electric",
        power_kw=150.0,
    )
    assert electric.annual_eur_cents < petrol.annual_eur_cents


# ---------------------------------------------------------------------------
# HTTP tests: GET /v1/listings/{id}/tco
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tco_endpoint_returns_200(tco_client: AsyncClient, tco_listing_id: int) -> None:
    """TCO endpoint returns 200 with correct listing_id."""
    resp = await tco_client.get(f"/v1/listings/{tco_listing_id}/tco")
    assert resp.status_code == 200
    body = resp.json()
    assert body["listing_id"] == tco_listing_id


@pytest.mark.anyio
async def test_tco_components_positive(tco_client: AsyncClient, tco_listing_id: int) -> None:
    """All TCO components must be positive for a valid petrol listing."""
    resp = await tco_client.get(
        f"/v1/listings/{tco_listing_id}/tco",
        params={"years": 3, "annual_km": 15000},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["years_count"] == 3
    assert body["annual_km"] == 15000
    assert body["total_registration_eur_cents"] > 0
    assert body["total_fuel_eur_cents"] > 0
    assert body["total_maintenance_eur_cents"] > 0
    assert body["total_insurance_eur_cents"] > 0
    assert body["total_depreciation_eur_cents"] > 0


@pytest.mark.anyio
async def test_tco_sum_invariant(tco_client: AsyncClient, tco_listing_id: int) -> None:
    """total_eur_cents must equal the sum of all component totals."""
    resp = await tco_client.get(
        f"/v1/listings/{tco_listing_id}/tco",
        params={"years": 5, "annual_km": 15000},
    )
    assert resp.status_code == 200
    body = resp.json()

    expected_total = (
        body["total_registration_eur_cents"]
        + body["total_fuel_eur_cents"]
        + body["total_maintenance_eur_cents"]
        + body["total_insurance_eur_cents"]
        + body["total_depreciation_eur_cents"]
    )
    assert body["total_eur_cents"] == expected_total


@pytest.mark.anyio
async def test_tco_per_year_sum_equals_total(tco_client: AsyncClient, tco_listing_id: int) -> None:
    """Sum of per_year[i].total_eur_cents must equal total_eur_cents."""
    resp = await tco_client.get(
        f"/v1/listings/{tco_listing_id}/tco",
        params={"years": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    per_year_sum = sum(y["total_eur_cents"] for y in body["per_year"])
    assert per_year_sum == body["total_eur_cents"]


@pytest.mark.anyio
async def test_tco_correct_number_of_years(tco_client: AsyncClient, tco_listing_id: int) -> None:
    """Number of per_year entries must match the years query param."""
    for n in (1, 3, 7):
        resp = await tco_client.get(
            f"/v1/listings/{tco_listing_id}/tco",
            params={"years": n},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["per_year"]) == n


@pytest.mark.anyio
async def test_tco_missing_listing_returns_404(tco_client: AsyncClient) -> None:
    """Nonexistent listing_id must return HTTP 404."""
    resp = await tco_client.get("/v1/listings/999999/tco")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# HTTP tests: GET /v1/listings/{id}/financing
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_financing_endpoint_returns_200(tco_client: AsyncClient, tco_listing_id: int) -> None:
    """Financing endpoint returns 200 for a valid listing."""
    resp = await tco_client.get(
        f"/v1/listings/{tco_listing_id}/financing",
        params={"down_payment_eur_cents": 0, "term_months": 60},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["term_months"] == 60
    assert body["monthly_eur_cents"] > 0


@pytest.mark.anyio
async def test_financing_total_payable_invariant_http(
    tco_client: AsyncClient, tco_listing_id: int
) -> None:
    """total_payable_eur_cents must equal monthly_eur_cents × term_months via HTTP."""
    resp = await tco_client.get(
        f"/v1/listings/{tco_listing_id}/financing",
        params={"down_payment_eur_cents": 100_000, "term_months": 48},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_payable_eur_cents"] == body["monthly_eur_cents"] * body["term_months"]


@pytest.mark.anyio
async def test_financing_missing_listing_returns_404(tco_client: AsyncClient) -> None:
    """Nonexistent listing_id must return HTTP 404 for financing endpoint."""
    resp = await tco_client.get("/v1/listings/999999/financing")
    assert resp.status_code == 404
