"""Deposit aggregate: buyer escrow held via payment provider until release/refund."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auto48.db import Base

if TYPE_CHECKING:
    from auto48.models.listing import Listing
    from auto48.models.user import User


class DepositStatus(enum.Enum):
    HELD = "held"
    RELEASED = "released"
    REFUNDED = "refunded"
    FAILED = "failed"


class Deposit(Base):
    __tablename__ = "deposits"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Money stored as integer EUR cents (project invariant).
    amount_eur_cents: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[DepositStatus] = mapped_column(
        Enum(
            DepositStatus,
            name="deposit_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=DepositStatus.HELD,
    )
    provider_ref: Mapped[str | None] = mapped_column(String(255), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    listing: Mapped[Listing] = relationship()
    buyer: Mapped[User] = relationship()
