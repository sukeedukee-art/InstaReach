from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path

class BaseEmailProvider(ABC):
    """
    Abstract interface for email delivery providers.
    Enables pluggable backends such as SMTP, Gmail API, Microsoft 365 Graph, etc.
    """

    @abstractmethod
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
        """
        Sends an email.
        Returns:
            (success: bool, error_message: Optional[str])
        """
        pass

    @abstractmethod
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """
        Tests whether the provider connection and credentials are valid.
        Returns:
            (connected: bool, error_message: Optional[str])
        """
        pass
