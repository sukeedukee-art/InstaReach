from typing import Any, Optional
import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

class LeadValidator:
    """Validates and normalizes lead information."""

    @staticmethod
    def normalize_email(email: Optional[str]) -> str:
        """Normalizes email to trimmed lowercase."""
        if not email:
            return ""
        return str(email).strip().lower()

    @classmethod
    def is_valid_email(cls, email: Optional[str]) -> bool:
        """Checks if email format matches RFC-compliant pattern."""
        if not email:
            return False
        clean = cls.normalize_email(email)
        return bool(EMAIL_REGEX.match(clean))

    @staticmethod
    def clean_text(val: Any) -> str:
        """Cleans and converts values to string, handling None and NaN."""
        if val is None:
            return ""
        s = str(val).strip()
        if s.lower() in ("nan", "none", "null", "n/a"):
            return ""
        return s
