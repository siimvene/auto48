"""Tests for the fraud/risk assessment service and GET /v1/listings/{id}/risk.

Schema setup: a session-scoped autouse fixture runs ``create_all`` once before
any test in this module — sharing the same SQLite file from conftest env vars.

Sentinel make/model keeps seeded data isolated from other test suites.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import auto48.models  # noqa: F401 — register all ORM metadata on Base
from auto48.api.routers.risk import router
from auto48.db import Base, async_session_factory, engine
from auto48.models.listing import Listing, ListingStatus
from auto48.models.seller import SellerProfile, SellerType
from auto48.models.user import User
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle
from auto48.services.fraud import (
    RiskAssessment,
    RiskFlag,
    _aggregate,
    _check_incomplete_fields,
    _check_scam_text_str,
    _is_placeholder_title,
    _matches_scam_patterns,
    assess_listing_risk,
)

# ---------------------------------------------------------------------------
# Sentinel make/model — unique across ALL test modules sharing the SQLite DB.
# ---------------------------------------------------------------------------

_MAKE = "Fraudtestmark"
_MODEL = "Riskcarmodel"
_YEAR = 2020

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def _make_seller(email: str) -> int:
    """Create User + SellerProfile; return profile id."""
    async with async_session_factory() as session:
        user = User(email=email, display_name="Risk Seller")
        session.add(user)
        await session.flush()
        profile = SellerProfile(user_id=user.id, type=SellerType.PRIVATE)
        session.add(profile)
        await session.flush()
        await session.commit()
        return int(profile.id)


async def _make_listing(
    seller_id: int,
    *,
    vin: str | None = None,
    title: str = "Test car",
    description: str | None = "Good condition, one owner.",
    price_eur_cents: int = 1_000_000,
    mileage_km: int | None = 80_000,
    status: ListingStatus = ListingStatus.ACTIVE,
    make: str = _MAKE,
    model: str = _MODEL,
    year: int = _YEAR,
) -> int:
    """Insert a Vehicle+Listing into the DB; return listing id."""
    async with async_session_factory() as session:
        vehicle = Vehicle(
            vin=vin,
            make=make,
            model=model,
            year=year,
            fuel=FuelType.PETROL,
            body=BodyType.SEDAN,
            transmission=Transmission.MANUAL,
        )
        session.add(vehicle)
        await session.flush()
        listing = Listing(
            seller_id=seller_id,
            vehicle_id=vehicle.id,
            title=title,
            description=description,
            price_eur_cents=price_eur_cents,
            mileage_km=mileage_km,
            status=status,
        )
        session.add(listing)
        await session.flush()
        await session.commit()
        return int(listing.id)


# ---------------------------------------------------------------------------
# Module-scoped schema creation + seed data
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
async def ensure_schema() -> None:
    """Create all tables once for this module."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="module")
async def seller_id(ensure_schema: None) -> int:  # noqa: ARG001
    return await _make_seller("fraud-seller@example.com")


@pytest.fixture(scope="module")
async def clean_listing_id(seller_id: int) -> int:
    """A clean listing with no fraud signals → low risk.

    Uses a unique make/model that has zero comparables so the underpriced
    signal cannot trigger (no market median to compare against).
    """
    return await _make_listing(
        seller_id,
        vin="CLEANVIN0000001",
        title="Clean car for sale",
        description="Regular car, no issues.",
        price_eur_cents=1_000_000,
        mileage_km=80_000,
        # Unique make+model — no comparables seeded → valuation returns UNKNOWN.
        make="Cleanmark",
        model="Cleanmodel",
    )


@pytest.fixture(scope="module")
async def dup_listing_ids(seller_id: int) -> tuple[int, int]:
    """Two ACTIVE listings with the same VIN — should trigger duplicate_listing."""
    vin = "DUPVINTEST00001"
    id1 = await _make_listing(
        seller_id,
        vin=vin,
        title="Dup car listing A",
        description="First listing.",
        price_eur_cents=900_000,
        mileage_km=60_000,
    )
    id2 = await _make_listing(
        seller_id,
        vin=vin,
        title="Dup car listing B",
        description="Second listing same VIN.",
        price_eur_cents=910_000,
        mileage_km=60_500,
    )
    return id1, id2


@pytest.fixture(scope="module")
async def underpriced_listing_id(seller_id: int) -> int:
    """A listing priced 50% below market, with 4 comparables at higher price.

    Seeds 4 ACTIVE comparable listings at 2_000_000 cents each (median=2_000_000),
    then inserts the subject at 500_000 cents (pct_vs_market ≈ -75 % < -30 %).
    """
    comp_price = 2_000_000
    async with async_session_factory() as session:
        for i in range(4):
            v = Vehicle(
                make=_MAKE,
                model=_MODEL,
                year=_YEAR,
                fuel=FuelType.PETROL,
                body=BodyType.SEDAN,
                transmission=Transmission.MANUAL,
            )
            session.add(v)
            await session.flush()
            lst = Listing(
                seller_id=seller_id,
                vehicle_id=v.id,
                title=f"Comp listing {i}",
                description="Comparable.",
                price_eur_cents=comp_price,
                mileage_km=80_000,
                status=ListingStatus.ACTIVE,
            )
            session.add(lst)
        await session.commit()

    return await _make_listing(
        seller_id,
        title="Suspiciously cheap car",
        description="Great car, must sell fast.",
        price_eur_cents=500_000,  # 75% below market
        mileage_km=80_000,
    )


