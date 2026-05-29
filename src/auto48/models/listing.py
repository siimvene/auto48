"""Listing aggregate: a vehicle offered for sale by a seller."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto48.db import Base

if TYPE_CHECKING:
    from auto48.models.photo import Photo
    from auto48.models.vehicle import Vehicle


class ListingStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SOLD = "sold"
    EXPIRED = "expired"


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("seller_profiles.id"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    # Money stored as integer EUR cents (project invariant).
    price_eur_cents: Mapped[int] = mapped_column(BigInteger, index=True)
    mileage_km: Mapped[int | None] = mapped_column(Integer, default=None)
    location_county: Mapped[str | None] = mapped_column(String(64), default=None)
    # Plain floats now; PostGIS Point later.
    lat: Mapped[float | None] = mapped_column(Float, default=None)
    lon: Mapped[float | None] = mapped_column(Float, default=None)
    status: Mapped[ListingStatus] = mapped_column(
        Enum(
            ListingStatus,
            name="listing_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=ListingStatus.DRAFT,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vehicle: Mapped[Vehicle] = relationship(back_populates="listings")
    photos: Mapped[list[Photo]] = relationship(
        back_populates="listing", order_by="Photo.position"
    )
