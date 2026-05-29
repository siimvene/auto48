"""TestDriveBooking aggregate: buyer requests a test drive, seller confirms/declines."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto48.db import Base

if TYPE_CHECKING:
    from auto48.models.listing import Listing
    from auto48.models.user import User


class TestDriveStatus(enum.Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class TestDriveBooking(Base):
    __tablename__ = "test_drive_bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    slot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[TestDriveStatus] = mapped_column(
        Enum(
            TestDriveStatus,
            name="test_drive_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=TestDriveStatus.REQUESTED,
    )
    note: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    listing: Mapped[Listing] = relationship()
    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
