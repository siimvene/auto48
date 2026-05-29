"""CommercialVehicleDataAdapter: skeleton for carVertical / autoDNA integration.

carVertical/autoDNA adapter — wire real endpoint + caching in Phase 1b;
cache per-VIN, fetch on listing create not per view.

Phase 1b checklist:
- Replace _ENDPOINT_LOOKUP / _ENDPOINT_HISTORY constants with real carVertical paths.
- Implement _parse_lookup / _parse_history from the vendor's documented JSON shape.
- Add per-VIN Redis / in-process cache: key = f"vdata:{vin}", TTL = 24 h.
- Trigger lookup at listing-create time (services/listing.py) — not on each GET.
"""

from __future__ import annotations

import httpx

from auto48.ports.vehicle_data import VehicleData, VehicleHistoryRecord

# Placeholder endpoint paths — replace when vendor docs are confirmed.
_ENDPOINT_LOOKUP = "/v1/decode"
_ENDPOINT_HISTORY = "/v1/history"


class CommercialVehicleDataAdapter:
    """Thin HTTP client for carVertical / autoDNA (or any compatible REST API).

    Requires AUTO48_VEHICLE_DATA_API_URL and AUTO48_VEHICLE_DATA_API_KEY to be set;
    returns None / empty list and raises NotImplementedError when unconfigured.
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._configured = bool(base_url and api_key)

    # ------------------------------------------------------------------
    # VehicleDataPort implementation
    # ------------------------------------------------------------------

    async def lookup(
        self,
        plate: str | None,
        vin: str | None,
    ) -> VehicleData | None:
        """Return decoded VehicleData from the commercial API.

        Not implemented — wire real endpoint in Phase 1b.
        """
        if not self._configured:
            return None
        raise NotImplementedError(
            "CommercialVehicleDataAdapter.lookup — wire real endpoint in Phase 1b"
        )

    async def history(self, vin: str) -> list[VehicleHistoryRecord]:
        """Return history timeline from the commercial API.

        Not implemented — wire real endpoint in Phase 1b.
        """
        if not self._configured:
            return []
        raise NotImplementedError(
            "CommercialVehicleDataAdapter.history — wire real endpoint in Phase 1b"
        )

    # ------------------------------------------------------------------
    # Private helpers (stubs for Phase 1b)
    # ------------------------------------------------------------------

    def _make_client(self) -> httpx.AsyncClient:
        """Construct an authenticated httpx client."""
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=10.0,
        )

    @staticmethod
    def _parse_lookup(payload: dict) -> VehicleData:
        """Map vendor JSON → VehicleData.

        Expected shape (carVertical/autoDNA v1, to be confirmed):
        {
            "make": "Toyota", "model": "Corolla", "year": 2019,
            "fuel_type": "petrol", "body_type": "sedan",
            "transmission": "manual", "drivetrain": "fwd",
            "engine_cc": 1600, "power_kw": 97,
            "color": "White", "first_registered": "2019-03-15"
        }
        """
        raise NotImplementedError("_parse_lookup — implement in Phase 1b")

    @staticmethod
    def _parse_history(payload: list[dict]) -> list[VehicleHistoryRecord]:
        """Map vendor JSON array → list[VehicleHistoryRecord].

        Expected shape (each item):
        {
            "event_type": "odometer", "occurred_at": "2021-06-01T12:00:00Z",
            "odometer_km": 85000, "source": "carVertical", "detail": {}
        }
        """
        raise NotImplementedError("_parse_history — implement in Phase 1b")
