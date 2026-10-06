import logging
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import List, Optional

from config.settings import SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_USE_TLS
from email_engine.base_provider import BaseEmailProvider

logger = logging.getLogger(__name__)

class SmtpEmailProvider(BaseEmailProvider):
    """Production-grade SMTP provider supporting TLS/SSL, attachments, and connection verification."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None
    ):
        self.host = host or SMTP_HOST
        self.port = port or SMTP_PORT
        self.username = username or SMTP_USERNAME
        self.password = password or SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else SMTP_USE_TLS

    def is_configured(self) -> bool:
        return bool(self.host and self.username and self.password)

    def test_connection(self) -> tuple[bool, Optional[str]]:
        """Verifies SMTP credentials and server connectivity."""
        # Verify required SMTP configuration
        missing = []
        if not self.host:
            missing.append('SMTP_HOST')
        if not self.username:
            missing.append('SMTP_USERNAME')
        if not self.password:
            missing.append('SMTP_PASSWORD')
        if missing:
            msg = f"SMTP settings incomplete: missing {', '.join(missing)}."
            logger.error(msg)
            return False, msg
        # All required settings present, continue with connection test

        try:
            if self.port == 465:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10)
                if self.use_tls:
                    server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            server.quit()
            return True, None
        except Exception as e:
            logger.error(f"SMTP Connection Test Failed: {e}")
            return False, str(e)

    def send_email(
        self,
        sender_name: str,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body_text: str,
        attachment_paths: Optional[List[str]] = None,
        body_html: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """Builds and dispatches an email message with attachments via SMTP."""
        if not self.is_configured():
            return False, "SMTP is not configured. Please supply SMTP credentials."

        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
            msg["To"] = recipient_email
            msg.set_content(body_text)

            if body_html:
                msg.add_alternative(body_html, subtype="html")

            # Attach files if supplied
            if attachment_paths:
                for file_path_str in attachment_paths:
                    path = Path(file_path_str)
                    if not path.exists():
                        logger.warning(f"Attachment file not found at path: {path}")
                        continue

                    mime_type, _ = mimetypes.guess_type(str(path))
                    if mime_type is None:
                        main_type, sub_type = "application", "octet-stream"
                    else:
                        main_type, sub_type = mime_type.split("/", 1)

                    with open(path, "rb") as f:
                        file_data = f.read()

                    msg.add_attachment(
                        file_data,
                        maintype=main_type,
                        subtype=sub_type,
                        filename=path.name
                    )

            # Establish Connection and Send
            if self.port == 465:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=20)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=20)
                if self.use_tls:
                    server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            server.send_message(msg)
            server.quit()
            logger.info(f"Successfully sent email to {recipient_email} with subject '{subject}'")
            return True, None

        except Exception as e:
            logger.error(f"Failed sending email to {recipient_email}: {e}")
            return False, str(e)
