"""Tests for EV charging helpers and the charging-cost HTTP endpoint.

Three areas:
1. Pure unit tests for ``charging.py`` service helpers.
2. HTTP tests: minimal FastAPI app mounting only the charging router (no DB needed).
3. DB round-trip: Vehicle can be created with EV fields and read back.

Sentinel make "Evtestmake" is unique to this module.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import auto48.models  # noqa: F401 — register all ORM metadata on Base
from auto48.api.routers.charging import router
from auto48.db import Base, async_session_factory, engine
from auto48.models.vehicle import BodyType, FuelType, Transmission, Vehicle
from auto48.services.charging import (
    DEFAULT_ANNUAL_KM,
    DEFAULT_PRICE_PER_KWH_EUR_CENTS,
    charging_cost_eur_cents,
    consumption_kwh_per_100km,
)

# ---------------------------------------------------------------------------
# Sentinel identifiers
# ---------------------------------------------------------------------------

_MAKE = "Evtestmake"
_MODEL = "Evtestmodel"

# ---------------------------------------------------------------------------
# Module-level schema setup
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
async def ensure_schema() -> None:
    """Create all tables once for this test module."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------
# Minimal charging-router app fixture
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _noop_lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    yield


@pytest.fixture
async def charging_client() -> AsyncClient:
    """Standalone FastAPI app with only the charging router — no DB."""
    app = FastAPI(lifespan=_noop_lifespan)
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=transport, base_url="http://test") as ac,
    ):
        yield ac


# ---------------------------------------------------------------------------
# Unit tests: consumption_kwh_per_100km
# ---------------------------------------------------------------------------


def test_consumption_known_value() -> None:
    """77 kWh / 400 km = 19.25 kWh/100 km."""
    result = consumption_kwh_per_100km(77.0, 400)
    assert result is not None
    assert abs(result - 19.25) < 0.01


def test_consumption_zero_range_returns_none() -> None:
    """range_km == 0 must return None, not raise."""
    assert consumption_kwh_per_100km(50.0, 0) is None


def test_consumption_negative_range_returns_none() -> None:
    """Negative range must return None."""
    assert consumption_kwh_per_100km(50.0, -100) is None


def test_consumption_scales_linearly() -> None:
    """Doubling the range halves the consumption."""
    c1 = consumption_kwh_per_100km(60.0, 300)
    c2 = consumption_kwh_per_100km(60.0, 600)
    assert c1 is not None and c2 is not None
    assert abs(c1 - 2 * c2) < 0.001


# ---------------------------------------------------------------------------
# Unit tests: charging_cost_eur_cents
# ---------------------------------------------------------------------------


def test_charging_cost_known_value() -> None:
    """Manual check: 77 kWh / 400 km * 100 = 19.25 kWh/100; 15000 km → 2887.5 kWh;
    × 1400 c/kWh = 4_042_500 EUR cents = 40 425 EUR.
    """
    cost = charging_cost_eur_cents(
        range_km=400,
        battery_kwh=77.0,
        annual_km=15_000,
        price_per_kwh_eur_cents=1_400,
    )
    assert cost == 4_042_500


def test_charging_cost_uses_defaults() -> None:
    """Calling with only required args uses DEFAULT_ANNUAL_KM and DEFAULT_PRICE_PER_KWH."""
    cost_explicit = charging_cost_eur_cents(
        range_km=400,
        battery_kwh=77.0,
        annual_km=DEFAULT_ANNUAL_KM,
        price_per_kwh_eur_cents=DEFAULT_PRICE_PER_KWH_EUR_CENTS,
    )
    cost_defaults = charging_cost_eur_cents(range_km=400, battery_kwh=77.0)
    assert cost_defaults == cost_explicit


def test_charging_cost_zero_range_raises() -> None:
    """range_km == 0 must raise ValueError."""
    with pytest.raises(ValueError, match="range_km"):
        charging_cost_eur_cents(range_km=0, battery_kwh=50.0)


def test_charging_cost_proportional_to_annual_km() -> None:
    """Doubling annual_km must double cost."""
    c1 = charging_cost_eur_cents(range_km=300, battery_kwh=60.0, annual_km=10_000)
    c2 = charging_cost_eur_cents(range_km=300, battery_kwh=60.0, annual_km=20_000)
    assert c2 == 2 * c1


def test_charging_cost_proportional_to_price() -> None:
    """Doubling the electricity price must double cost."""
    c1 = charging_cost_eur_cents(
        range_km=300, battery_kwh=60.0, price_per_kwh_eur_cents=1_000
    )
    c2 = charging_cost_eur_cents(
        range_km=300, battery_kwh=60.0, price_per_kwh_eur_cents=2_000
    )
    assert c2 == 2 * c1


