"""
File: app/domain/ports/email_sender.py
Folder: backend/app/domain/ports
Purpose: Interface for sending transactional emails. The Resend
         implementation lives in infrastructure/email/resend_email_sender.py.
"""

from abc import ABC, abstractmethod


class EmailSenderPort(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, html_body: str) -> None:
        raise NotImplementedError