@pytest.fixture(scope="module")
async def scam_text_listing_id(seller_id: int) -> int:
    """A listing with scam-bait text in the description."""
    return await _make_listing(
        seller_id,
        vin="SCAMVINTEST0001",
        title="Car for quick sale",
        description=(
            "Contact via email only. Payment via western union accepted. "
            "Pay deposit before viewing to reserve."
        ),
        price_eur_cents=1_200_000,
        mileage_km=55_000,
    )


# ---------------------------------------------------------------------------
# FastAPI test client (risk router only)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _risk_lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def risk_client(ensure_schema: None) -> AsyncClient:  # noqa: ARG001
    """Standalone FastAPI app with only the risk router."""
    app = FastAPI(lifespan=_risk_lifespan)
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


# ---------------------------------------------------------------------------
# Unit tests: pure helper functions
# ---------------------------------------------------------------------------


def test_matches_scam_patterns_shipping() -> None:
    assert _matches_scam_patterns("Please arrange shipping to my address")


def test_matches_scam_patterns_western_union() -> None:
    assert _matches_scam_patterns("Payment by Western Union only")


def test_matches_scam_patterns_wire_transfer() -> None:
    assert _matches_scam_patterns("Send wire transfer before I release the car")


def test_matches_scam_patterns_pay_before_viewing() -> None:
    assert _matches_scam_patterns("Pay deposit before viewing the vehicle")


def test_matches_scam_patterns_clean_text() -> None:
    assert not _matches_scam_patterns("Nice car, call between 9-17, test drive welcome")


def test_is_placeholder_title_test() -> None:
    assert _is_placeholder_title("test")


def test_is_placeholder_title_untitled() -> None:
    assert _is_placeholder_title("Untitled")


def test_is_placeholder_title_real_title() -> None:
    assert not _is_placeholder_title("2020 Toyota Corolla, excellent condition")


def test_aggregate_no_flags() -> None:
    score, level = _aggregate([])
    assert score == 0
    assert level == "low"


def test_aggregate_high_flag() -> None:
    flags = [RiskFlag(code="x", severity="high", detail="d")]
    score, level = _aggregate(flags)
    assert score == 50
    assert level == "medium"


def test_aggregate_two_high_flags_capped() -> None:
    flags = [
        RiskFlag(code="a", severity="high", detail="d"),
        RiskFlag(code="b", severity="high", detail="d"),
        RiskFlag(code="c", severity="high", detail="d"),
    ]
    score, level = _aggregate(flags)
    assert score == 100
    assert level == "high"


def test_check_scam_text_triggered() -> None:
    """_check_scam_text_str returns a flag when description contains a scam pattern."""
    flag = _check_scam_text_str(
        "Pay western union to secure the vehicle before viewing"
    )
    assert flag is not None
    assert flag.code == "suspicious_text"
    assert flag.severity == "high"


def test_check_scam_text_none_description() -> None:
    assert _check_scam_text_str(None) is None


def test_check_incomplete_missing_vin_and_description() -> None:
    flag = _check_incomplete_fields(
        title="Good car",
        description=None,
        vin=None,
    )
    assert flag is not None
    assert flag.code == "incomplete_data"
    assert flag.severity == "low"


def test_check_incomplete_has_vin_no_description() -> None:
    """VIN present → not flagged even without description."""
    assert (
        _check_incomplete_fields(title="Good car", description=None, vin="ABC123")
        is None
    )


def test_check_incomplete_placeholder_title() -> None:
    flag = _check_incomplete_fields(
        title="test",
        description="Some description",
        vin="SOMEVIN",
    )
    assert flag is not None
    assert flag.code == "incomplete_data"


# ---------------------------------------------------------------------------
# Integration tests: assess_listing_risk via DB
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_clean_listing_low_risk(clean_listing_id: int) -> None:
    """A clean listing should have low risk level and no flags."""
    async with async_session_factory() as session:
        listing = await session.get(Listing, clean_listing_id)
        assert listing is not None
        result: RiskAssessment = await assess_listing_risk(session, listing)
    assert result.level == "low"
    assert result.score < 30
    # Should have no flags (clean listing with unique VIN, no scam text, fair price)
    assert all(f.code != "suspicious_text" for f in result.flags)
    assert all(f.code != "underpriced_vs_market" for f in result.flags)


