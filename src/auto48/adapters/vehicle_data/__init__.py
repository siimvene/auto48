"""Vehicle-data adapter factory.

Returns CommercialVehicleDataAdapter when both API URL and key are configured,
otherwise falls back to StubVehicleDataAdapter for offline dev and CI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from auto48.config import Settings
    from auto48.ports.vehicle_data import VehicleDataPort


def get_vehicle_data_adapter(settings: Settings) -> VehicleDataPort:
    """Return the appropriate VehicleDataPort implementation.

    Commercial adapter is returned only when both vehicle_data_api_url and
    vehicle_data_api_key are non-empty; otherwise the deterministic stub is used.
    """
    from auto48.adapters.vehicle_data.commercial import CommercialVehicleDataAdapter
    from auto48.adapters.vehicle_data.stub import StubVehicleDataAdapter

    if settings.vehicle_data_api_url and settings.vehicle_data_api_key:
        return CommercialVehicleDataAdapter(
            base_url=settings.vehicle_data_api_url,
            api_key=settings.vehicle_data_api_key,
        )
    return StubVehicleDataAdapter()
