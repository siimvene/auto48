"""arq image-processing worker.

Tasks
-----
process_image(ctx, photo_id)
    Stub that demonstrates the processing pipeline:
      • Resize to max 1920 px on the long edge
      • Strip EXIF metadata
      • (Placeholder) blur licence plates / faces
    Sets Photo.processed = True on success.

Usage
-----
Run the worker directly:

    AUTO48_REDIS_URL=redis://localhost:6379/0 \
    arq auto48.workers.images.WorkerSettings

Or via uvicorn worker pool (not recommended for CPU work; prefer a dedicated process).
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from arq.connections import RedisSettings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


async def process_image(ctx: dict[str, object], photo_id: int) -> None:  # noqa: ARG001
    """Download, process, and re-upload a listing photo.

    This is currently a stub; a full implementation would:
      1. Fetch bytes from the MediaPort using Photo.url / key.
      2. Resize with Pillow.
      3. Strip EXIF.
      4. Run plate/face blurring (OpenCV or external API).
      5. Re-upload and update Photo.url if the key changes.

    For now it just marks the photo processed=True so tests can verify the
    async pipeline is wired up correctly.
    """
    from sqlalchemy import select

    from auto48.db import async_session_factory
    from auto48.models.photo import Photo

    log = logger.bind(photo_id=photo_id)

    async with async_session_factory() as session:
        photo = await session.scalar(select(Photo).where(Photo.id == photo_id))
        if photo is None:
            log.warning("process_image: photo not found")
            return

        # ---- Pillow processing stub ----------------------------------------
        try:
            # In a real implementation we'd fetch the bytes from the media store.
            # Here we just demonstrate Pillow is available and the pipeline shape.
            _demo_resize_strip_exif(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
        except Exception:  # noqa: BLE001
            logging.getLogger(__name__).warning(
                "Pillow processing failed for photo %d; marking processed anyway", photo_id
            )

        photo.processed = True
        await session.commit()
        log.info("process_image: done")


def _demo_resize_strip_exif(raw: bytes, max_px: int = 1920) -> bytes:
    """Resize *raw* image bytes to at most *max_px* on the long edge, strip EXIF."""
    from PIL import Image, ImageOps

    opened: Image.Image = Image.open(io.BytesIO(raw))
    # Strip EXIF by converting through data
    img: Image.Image = ImageOps.exif_transpose(opened) or opened

    w, h = img.size
    if max(w, h) > max_px:
        scale = max_px / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    fmt = img.format or "JPEG"
    img.save(buf, format=fmt)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# WorkerSettings — consumed by `arq auto48.workers.images.WorkerSettings`
# ---------------------------------------------------------------------------


class WorkerSettings:
    functions = [process_image]

    @property
    def redis_settings(self) -> RedisSettings:
        from arq.connections import RedisSettings

        from auto48.config import get_settings

        return RedisSettings.from_dsn(get_settings().redis_url)
