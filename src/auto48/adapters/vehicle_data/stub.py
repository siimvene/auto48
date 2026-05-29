"""StubVehicleDataAdapter: deterministic offline adapter for dev and tests.

Data is derived from the plate/VIN string so results are stable across runs.
Two synthetic history events are always returned, with a believable monotonic
odometer progression (no rollback on normal input).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime

from auto48.models.history import HistoryEventType
from auto48.models.vehicle import BodyType, Drivetrain, FuelType, Transmission
from auto48.ports.vehicle_data import VehicleData, VehicleHistoryRecord

_MAKES = ["Toyota", "Volkswagen", "Ford", "BMW", "Renault", "Skoda", "Audi", "Hyundai"]
_MODELS = ["Corolla", "Golf", "Focus", "3 Series", "Megane", "Octavia", "A4", "i30"]
_COLORS = ["White", "Black", "Silver", "Blue", "Red", "Grey"]
_BODIES = list(BodyType)
_FUELS = [FuelType.PETROL, FuelType.DIESEL, FuelType.HYBRID, FuelType.ELECTRIC]
_TRANSMISSIONS = [Transmission.MANUAL, Transmission.AUTOMATIC]
_DRIVETRAINS = [Drivetrain.FWD, Drivetrain.RWD, Drivetrain.AWD]


def _hash_index(key: str, modulus: int) -> int:
    digest = int(hashlib.md5(key.encode(), usedforsecurity=False).hexdigest(), 16)
    return digest % modulus


class StubVehicleDataAdapter:
    """Deterministic fake adapter — no network calls, safe for offline dev and CI."""

    async def lookup(
        self,
        plate: str | None,
        vin: str | None,
    ) -> VehicleData | None:
        seed = (vin or plate or "").upper().strip()
        if not seed:
            raise ValueError("Either plate or vin must be provided")

        i = _hash_index(seed, len(_MAKES))
        make = _MAKES[i]
        model = _MODELS[i]
        year = 2010 + _hash_index(seed + "year", 13)
        fuel = _FUELS[_hash_index(seed + "fuel", len(_FUELS))]
        body = _BODIES[_hash_index(seed + "body", len(_BODIES))]
        transmission = _TRANSMISSIONS[_hash_index(seed + "tx", len(_TRANSMISSIONS))]
        drivetrain = _DRIVETRAINS[_hash_index(seed + "dr", len(_DRIVETRAINS))]
        engine_cc = 1000 + _hash_index(seed + "cc", 31) * 100
        power_kw = 50 + _hash_index(seed + "kw", 151)
        color = _COLORS[_hash_index(seed + "color", len(_COLORS))]
        reg_day = 1 + _hash_index(seed + "day", 28)
        reg_month = 1 + _hash_index(seed + "month", 12)
        first_registered = date(year, reg_month, reg_day)

        return VehicleData(
            make=make,
            model=model,
            year=year,
            fuel=fuel,
            body=body,
            transmission=transmission,
            variant=f"{engine_cc // 1000}.{(engine_cc % 1000) // 100}",
            drivetrain=drivetrain,
            engine_cc=engine_cc,
            power_kw=power_kw,
            color=color,
            first_registered=first_registered,
        )

    async def history(self, vin: str) -> list[VehicleHistoryRecord]:
        seed = vin.upper().strip()
        base_odo = 10000 + _hash_index(seed + "odo", 91) * 1000

        return [
            VehicleHistoryRecord(
                event_type=HistoryEventType.REGISTRATION,
                occurred_at=datetime(
                    2015 + _hash_index(seed + "ry", 8),
                    1 + _hash_index(seed + "rm", 12),
                    1 + _hash_index(seed + "rd", 28),
                    tzinfo=UTC,
                ),
                odometer_km=base_odo,
                source="stub",
                detail={"country": "EE"},
            ),
            VehicleHistoryRecord(
                event_type=HistoryEventType.INSPECTION,
                occurred_at=datetime(
                    2020 + _hash_index(seed + "iy", 4),
                    1 + _hash_index(seed + "im", 12),
                    1 + _hash_index(seed + "id", 28),
                    tzinfo=UTC,
                ),
                odometer_km=base_odo + 50000 + _hash_index(seed + "delta", 50001),
                source="stub",
                detail={"result": "passed"},
            ),
        ]
