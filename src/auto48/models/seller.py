"""Seller profile aggregate (private person or dealer)."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from auto48.db import Base


class SellerType(enum.Enum):
    PRIVATE = "PRIVATE"
    DEALER = "DEALER"


class SellerProfile(Base):
    __tablename__ = "seller_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[SellerType] = mapped_column(
        Enum(
            SellerType,
            name="seller_type",
            values_callable=lambda e: [m.value for m in e],
        )
    )
    company_name: Mapped[str | None] = mapped_column(String(255), default=None)
    # verified: set true after eID identity check (Phase 2).
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
