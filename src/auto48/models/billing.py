"""Billing aggregates: dealer subscriptions and listing promotions."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from auto48.db import Base


class SubscriptionPlan(enum.Enum):
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class PromotionKind(enum.Enum):
    BUMP = "bump"
    FEATURED = "featured"
    SPOTLIGHT = "spotlight"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("seller_profiles.id"), index=True, nullable=False
    )
    plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(
            SubscriptionPlan,
            name="subscription_plan",
            values_callable=lambda e: [m.value for m in e],
        )
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(
            SubscriptionStatus,
            name="subscription_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        default=SubscriptionStatus.ACTIVE,
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), default=None, nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id"), index=True, nullable=False
    )
    kind: Mapped[PromotionKind] = mapped_column(
        Enum(
            PromotionKind,
            name="promotion_kind",
            values_callable=lambda e: [m.value for m in e],
        )
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stripe_payment_id: Mapped[str | None] = mapped_column(
        String(255), default=None, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
