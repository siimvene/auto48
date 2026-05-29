"""Tests for the stolen-vehicle check port: StubAdapter (direct) + router (HTTP)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auto48.adapters.stolen.stub import StubStolenVehicleAdapter
from auto48.api.routers.stolen import _get_adapter, router

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DENYLIST_VIN = "WBA3A5G5XEF000001"  # in the stub hardcoded denylist
_SUFFIX_VIN = "AASTOLEN"             # ends with "STOLEN", passes 8-17 char rule
_CLEAN_VIN = "TESTVIN001"            # normal VIN, not flagged
_INVALID_VIN = "!BAD!"               # fails charset validation → 400


def _make_app(adapter_override=None) -> FastAPI:
    """Mount only the stolen router; optionally inject a custom adapter."""
    app = FastAPI()
    app.include_router(router)
    if adapter_override is not None:
        app.dependency_overrides[_get_adapter] = lambda: adapter_override
    return app


@pytest.fixture
def stub() -> StubStolenVehicleAdapter:
    return StubStolenVehicleAdapter()


@pytest.fixture
async def stolen_client(stub) -> AsyncClient:
    app = _make_app(adapter_override=stub)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# StubStolenVehicleAdapter — direct unit tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_stub_denylist_vin_flagged(stub):
    """A VIN in the hardcoded denylist must be flagged."""
    result = await stub.check(_DENYLIST_VIN)
    assert result.flagged is True
    assert result.vin == _DENYLIST_VIN
    assert result.source == "stub"
    assert result.detail is not None


@pytest.mark.anyio
async def test_stub_suffix_vin_flagged(stub):
    """A VIN ending in 'STOLEN' must be flagged by the suffix rule."""
    result = await stub.check(_SUFFIX_VIN)
    assert result.flagged is True
    assert result.source == "stub"
    assert result.detail is not None


@pytest.mark.anyio
async def test_stub_clean_vin_not_flagged(stub):
    """A normal VIN that is neither in the denylist nor matches the suffix rule."""
    result = await stub.check(_CLEAN_VIN)
    assert result.flagged is False
    assert result.source == "stub"
    assert result.detail is None


@pytest.mark.anyio
async def test_stub_check_deterministic(stub):
    """Same VIN must always return the same result."""
    r1 = await stub.check(_CLEAN_VIN)
    r2 = await stub.check(_CLEAN_VIN)
    assert r1 == r2


@pytest.mark.anyio
async def test_stub_normalises_to_uppercase(stub):
    """Lowercase input must be normalised and flagged correctly."""
    result = await stub.check(_SUFFIX_VIN.lower())
    assert result.flagged is True
    assert result.vin == _SUFFIX_VIN  # normalised to uppercase


# ---------------------------------------------------------------------------
# Stolen router — HTTP tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_endpoint_flagged_denylist(stolen_client):
    resp = await stolen_client.get(f"/v1/vehicles/{_DENYLIST_VIN}/stolen-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["flagged"] is True
    assert data["source"] == "stub"
    assert data["vin"] == _DENYLIST_VIN


@pytest.mark.anyio
async def test_endpoint_flagged_suffix(stolen_client):
    resp = await stolen_client.get(f"/v1/vehicles/{_SUFFIX_VIN}/stolen-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["flagged"] is True
    assert data["source"] == "stub"


@pytest.mark.anyio
async def test_endpoint_clean_vin(stolen_client):
    resp = await stolen_client.get(f"/v1/vehicles/{_CLEAN_VIN}/stolen-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["flagged"] is False
    assert data["source"] == "stub"
    assert data["detail"] is None


@pytest.mark.anyio
async def test_endpoint_invalid_vin_400():
    """An obviously invalid VIN must return 400 without touching the adapter."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/v1/vehicles/{_INVALID_VIN}/stolen-check")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_endpoint_too_short_vin_400():
    """A VIN that is too short (< 8 chars) must return 400."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/vehicles/TOOSHRT/stolen-check")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_endpoint_response_schema_fields(stolen_client):
    """Response must contain all required schema fields."""
    resp = await stolen_client.get(f"/v1/vehicles/{_CLEAN_VIN}/stolen-check")
    assert resp.status_code == 200
    data = resp.json()
    assert "vin" in data
    assert "flagged" in data
    assert "source" in data
    assert "detail" in data
