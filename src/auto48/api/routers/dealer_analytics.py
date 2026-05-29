"""Dealer analytics router.

GET /v1/dealer/analytics — aggregate performance dashboard for the authenticated DEALER.

Errors:
  404 — no SellerProfile for the authenticated user
  403 — SellerProfile exists but is not type DEALER
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from auto48.api.dependencies import CurrentUser, DbSession
from auto48.models.analytics_schemas import (
    BodyBreakdownItemSchema,
    DealerAnalyticsSchema,
    FeedHealthSchema,
    InventoryValueSchema,
    ListingCountsSchema,
    MakeBreakdownItemSchema,
    TestDriveByStatusSchema,
)
from auto48.models.seller import SellerProfile, SellerType
from auto48.services.dealer_analytics import compute_dealer_analytics

router = APIRouter(tags=["dealer-analytics"])


@router.get("/v1/dealer/analytics", response_model=DealerAnalyticsSchema)
async def get_dealer_analytics(
    db: DbSession,
    current_user: CurrentUser,
) -> DealerAnalyticsSchema:
    """Return the aggregate performance dashboard for the authenticated DEALER."""
    profile = await db.scalar(
        select(SellerProfile).where(SellerProfile.user_id == current_user.id)
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No seller profile found for this user",
        )
    if profile.type is not SellerType.DEALER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only DEALER accounts can access dealer analytics",
        )

    analytics = await compute_dealer_analytics(db, seller_profile_id=profile.id)

    return DealerAnalyticsSchema(
        listing_counts=ListingCountsSchema(
            total=analytics.listing_counts.total,
            active=analytics.listing_counts.active,
            sold=analytics.listing_counts.sold,
            draft=analytics.listing_counts.draft,
            expired=analytics.listing_counts.expired,
        ),
        inventory_value=InventoryValueSchema(
            total_eur_cents=analytics.inventory_value.total_eur_cents,
            avg_eur_cents=analytics.inventory_value.avg_eur_cents,
        ),
        top_makes=[
            MakeBreakdownItemSchema(
                make=m.make,
                count=m.count,
                avg_price_eur_cents=m.avg_price_eur_cents,
            )
            for m in analytics.top_makes
        ],
        top_bodies=[
            BodyBreakdownItemSchema(
                body=b.body,
                count=b.count,
                avg_price_eur_cents=b.avg_price_eur_cents,
            )
            for b in analytics.top_bodies
        ],
        total_leads=analytics.total_leads,
        total_test_drives=analytics.total_test_drives,
        test_drives_by_status=[
            TestDriveByStatusSchema(status=td.status, count=td.count)
            for td in analytics.test_drives_by_status
        ],
        feed_health=[
            FeedHealthSchema(
                feed_id=f.feed_id,
                status=f.status,
                created_count=f.created_count,
                updated_count=f.updated_count,
                error_count=f.error_count,
            )
            for f in analytics.feed_health
        ],
    )
