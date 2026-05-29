"""Notify adapter factory.

Returns SmtpNotifyAdapter when smtp_host is configured, otherwise falls back to
StubNotifyAdapter for offline dev and CI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from auto48.config import Settings
    from auto48.ports.notify import NotifyPort


def get_notify_adapter(settings: Settings) -> NotifyPort:
    """Return the appropriate NotifyPort implementation.

    SMTP adapter is returned only when smtp_host is non-empty; otherwise the
    in-process stub is used.
    """
    from auto48.adapters.notify.smtp import SmtpNotifyAdapter
    from auto48.adapters.notify.stub import StubNotifyAdapter

    if settings.smtp_host:
        return SmtpNotifyAdapter(settings)
    return StubNotifyAdapter()
