"""StubNotifyAdapter: in-process email recorder for dev and unit tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SentEmail:
    """A single captured email message."""

    to: str
    subject: str
    body: str


class StubNotifyAdapter:
    """Records outgoing emails in a list; never opens a network connection."""

    def __init__(self) -> None:
        self.sent: list[SentEmail] = []

    async def send_email(self, to: str, subject: str, body: str) -> None:
        """Append the email to the in-memory sent list."""
        self.sent.append(SentEmail(to=to, subject=subject, body=body))

    def clear(self) -> None:
        """Reset the sent list between test cases."""
        self.sent.clear()
