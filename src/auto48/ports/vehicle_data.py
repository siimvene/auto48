"""VehicleDataPort: clean-room protocol separating domain logic from data providers.

Implementations live under adapters/vehicle_data/. The port lets the domain layer
stay unaware of whether data comes from carVertical, autoDNA, a stub, or cache.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from auto48.models.history import HistoryEventType
from auto48.models.vehicle import BodyType, Drivetrain, FuelType, Transmission


@dataclass
class VehicleData:
    """Decoded vehicle specification returned by a lookup."""

    make: str
    model: str
    year: int
    fuel: FuelType
    body: BodyType
    transmission: Transmission
    variant: str | None = None
    drivetrain: Drivetrain | None = None
    engine_cc: int | None = None
    power_kw: int | None = None
    color: str | None = None
    first_registered: date | None = None


@dataclass
class VehicleHistoryRecord:
    """A single event in the vehicle's provenance timeline.

    Attribute names (occurred_at, odometer_km) intentionally match those read
    by auto48.models.history.detect_rollback so records can be passed directly.
    """

    event_type: HistoryEventType
    occurred_at: datetime
    source: str
    odometer_km: int | None = None
    detail: dict[str, Any] | None = None


class VehicleDataPort(Protocol):
    """Async contract for vehicle specification and history providers."""

    async def lookup(
        self,
        plate: str | None,
        vin: str | None,
    ) -> VehicleData | None:
        """Return decoded vehicle data for the given plate or VIN.

        Returns None if the vehicle is not found in the source.
        Raises ValueError if both plate and vin are None.
        """
        ...

    async def history(self, vin: str) -> list[VehicleHistoryRecord]:
        """Return the provenance timeline for the given VIN, ordered ascending."""
        ...
