"""Vehicle aggregate: the physical car a listing references."""

import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto48.db import Base


class FuelType(enum.Enum):
    PETROL = "petrol"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    PLUGIN_HYBRID = "plugin_hybrid"
    ELECTRIC = "electric"
    LPG = "lpg"
    CNG = "cng"
    OTHER = "other"


class BodyType(enum.Enum):
    SEDAN = "sedan"
    HATCHBACK = "hatchback"
    WAGON = "wagon"
    SUV = "suv"
    COUPE = "coupe"
    CONVERTIBLE = "convertible"
    MINIVAN = "minivan"
    PICKUP = "pickup"
    VAN = "van"
    OTHER = "other"


class Transmission(enum.Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SEMI_AUTOMATIC = "semi_automatic"
    CVT = "cvt"


class Drivetrain(enum.Enum):
    FWD = "fwd"
    RWD = "rwd"
    AWD = "awd"


def _enum_values(e: type[enum.Enum]) -> list[str]:
    return [m.value for m in e]


class Vehicle(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    vin: Mapped[str | None] = mapped_column(String(32), index=True, default=None)
    plate: Mapped[str | None] = mapped_column(String(16), index=True, default=None)
    make: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(64), index=True)
    variant: Mapped[str | None] = mapped_column(String(128), default=None)
    year: Mapped[int] = mapped_column(Integer)
    fuel: Mapped[FuelType] = mapped_column(
        Enum(FuelType, name="fuel_type", values_callable=_enum_values)
    )
    body: Mapped[BodyType] = mapped_column(
        Enum(BodyType, name="body_type", values_callable=_enum_values)
    )
    transmission: Mapped[Transmission] = mapped_column(
        Enum(Transmission, name="transmission", values_callable=_enum_values)
    )
    drivetrain: Mapped[Drivetrain | None] = mapped_column(
        Enum(Drivetrain, name="drivetrain", values_callable=_enum_values), default=None
    )
    # JSON (not JSONB) for sqlite compatibility; Postgres maps it to JSONB-capable JSON.
    specs: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    listings: Mapped[list["Listing"]] = relationship(back_populates="vehicle")  # noqa: F821
