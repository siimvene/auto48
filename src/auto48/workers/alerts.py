"""arq alerts worker.

Tasks
-----
run_saved_search_alerts(ctx)
    Iterates all active saved searches, finds new matching listings, creates
    Alert rows, and dispatches summary emails via the configured NotifyPort.

Usage
-----
Run the worker:

    arq auto48.workers.alerts.WorkerSettings

Or alongside images.py in a combined worker process.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from arq.connections import RedisSettings

logger = structlog.get_logger(__name__)


async def run_saved_search_alerts(ctx: dict[str, object]) -> None:  # noqa: ARG001
    """Dispatch saved-search alert emails for all active saved searches."""
    from auto48.adapters.notify import get_notify_adapter
    from auto48.config import get_settings
    from auto48.db import async_session_factory
    from auto48.services.saved_search import run_alerts

    settings = get_settings()
    notify = get_notify_adapter(settings)

    async with async_session_factory() as session:
        try:
            await run_alerts(session, notify)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    logger.info("run_saved_search_alerts: complete")


class WorkerSettings:
    functions = [run_saved_search_alerts]

    @property
    def redis_settings(self) -> RedisSettings:
        from arq.connections import RedisSettings

        from auto48.config import get_settings

        return RedisSettings.from_dsn(get_settings().redis_url)
