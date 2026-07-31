"""
File: app/infrastructure/email/resend_email_sender.py
Folder: backend/app/infrastructure/email
Purpose: Concrete EmailSenderPort implementation using the Resend HTTP API.
"""

import httpx

from app.core.config import get_settings
from app.domain.ports.email_sender import EmailSenderPort


class ResendEmailSender(EmailSenderPort):
    _API_URL = "https://api.resend.com/emails"

    def send(self, to: str, subject: str, html_body: str) -> None:
        settings = get_settings()
        response = httpx.post(
            self._API_URL,
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={
                "from": settings.RESEND_FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html_body,
            },
            timeout=10.0,
        )
        response.raise_for_status()