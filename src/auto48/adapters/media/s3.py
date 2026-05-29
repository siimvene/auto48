"""S3MediaAdapter — boto3-backed adapter for S3-compatible storage (MinIO, AWS S3).

Import-time safe: the boto3 client is created lazily on first use, so the module
can be imported even when S3 credentials are not configured.
"""

from __future__ import annotations

import asyncio
import logging
from functools import cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import boto3 as _boto3_type  # only for type stubs

logger = logging.getLogger(__name__)


class S3MediaAdapter:
    """Thin async wrapper around a boto3 S3 client for S3-compatible stores."""

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        public_base_url: str | None = None,
    ) -> None:
        if not endpoint_url or not access_key or not secret_key:
            raise RuntimeError(
                "S3MediaAdapter requires AUTO48_S3_ENDPOINT, AUTO48_S3_ACCESS_KEY, "
                "and AUTO48_S3_SECRET_KEY to be set."
            )
        self._endpoint_url = endpoint_url
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        # If no explicit public base URL is provided, derive it from the endpoint.
        self._public_base = (
            public_base_url or f"{endpoint_url.rstrip('/')}/{bucket}"
        )

    @cached_property
    def _client(self) -> _boto3_type.client:  # noqa: F821
        import boto3  # deferred import — not required at import time

        return boto3.client(
            "s3",
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        )

    # ------------------------------------------------------------------
    # MediaPort interface
    # ------------------------------------------------------------------

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            ),
        )
        url = self.url_for(key)
        logger.debug("s3: uploaded %s (%d bytes) → %s", key, len(data), url)
        return url

    def url_for(self, key: str) -> str:
        return f"{self._public_base}/{key}"

    async def delete(self, key: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.delete_object(Bucket=self._bucket, Key=key),
        )
        logger.debug("s3: deleted %s", key)
