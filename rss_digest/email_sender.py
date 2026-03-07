from __future__ import annotations

import smtplib
from email.message import EmailMessage

from rss_digest.config import AppConfig


def send_digest_email(config: AppConfig, subject: str, markdown_body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.digest_email_from
    message["To"] = config.digest_email_to

    # Plain fallback plus markdown alternative.
    message.set_content(markdown_body)
    message.add_alternative(markdown_body, subtype="markdown")

    with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
        server.starttls()
        server.login(config.smtp_user, config.smtp_app_password)
        server.send_message(message)
