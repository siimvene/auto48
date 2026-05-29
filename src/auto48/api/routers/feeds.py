"""Dealer feed endpoints.

POST   /v1/dealer/feeds               — register a new feed (DEALER only)
GET    /v1/dealer/feeds               — list caller's feeds
POST   /v1/dealer/feeds/{id}/ingest   — trigger synchronous ingest; enqueue to arq best-effort
GET    /v1/dealer/feeds/{id}/runs     — list IngestRun history for a feed

RFC 7807 errors via HTTPException.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from auto48.api.dependencies import CurrentUser, DbSession
from auto48.models.dealer_feed import DealerFeed, IngestRun
from auto48.models.feed_schemas import (
    FeedCreate,
    FeedListResponse,
    FeedResponse,
    IngestTriggerResponse,
    RunListResponse,
)
from auto48.models.seller import SellerProfile, SellerType
from auto48.ports.feed import FeedPort

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/dealer/feeds", tags=["feeds"])


# ---------------------------------------------------------------------------
# Adapter dependency (override in tests via app.dependency_overrides)
# ---------------------------------------------------------------------------


def _get_fetch_adapter() -> FeedPort:
    """Return the default live HTTP fetch adapter."""
    from auto48.adapters.feed.http_fetch import HttpFeedAdapter

    return HttpFeedAdapter()


FetchAdapter = Annotated[FeedPort, Depends(_get_fetch_adapter)]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _get_dealer_profile(db: DbSession, current_user: CurrentUser) -> SellerProfile:
    """Load the SellerProfile for *current_user*; 403 if absent or not DEALER."""
    profile = await db.scalar(
        select(SellerProfile).where(SellerProfile.user_id == current_user.id)
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No seller profile found for this user",
        )
    if profile.type != SellerType.DEALER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only DEALER accounts can manage feeds",
        )
    return profile


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=FeedResponse, status_code=status.HTTP_201_CREATED)
async def create_feed(
    payload: FeedCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> FeedResponse:
    """Register a new dealer inventory feed."""
    profile = await _get_dealer_profile(db, current_user)

    feed = DealerFeed(
        seller_id=profile.id,
        url=str(payload.url),
        format=payload.format,
    )
    db.add(feed)
    await db.flush()
    await db.refresh(feed)
    return FeedResponse.model_validate(feed)


@router.get("", response_model=FeedListResponse)
async def list_feeds(
    db: DbSession,
    current_user: CurrentUser,
) -> FeedListResponse:
    """List all feeds for the calling dealer."""
    profile = await _get_dealer_profile(db, current_user)

    rows = (
        await db.scalars(
            select(DealerFeed)
            .where(DealerFeed.seller_id == profile.id)
            .order_by(DealerFeed.created_at.desc())
        )
    ).all()
    total = await db.scalar(
        select(func.count()).where(DealerFeed.seller_id == profile.id)
    )
    return FeedListResponse(
        items=[FeedResponse.model_validate(r) for r in rows],
        total=total or 0,
    )


@router.post(
    "/{feed_id}/ingest",
    response_model=IngestTriggerResponse,
    status_code=status.HTTP_200_OK,
)
async def trigger_ingest(
    feed_id: int,
    db: DbSession,
    current_user: CurrentUser,
    fetch_adapter: FetchAdapter,
) -> IngestTriggerResponse:
    """Run ingest synchronously and enqueue an arq task best-effort."""
    profile = await _get_dealer_profile(db, current_user)

    # Verify the feed belongs to this dealer
    feed = await db.get(DealerFeed, feed_id)
    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )
    if feed.seller_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Feed does not belong to your account",
        )

    from auto48.services.ingest import ingest_feed

    run = await ingest_feed(db, feed_id, fetch_adapter)

    # Best-effort enqueue to arq (Redis may be unavailable in dev/tests)
    await _enqueue_ingest(feed_id)

    return IngestTriggerResponse(
        run_id=run.id,
        status=run.status,
        created_count=run.created_count,
        updated_count=run.updated_count,
        error_count=run.error_count,
    )


@router.get("/{feed_id}/runs", response_model=RunListResponse)
async def list_runs(
    feed_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> RunListResponse:
    """List IngestRun history for a feed owned by the calling dealer."""
    profile = await _get_dealer_profile(db, current_user)

    feed = await db.get(DealerFeed, feed_id)
    if feed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feed {feed_id} not found",
        )
    if feed.seller_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Feed does not belong to your account",
        )

    rows = (
        await db.scalars(
            select(IngestRun)
            .where(IngestRun.feed_id == feed_id)
            .order_by(IngestRun.started_at.desc())
        )
    ).all()
    total = await db.scalar(
        select(func.count()).where(IngestRun.feed_id == feed_id)
    )
    from auto48.models.feed_schemas import IngestRunResponse

    return RunListResponse(
        items=[IngestRunResponse.model_validate(r) for r in rows],
        total=total or 0,
    )


# ---------------------------------------------------------------------------
# arq enqueueing (graceful degradation when Redis is down)
# ---------------------------------------------------------------------------


async def _enqueue_ingest(feed_id: int) -> None:
    """Enqueue a run_feed_ingest job; silently continue if Redis is unavailable."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        from auto48.config import get_settings

        settings = get_settings()
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await redis.enqueue_job("run_feed_ingest", feed_id)
        await redis.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Could not enqueue run_feed_ingest for feed %d (Redis unavailable?): %s",
            feed_id,
            exc,
        )
