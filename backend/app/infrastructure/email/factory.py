"""
File: app/infrastructure/email/factory.py
Folder: backend/app/infrastructure/email
Purpose: Builds the configured EmailSenderPort implementation. Only one
         provider today (Resend), but this keeps the same factory pattern
         as build_llm_client / build_file_storage for future swaps.
"""

from app.domain.ports.email_sender import EmailSenderPort
from app.infrastructure.email.resend_email_sender import ResendEmailSender


def build_email_sender() -> EmailSenderPort:
    return ResendEmailSender()