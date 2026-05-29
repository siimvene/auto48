"""Tests for the VehicleData port: StubAdapter (direct) + vehicles router (HTTP)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auto48.adapters.vehicle_data.stub import StubVehicleDataAdapter
from auto48.api.routers.vehicles import _get_adapter, router
from auto48.models.history import HistoryEventType, detect_rollback
from auto48.models.vehicle import BodyType, FuelType, Transmission
from auto48.ports.vehicle_data import VehicleHistoryRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(adapter_override=None) -> FastAPI:
    """Mount only the vehicles router; optionally inject a custom adapter."""
    app = FastAPI()
    app.include_router(router)
    if adapter_override is not None:
        app.dependency_overrides[_get_adapter] = lambda: adapter_override
    return app


@pytest.fixture
def stub() -> StubVehicleDataAdapter:
    return StubVehicleDataAdapter()


@pytest.fixture
async def vehicles_client(stub) -> AsyncClient:
    app = _make_app(adapter_override=stub)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# StubVehicleDataAdapter — direct unit tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_stub_lookup_by_plate(stub):
    result = await stub.lookup(plate="123ABC", vin=None)
    assert result is not None
    assert result.make
    assert result.model
    assert 2010 <= result.year <= 2022
    assert isinstance(result.fuel, FuelType)
    assert isinstance(result.body, BodyType)
    assert isinstance(result.transmission, Transmission)


@pytest.mark.anyio
async def test_stub_lookup_by_vin(stub):
    result = await stub.lookup(plate=None, vin="WBA3A5G5XEF595848")
    assert result is not None
    assert result.engine_cc is not None
    assert result.power_kw is not None


@pytest.mark.anyio
async def test_stub_lookup_deterministic(stub):
    r1 = await stub.lookup(plate=None, vin="TESTVIN001")
    r2 = await stub.lookup(plate=None, vin="TESTVIN001")
    assert r1 == r2


@pytest.mark.anyio
async def test_stub_history_returns_two_events(stub):
    records = await stub.history("TESTVIN001")
    assert len(records) == 2
    types = {r.event_type for r in records}
    assert HistoryEventType.REGISTRATION in types


@pytest.mark.anyio
async def test_stub_history_no_rollback(stub):
    """Normal stub history has ascending odometer — rollback should be False."""
    records = await stub.history("TESTVIN001")
    assert detect_rollback(records) is False


@pytest.mark.anyio
async def test_rollback_detection_with_synthetic_records():
    """detect_rollback returns True when odometer decreases in time order."""
    t = lambda y, m, d: datetime(y, m, d, tzinfo=UTC)  # noqa: E731
    records = [
        VehicleHistoryRecord(
            event_type=HistoryEventType.ODOMETER,
            occurred_at=t(2020, 1, 1),
            odometer_km=100000,
            source="test",
        ),
        VehicleHistoryRecord(
            event_type=HistoryEventType.ODOMETER,
            occurred_at=t(2021, 1, 1),
            odometer_km=80000,  # rollback!
            source="test",
        ),
    ]
    assert detect_rollback(records) is True


@pytest.mark.anyio
async def test_stub_lookup_no_args_raises(stub):
    with pytest.raises(ValueError):
        await stub.lookup(plate=None, vin=None)


# ---------------------------------------------------------------------------
# Vehicles router — HTTP tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_lookup_by_plate_200(vehicles_client):
    resp = await vehicles_client.get("/v1/vehicles/lookup", params={"plate": "123ABC"})
    assert resp.status_code == 200
    data = resp.json()
    assert "make" in data
    assert "year" in data
    assert "fuel" in data


@pytest.mark.anyio
async def test_lookup_by_vin_200(vehicles_client):
    resp = await vehicles_client.get(
        "/v1/vehicles/lookup", params={"vin": "WBA3A5G5XEF595848"}
    )
    assert resp.status_code == 200
    assert resp.json()["make"]


@pytest.mark.anyio
async def test_lookup_missing_params_400(vehicles_client):
    resp = await vehicles_client.get("/v1/vehicles/lookup")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_history_200(vehicles_client):
    resp = await vehicles_client.get("/v1/vehicles/TESTVIN001/history")
    assert resp.status_code == 200
    data = resp.json()
    assert "records" in data
    assert "rollback_suspected" in data
    assert len(data["records"]) == 2
    assert data["rollback_suspected"] is False


@pytest.mark.anyio
async def test_history_rollback_suspected_true():
    """Override the adapter to emit descending odometer and assert flag is True."""

    class RollbackStub:
        async def lookup(self, plate, vin):
            return None

        async def history(self, vin):
            t = lambda y: datetime(y, 6, 1, tzinfo=UTC)  # noqa: E731
            return [
                VehicleHistoryRecord(
                    event_type=HistoryEventType.ODOMETER,
                    occurred_at=t(2018),
                    odometer_km=120000,
                    source="test",
                ),
                VehicleHistoryRecord(
                    event_type=HistoryEventType.ODOMETER,
                    occurred_at=t(2020),
                    odometer_km=95000,
                    source="test",
                ),
            ]

    app = _make_app(adapter_override=RollbackStub())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/vehicles/ANYVIN/history")
    assert resp.status_code == 200
    assert resp.json()["rollback_suspected"] is True
