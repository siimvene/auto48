"""Billing router: dealer subscriptions and listing promotions.

POST /v1/billing/subscribe              — dealer subscribes to a plan
GET  /v1/billing/subscription           — current dealer's active subscription
POST /v1/listings/{listing_id}/promotions — listing owner adds a promotion
GET  /v1/listings/{listing_id}/promotions — list promotions for a listing

RFC 7807 errors; thin handlers, all logic delegated to services.billing.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from auto48.adapters.payment import get_payment_adapter
from auto48.api.dependencies import CurrentUser, DbSession
from auto48.config import get_settings
from auto48.models.billing import Subscription
from auto48.models.billing_schemas import (
    CreatePromotionRequest,
    PromotionResponse,
    SubscribeRequest,
    SubscriptionResponse,
)
from auto48.models.listing import Listing
from auto48.models.seller import SellerProfile, SellerType
from auto48.ports.payment import PaymentPort
from auto48.services.billing import (
    create_promotion,
    list_promotions,
    subscribe,
)

router = APIRouter(prefix="/v1", tags=["billing"])


def _get_payment_adapter() -> PaymentPort:
    return get_payment_adapter(get_settings())


PaymentAdapter = Annotated[PaymentPort, Depends(_get_payment_adapter)]


# ---------------------------------------------------------------------------
# Subscription endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/billing/subscribe",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def billing_subscribe(
    payload: SubscribeRequest,
    current_user: CurrentUser,
    db: DbSession,
    adapter: PaymentAdapter,
) -> SubscriptionResponse:
    """Subscribe the current dealer to a plan.

    Raises 403 if the caller's seller profile is not of type DEALER.
    Raises 404 if no seller profile is found for the current user.
    """
    seller = await db.scalar(
        select(SellerProfile).where(SellerProfile.user_id == current_user.id)
    )
    if seller is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No seller profile found for the current user.",
        )
    if seller.type is not SellerType.DEALER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only DEALER sellers can subscribe to plans.",
        )

    sub = await subscribe(db, seller, payload.plan, adapter)
    return SubscriptionResponse.model_validate(sub)


@router.get("/billing/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: CurrentUser,
    db: DbSession,
) -> SubscriptionResponse:
    """Return the most recent subscription for the current dealer.

    Raises 404 if the user has no seller profile or no subscriptions.
    """
    seller = await db.scalar(
        select(SellerProfile).where(SellerProfile.user_id == current_user.id)
    )
    if seller is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No seller profile found for the current user.",
        )

    sub = await db.scalar(
        select(Subscription)
        .where(Subscription.seller_id == seller.id)
        .order_by(Subscription.created_at.desc())
    )
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found for the current user.",
        )
    return SubscriptionResponse.model_validate(sub)


# ---------------------------------------------------------------------------
# Promotion endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/listings/{listing_id}/promotions",
    response_model=PromotionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_listing_promotion(
    listing_id: int,
    payload: CreatePromotionRequest,
    current_user: CurrentUser,
    db: DbSession,
    adapter: PaymentAdapter,
) -> PromotionResponse:
    """Promote a listing.

    Raises 404 if the listing does not exist.
    Raises 403 if the current user does not own the listing's seller profile.
    """
    listing = await db.scalar(select(Listing).where(Listing.id == listing_id))
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found.",
        )

    seller = await db.scalar(
        select(SellerProfile).where(SellerProfile.id == listing.seller_id)
    )
    if seller is None or seller.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this listing.",
        )

    promo = await create_promotion(db, listing, payload.kind, payload.duration_days, adapter)
    return PromotionResponse.model_validate(promo)


@router.get(
    "/listings/{listing_id}/promotions",
    response_model=list[PromotionResponse],
)
async def get_listing_promotions(
    listing_id: int,
    db: DbSession,
) -> list[PromotionResponse]:
    """Return all promotions for a listing.

    Raises 404 if the listing does not exist.
    """
    listing = await db.scalar(select(Listing).where(Listing.id == listing_id))
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found.",
        )

    promos = await list_promotions(db, listing_id)
    return [PromotionResponse.model_validate(p) for p in promos]