@pytest.mark.anyio
async def test_duplicate_vin_flagged(dup_listing_ids: tuple[int, int]) -> None:
    """Each listing in a VIN-duplicate pair must trigger duplicate_listing flag."""
    id1, id2 = dup_listing_ids
    async with async_session_factory() as session:
        listing1 = await session.get(Listing, id1)
        assert listing1 is not None
        result1 = await assess_listing_risk(session, listing1)

    async with async_session_factory() as session:
        listing2 = await session.get(Listing, id2)
        assert listing2 is not None
        result2 = await assess_listing_risk(session, listing2)

    dup_codes1 = [f.code for f in result1.flags]
    dup_codes2 = [f.code for f in result2.flags]
    assert "duplicate_listing" in dup_codes1
    assert "duplicate_listing" in dup_codes2

    # At least one duplicate flag must have high severity (VIN match)
    severities1 = {f.severity for f in result1.flags if f.code == "duplicate_listing"}
    assert "high" in severities1


@pytest.mark.anyio
async def test_underpriced_flagged(underpriced_listing_id: int) -> None:
    """Listing priced 75% below market with >=3 comps must flag underpriced_vs_market."""
    async with async_session_factory() as session:
        listing = await session.get(Listing, underpriced_listing_id)
        assert listing is not None
        result = await assess_listing_risk(session, listing)
    codes = [f.code for f in result.flags]
    assert "underpriced_vs_market" in codes
    under_flag = next(f for f in result.flags if f.code == "underpriced_vs_market")
    assert under_flag.severity == "high"
    assert result.level in ("medium", "high")


@pytest.mark.anyio
async def test_scam_text_flagged(scam_text_listing_id: int) -> None:
    """Listing with scam-bait description must flag suspicious_text."""
    async with async_session_factory() as session:
        listing = await session.get(Listing, scam_text_listing_id)
        assert listing is not None
        result = await assess_listing_risk(session, listing)
    codes = [f.code for f in result.flags]
    assert "suspicious_text" in codes
    scam_flag = next(f for f in result.flags if f.code == "suspicious_text")
    assert scam_flag.severity == "high"
    assert result.level in ("medium", "high")


# ---------------------------------------------------------------------------
# HTTP integration tests: GET /v1/listings/{id}/risk
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_http_risk_404(risk_client: AsyncClient) -> None:
    """Non-existent listing → HTTP 404."""
    resp = await risk_client.get("/v1/listings/999999/risk")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_http_risk_clean_listing(
    risk_client: AsyncClient,
    clean_listing_id: int,
) -> None:
    """Clean listing → 200, low level, no suspicious flags."""
    resp = await risk_client.get(f"/v1/listings/{clean_listing_id}/risk")
    assert resp.status_code == 200
    body = resp.json()
    assert body["level"] == "low"
    assert isinstance(body["score"], int)
    assert 0 <= body["score"] <= 100
    assert isinstance(body["flags"], list)


@pytest.mark.anyio
async def test_http_risk_duplicate(
    risk_client: AsyncClient,
    dup_listing_ids: tuple[int, int],
) -> None:
    """Duplicate VIN listing → 200, duplicate_listing flag present."""
    listing_id = dup_listing_ids[0]
    resp = await risk_client.get(f"/v1/listings/{listing_id}/risk")
    assert resp.status_code == 200
    body = resp.json()
    codes = [f["code"] for f in body["flags"]]
    assert "duplicate_listing" in codes


@pytest.mark.anyio
async def test_http_risk_scam_text(
    risk_client: AsyncClient,
    scam_text_listing_id: int,
) -> None:
    """Scam-text listing → 200, suspicious_text flag present."""
    resp = await risk_client.get(f"/v1/listings/{scam_text_listing_id}/risk")
    assert resp.status_code == 200
    body = resp.json()
    codes = [f["code"] for f in body["flags"]]
    assert "suspicious_text" in codes


@pytest.mark.anyio
async def test_http_risk_underpriced(
    risk_client: AsyncClient,
    underpriced_listing_id: int,
) -> None:
    """Underpriced listing → 200, underpriced_vs_market flag present."""
    resp = await risk_client.get(f"/v1/listings/{underpriced_listing_id}/risk")
    assert resp.status_code == 200
    body = resp.json()
    codes = [f["code"] for f in body["flags"]]
    assert "underpriced_vs_market" in codes
    assert body["level"] in ("medium", "high")


@pytest.mark.anyio
async def test_http_risk_response_schema(
    risk_client: AsyncClient,
    clean_listing_id: int,
) -> None:
    """Response must have all required fields with correct types."""
    resp = await risk_client.get(f"/v1/listings/{clean_listing_id}/risk")
    assert resp.status_code == 200
    body = resp.json()
    assert "score" in body
    assert "level" in body
    assert "flags" in body
    assert body["level"] in ("low", "medium", "high")
    for flag in body["flags"]:
        assert "code" in flag
        assert "severity" in flag
        assert "detail" in flag
        assert flag["severity"] in ("low", "medium", "high")
