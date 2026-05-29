"""HTTP and stub adapters that implement FeedPort."""

from __future__ import annotations


class HttpFeedAdapter:
    """Fetch a URL using httpx.AsyncClient and return the raw bytes."""

    async def fetch(self, url: str) -> bytes:
        """GET *url* and return the response body as bytes."""
        import httpx

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content


class StubFeedAdapter:
    """Return canned bytes regardless of the URL — for tests and offline dev."""

    def __init__(self, payload: bytes = b"") -> None:
        self._payload = payload

    async def fetch(self, url: str) -> bytes:  # noqa: ARG002
        """Return the canned payload; URL is ignored."""
        return self._payload
