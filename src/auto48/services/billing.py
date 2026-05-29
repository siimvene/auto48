"""Billing service layer: subscriptions and listing promotions.

All DB I/O is async; callers supply the session and adapter so this layer stays
unit-testable without the FastAPI DI machinery.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auto48.models.billing import (
    Promotion,
    PromotionKind,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from auto48.models.listing import Listing
from auto48.models.seller import SellerProfile, SellerType
from auto48.ports.payment import PaymentPort

# Price map for promotion kinds (EUR cents).
_PROMOTION_PRICE_CENTS: dict[PromotionKind, int] = {
    PromotionKind.BUMP: 500,
    PromotionKind.FEATURED: 1500,
    PromotionKind.SPOTLIGHT: 3000,
}


async def subscribe(
    db: AsyncSession,
    seller_profile: SellerProfile,
    plan: SubscriptionPlan,
    adapter: PaymentPort,
) -> Subscription:
    """Create a new Subscription for a DEALER seller profile.

    Raises:
        ValueError: if the seller is not a DEALER.
    """
    if seller_profile.type is not SellerType.DEALER:
        raise ValueError("Only DEALER sellers can subscribe to plans.")

    result = await adapter.create_subscription(
        customer_ref=str(seller_profile.id),
        plan=plan.value,
    )

    subscription = Subscription(
        seller_id=seller_profile.id,
        plan=plan,
        status=SubscriptionStatus.ACTIVE,
        stripe_subscription_id=result.provider_id,
        current_period_end=None,
    )
    db.add(subscription)
    await db.flush()
    return subscription


async def create_promotion(
    db: AsyncSession,
    listing: Listing,
    kind: PromotionKind,
    duration_days: int,
    adapter: PaymentPort,
) -> Promotion:
    """Create a Promotion for a listing and record the payment.

    Args:
        db: Active async session.
        listing: The listing to promote.
        kind: Promotion type.
        duration_days: How long the promotion runs.
        adapter: Payment adapter to charge through.

    Returns:
        Persisted Promotion ORM object.
    """
    amount_cents = _PROMOTION_PRICE_CENTS[kind]
    result = await adapter.create_promotion_charge(
        listing_ref=str(listing.id),
        kind=kind.value,
        amount_cents=amount_cents,
    )

    now = datetime.now(tz=UTC)
    promotion = Promotion(
        listing_id=listing.id,
        kind=kind,
        starts_at=now,
        ends_at=now + timedelta(days=duration_days),
        stripe_payment_id=result.provider_id,
    )
    db.add(promotion)
    await db.flush()
    return promotion


async def list_subscriptions(
    db: AsyncSession,
    seller_id: int,
) -> list[Subscription]:
    """Return all subscriptions for a seller profile, newest first."""
    rows = await db.scalars(
        select(Subscription)
        .where(Subscription.seller_id == seller_id)
        .order_by(Subscription.created_at.desc())
    )
    return list(rows.all())


async def list_promotions(
    db: AsyncSession,
    listing_id: int,
) -> list[Promotion]:
    """Return all promotions for a listing, newest first."""
    rows = await db.scalars(
        select(Promotion)
        .where(Promotion.listing_id == listing_id)
        .order_by(Promotion.created_at.desc())
    )
    return list(rows.all())
