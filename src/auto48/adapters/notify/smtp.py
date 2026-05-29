"""SmtpNotifyAdapter: sends plain-text emails via stdlib smtplib.

Blocking smtplib calls are offloaded to a thread via asyncio.to_thread so the
event loop is never stalled.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from auto48.config import Settings


class SmtpNotifyAdapter:
    """Sends emails through a configured SMTP relay using stdlib only."""

    def __init__(self, settings: Settings) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._user = settings.smtp_user
        self._password = settings.smtp_password
        self._from = settings.email_from

    async def send_email(self, to: str, subject: str, body: str) -> None:
        """Dispatch a plain-text email; runs the blocking SMTP send in a thread."""
        await asyncio.to_thread(self._send_sync, to, subject, body)

    def _send_sync(self, to: str, subject: str, body: str) -> None:
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = self._from
        msg["To"] = to
        msg["Subject"] = subject

        with smtplib.SMTP(self._host, self._port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            if self._user:
                smtp.login(self._user, self._password)
            smtp.sendmail(self._from, [to], msg.as_string())
