"""NotifyPort: clean-room protocol for sending notification emails.

Implementations live under adapters/notify/. The port keeps the domain layer
unaware of whether email is sent via SMTP, a stub, or any future provider.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class NotifyPort(Protocol):
    """Async contract for email notification providers."""

    async def send_email(self, to: str, subject: str, body: str) -> None:
        """Send a plain-text email.

        Args:
            to:      Recipient address.
            subject: Email subject line.
            body:    Plain-text body.
        """
        ...
