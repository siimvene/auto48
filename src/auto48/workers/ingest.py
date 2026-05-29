"""arq ingest worker: run_feed_ingest task.

Usage
-----
Run the worker directly:

    AUTO48_REDIS_URL=redis://localhost:6379/0 \\
    arq auto48.workers.ingest.WorkerSettings

The task fetches a DealerFeed by id, runs the full ingest pipeline, and
commits an IngestRun row with final counts and status.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from arq.connections import RedisSettings

logger = structlog.get_logger(__name__)


async def run_feed_ingest(ctx: dict[str, object], feed_id: int) -> None:  # noqa: ARG001
    """Fetch, parse, and upsert a dealer feed identified by *feed_id*.

    This task is the arq entry point. It creates its own DB session and uses
    HttpFeedAdapter for live feeds.
    """
    from auto48.adapters.feed.http_fetch import HttpFeedAdapter
    from auto48.db import async_session_factory
    from auto48.services.ingest import ingest_feed

    log = logger.bind(feed_id=feed_id)
    log.info("run_feed_ingest: starting")

    adapter = HttpFeedAdapter()
    async with async_session_factory() as session:
        try:
            run = await ingest_feed(session, feed_id, adapter)
            log.info(
                "run_feed_ingest: done",
                run_id=run.id,
                status=run.status.value,
                created=run.created_count,
                updated=run.updated_count,
                errors=run.error_count,
            )
        except Exception as exc:
            logging.getLogger(__name__).error(
                "run_feed_ingest: unhandled error feed=%d: %s", feed_id, exc
            )
            raise


class WorkerSettings:
    functions = [run_feed_ingest]

    @property
    def redis_settings(self) -> RedisSettings:
        from arq.connections import RedisSettings

        from auto48.config import get_settings

        return RedisSettings.from_dsn(get_settings().redis_url)
