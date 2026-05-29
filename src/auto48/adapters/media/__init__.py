"""Media adapter package: factory that selects stub vs. S3 by configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from auto48.config import Settings
    from auto48.ports.media import MediaPort


def get_media_adapter(settings: Settings) -> MediaPort:
    """Return an S3MediaAdapter when S3 is fully configured, StubMediaAdapter otherwise."""
    if settings.s3_endpoint and settings.s3_access_key and settings.s3_secret_key:
        from auto48.adapters.media.s3 import S3MediaAdapter

        return S3MediaAdapter(  # type: ignore[return-value]
            endpoint_url=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket,
        )

    from auto48.adapters.media.stub import StubMediaAdapter

    return StubMediaAdapter()  # type: ignore[return-value]
