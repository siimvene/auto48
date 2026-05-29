"""Vehicle history timeline: append-only events; basis for the trust badge."""

import enum
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from auto48.db import Base


@runtime_checkable
class OdometerReading(Protocol):
    """Structural protocol satisfied by VehicleHistoryEvent and VehicleHistoryRecord."""

    occurred_at: datetime
    odometer_km: int | None


class HistoryEventType(enum.Enum):
    REGISTRATION = "registration"
    ODOMETER = "odometer"
    INSPECTION = "inspection"
    OWNER_CHANGE = "owner_change"
    DAMAGE = "damage"
    IMPORT = "import"


class VehicleHistoryEvent(Base):
    """Append-only; ordered by occurred_at to form the trust timeline."""

    __tablename__ = "vehicle_history_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    event_type: Mapped[HistoryEventType] = mapped_column(
        Enum(
            HistoryEventType,
            name="history_event_type",
            values_callable=lambda e: [m.value for m in e],
        )
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    odometer_km: Mapped[int | None] = mapped_column(Integer, default=None)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    source: Mapped[str] = mapped_column(String(128))


def detect_rollback(events: Iterable[OdometerReading]) -> bool:
    """True if odometer readings, ordered by occurred_at, ever decrease."""
    readings = [
        e.odometer_km
        for e in sorted(events, key=lambda e: e.occurred_at)
        if e.odometer_km is not None
    ]
    return any(later < earlier for earlier, later in zip(readings, readings[1:], strict=False))
