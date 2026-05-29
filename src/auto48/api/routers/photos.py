"""Photos resource: multipart upload, listing, and deletion of listing photos.

POST   /v1/listings/{listing_id}/photos  — upload a photo (multipart/form-data)
GET    /v1/listings/{listing_id}/photos  — list photos for a listing
DELETE /v1/photos/{id}                   — delete a single photo

RFC 7807 errors via HTTPException.  arq enqueueing degrades gracefully when
Redis is unavailable so the endpoint works in dev/tests without a broker.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import func, select

from auto48.adapters.media import get_media_adapter
from auto48.api.dependencies import CurrentUser, DbSession
from auto48.config import get_settings
from auto48.models.listing import Listing
from auto48.models.photo import Photo
from auto48.models.photo_schemas import PhotoResponse
from auto48.models.seller import SellerProfile
from auto48.models.user import User
from auto48.ports.media import MediaPort

logger = logging.getLogger(__name__)

router = APIRouter(tags=["photos"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------


def _media_adapter() -> MediaPort:
    """Return the configured MediaPort adapter (cached per process)."""
    return get_media_adapter(get_settings())


async def _assert_owns_listing(db: DbSession, listing: Listing, user: User) -> None:
    """403 unless `user` owns the seller profile behind `listing`."""
    seller = await db.get(SellerProfile, listing.seller_id)
    if seller is None or seller.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this listing",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/v1/listings/{listing_id}/photos",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_photo(
    listing_id: int,
    file: UploadFile,
    db: DbSession,
    current_user: CurrentUser,
) -> PhotoResponse:
    # 1. Verify listing exists and the caller owns it
    listing = await db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found",
        )
    await _assert_owns_listing(db, listing, current_user)

    # 2. Read file bytes
    data = await file.read()
    content_type = file.content_type or "application/octet-stream"

    # 3. Build a unique storage key
    ext = (file.filename or "").rsplit(".", 1)[-1] if "." in (file.filename or "") else "bin"
    key = f"listings/{listing_id}/{uuid.uuid4().hex}.{ext}"

    # 4. Store via MediaPort
    media = _media_adapter()
    url = await media.put(key, data, content_type)

    # 5. Determine next position
    max_pos = await db.scalar(
        select(func.max(Photo.position)).where(Photo.listing_id == listing_id)
    )
    next_pos = (max_pos or 0) + 1

    # 6. Persist Photo row
    photo = Photo(listing_id=listing_id, url=url, position=next_pos, processed=False)
    db.add(photo)
    await db.flush()
    await db.refresh(photo)

    # 7. Enqueue processing job — degrade gracefully if Redis is unavailable
    await _enqueue_process(photo.id)

    return PhotoResponse.model_validate(photo)


@router.get(
    "/v1/listings/{listing_id}/photos",
    response_model=list[PhotoResponse],
)
async def list_photos(listing_id: int, db: DbSession) -> list[PhotoResponse]:
    listing = await db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found",
        )

    rows = (
        await db.scalars(
            select(Photo)
            .where(Photo.listing_id == listing_id)
            .order_by(Photo.position)
        )
    ).all()
    return [PhotoResponse.model_validate(r) for r in rows]


@router.delete("/v1/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(photo_id: int, db: DbSession, current_user: CurrentUser) -> None:
    photo = await db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Photo {photo_id} not found",
        )
    listing = await db.get(Listing, photo.listing_id)
    if listing is not None:
        await _assert_owns_listing(db, listing, current_user)

    # Remove from object store
    try:
        media = _media_adapter()
        # Derive key from URL (best-effort; stub and S3 both use trailing path)
        key = photo.url.split("/objects/", 1)[-1] if "/objects/" in photo.url else photo.url
        await media.delete(key)
    except Exception:
        logger.warning("Failed to delete object for photo %d; removing DB row anyway", photo_id)

    await db.delete(photo)


# ---------------------------------------------------------------------------
# arq job enqueueing (non-blocking, graceful degradation)
# ---------------------------------------------------------------------------


async def _enqueue_process(photo_id: int) -> None:
    """Enqueue a process_image job; silently continue if Redis is unavailable."""
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        settings = get_settings()
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        await redis.enqueue_job("process_image", photo_id)
        await redis.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Could not enqueue process_image for photo %d (Redis unavailable?): %s",
            photo_id,
            exc,
        )
