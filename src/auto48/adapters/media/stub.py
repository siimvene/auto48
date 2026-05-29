"""StubMediaAdapter — in-process store for dev and unit tests (no external deps)."""

import logging

logger = logging.getLogger(__name__)

_FAKE_BASE = "http://stub-media/objects"


class StubMediaAdapter:
    """Stores bytes in an in-process dict; returns fake deterministic URLs."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> str:  # noqa: ARG002
        self._store[key] = data
        url = f"{_FAKE_BASE}/{key}"
        logger.debug("stub: stored %s (%d bytes) → %s", key, len(data), url)
        return url

    def url_for(self, key: str) -> str:
        return f"{_FAKE_BASE}/{key}"

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
        logger.debug("stub: deleted %s", key)