# ---------------------------------------------------------------------------
# HTTP tests: GET /v1/vehicles/charging-cost
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_charging_cost_endpoint_200(charging_client: AsyncClient) -> None:
    """Valid params return 200 with correct structure."""
    resp = await charging_client.get(
        "/v1/vehicles/charging-cost",
        params={"battery_kwh": 77.0, "range_km": 400},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["battery_kwh"] == 77.0
    assert body["range_km"] == 400
    assert body["annual_cost_eur_cents"] > 0
    assert body["monthly_cost_eur_cents"] > 0


@pytest.mark.anyio
async def test_charging_cost_monthly_equals_annual_div12(charging_client: AsyncClient) -> None:
    """monthly_cost must equal round(annual / 12)."""
    resp = await charging_client.get(
        "/v1/vehicles/charging-cost",
        params={"battery_kwh": 60.0, "range_km": 350},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["monthly_cost_eur_cents"] == round(body["annual_cost_eur_cents"] / 12)


@pytest.mark.anyio
async def test_charging_cost_consumption_field(charging_client: AsyncClient) -> None:
    """consumption_kwh_per_100km field must be present and close to manual calc."""
    resp = await charging_client.get(
        "/v1/vehicles/charging-cost",
        params={"battery_kwh": 50.0, "range_km": 250},
    )
    assert resp.status_code == 200
    body = resp.json()
    # 50 / 250 * 100 = 20.0
    assert abs(body["consumption_kwh_per_100km"] - 20.0) < 0.01


@pytest.mark.anyio
async def test_charging_cost_missing_battery_returns_400(charging_client: AsyncClient) -> None:
    """Omitting battery_kwh must return HTTP 400."""
    resp = await charging_client.get(
        "/v1/vehicles/charging-cost",
        params={"range_km": 400},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_charging_cost_missing_range_returns_400(charging_client: AsyncClient) -> None:
    """Omitting range_km must return HTTP 400."""
    resp = await charging_client.get(
        "/v1/vehicles/charging-cost",
        params={"battery_kwh": 60.0},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_charging_cost_missing_both_returns_400(charging_client: AsyncClient) -> None:
    """Omitting both battery_kwh and range_km must return HTTP 400."""
    resp = await charging_client.get("/v1/vehicles/charging-cost")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_charging_cost_custom_params(charging_client: AsyncClient) -> None:
    """Custom annual_km and price_per_kwh_eur_cents are reflected in response."""
    resp = await charging_client.get(
        "/v1/vehicles/charging-cost",
        params={
            "battery_kwh": 40.0,
            "range_km": 200,
            "annual_km": 20_000,
            "price_per_kwh_eur_cents": 2_000,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["annual_km"] == 20_000
    assert body["price_per_kwh_eur_cents"] == 2_000
    # Manual: 40/200*100=20 kWh/100; 20000km → 4000 kWh; × 2000c = 8_000_000 c
    assert body["annual_cost_eur_cents"] == 8_000_000


# ---------------------------------------------------------------------------
# DB round-trip: Vehicle with EV fields
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_vehicle_ev_fields_round_trip(ensure_schema: None) -> None:  # noqa: ARG001
    """A Vehicle can be created with all four EV fields and read back correctly."""
    async with async_session_factory() as session:
        vehicle = Vehicle(
            make=_MAKE,
            model=_MODEL,
            year=2023,
            fuel=FuelType.ELECTRIC,
            body=BodyType.SUV,
            transmission=Transmission.AUTOMATIC,
            battery_kwh=77.4,
            range_km=513,
            charge_power_kw=150.0,
            charge_port="ccs",
        )
        session.add(vehicle)
        await session.flush()
        vehicle_id = vehicle.id
        await session.commit()

    async with async_session_factory() as session:
        loaded = await session.get(Vehicle, vehicle_id)
        assert loaded is not None
        assert loaded.battery_kwh == 77.4
        assert loaded.range_km == 513
        assert loaded.charge_power_kw == 150.0
        assert loaded.charge_port == "ccs"
        assert loaded.fuel == FuelType.ELECTRIC


@pytest.mark.anyio
async def test_vehicle_ev_fields_default_none(ensure_schema: None) -> None:  # noqa: ARG001
    """A Vehicle created without EV fields has all four EV columns as None."""
    async with async_session_factory() as session:
        vehicle = Vehicle(
            make=_MAKE,
            model=f"{_MODEL}plain",
            year=2020,
            fuel=FuelType.PETROL,
            body=BodyType.HATCHBACK,
            transmission=Transmission.MANUAL,
        )
        session.add(vehicle)
        await session.flush()
        vehicle_id = vehicle.id
        await session.commit()

    async with async_session_factory() as session:
        loaded = await session.get(Vehicle, vehicle_id)
        assert loaded is not None
        assert loaded.battery_kwh is None
        assert loaded.range_km is None
        assert loaded.charge_power_kw is None
        assert loaded.charge_port is None


# ---------------------------------------------------------------------------
# Backward-compat: VehicleCreate without EV fields still works
# ---------------------------------------------------------------------------


def test_vehicle_create_backward_compat() -> None:
    """VehicleCreate without EV fields constructs successfully (all default None)."""
    from auto48.models.schemas import VehicleCreate

    vc = VehicleCreate(
        make="Toyota",
        model="Yaris",
        year=2019,
        fuel=FuelType.PETROL,
        body=BodyType.HATCHBACK,
        transmission=Transmission.MANUAL,
    )
    assert vc.battery_kwh is None
    assert vc.range_km is None
    assert vc.charge_power_kw is None
    assert vc.charge_port is None
