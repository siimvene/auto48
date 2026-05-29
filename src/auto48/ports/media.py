"""MediaPort — port (Protocol) for object-store operations.

Adapters: StubMediaAdapter (dev/tests), S3MediaAdapter (production/MinIO).
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MediaPort(Protocol):
    """Store, resolve, and delete media objects (photos)."""

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Upload *data* under *key* and return the public URL."""
        ...

    def url_for(self, key: str) -> str:
        """Return the public URL for an already-uploaded *key*."""
        ...

    async def delete(self, key: str) -> None:
        """Remove the object identified by *key*."""
        ...
