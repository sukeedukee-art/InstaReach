import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Initialize logger
logger = logging.getLogger(__name__)

# Base Project Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from base directory
load_dotenv(BASE_DIR / ".env")

# App & Storage Paths
STORAGE_DIR = BASE_DIR / "storage"
DATABASE_DIR = STORAGE_DIR / "database"
ATTACHMENTS_DIR = STORAGE_DIR / "attachments"

# Ensure storage directories exist
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_DIR / 'cold_mail.db'}")

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# SMTP Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587").strip() or 587)
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")

# Default Sender Identity
SENDER_NAME = os.getenv("SENDER_NAME", "Dr. Alistair Vance").strip()
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "outreach@uk-teleradiology-partners.co.uk").strip()
SENDER_COMPANY = os.getenv("SENDER_COMPANY", "UK Teleradiology Partners").strip()

# Admin Auth (Prototype credentials)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "adminpassword123").strip()
DEFAULT_DELAY_SECONDS = int(os.getenv("DEFAULT_DELAY_SECONDS", "30").strip() or 30)
DEFAULT_DAILY_LIMIT = int(os.getenv("DEFAULT_DAILY_LIMIT", "100").strip() or 100)

def validate_smtp_settings():
    """Ensures required SMTP settings are present; raises if any are missing."""
    missing = []
    if not SMTP_HOST:
        missing.append('SMTP_HOST')
    if not SMTP_USERNAME:
        missing.append('SMTP_USERNAME')
    if not SMTP_PASSWORD:
        missing.append('SMTP_PASSWORD')
    if missing:
        msg = f"SMTP configuration incomplete: missing {', '.join(missing)}. Please set them in the .env file."
        logger.error(msg)
        raise RuntimeError(msg)
    return True

# Validate on import
try:
    validate_smtp_settings()
except RuntimeError:
    # Swallow exception to allow application to start but ensure errors are visible during connection attempts.
    pass

def reload_settings():
    """Reload environment variables from .env and re‑validate SMTP configuration."""
    load_dotenv(BASE_DIR / ".env", override=True)
    # Re‑load configuration variables
    global GEMINI_API_KEY, SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_USE_TLS
    global SENDER_NAME, SENDER_EMAIL, SENDER_COMPANY, DEFAULT_DELAY_SECONDS, DEFAULT_DAILY_LIMIT
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587").strip() or 587)
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")
    SENDER_NAME = os.getenv("SENDER_NAME", "Dr. Alistair Vance").strip()
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "outreach@uk-teleradiology-partners.co.uk").strip()
    SENDER_COMPANY = os.getenv("SENDER_COMPANY", "UK Teleradiology Partners").strip()
    DEFAULT_DELAY_SECONDS = int(os.getenv("DEFAULT_DELAY_SECONDS", "30").strip() or 30)
    DEFAULT_DAILY_LIMIT = int(os.getenv("DEFAULT_DAILY_LIMIT", "100").strip() or 100)
    validate_smtp_settings()
    return True

    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587").strip() or 587)
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1", "yes")
    SENDER_NAME = os.getenv("SENDER_NAME", "Dr. Alistair Vance").strip()
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "outreach@uk-teleradiology-partners.co.uk").strip()
    SENDER_COMPANY = os.getenv("SENDER_COMPANY", "UK Teleradiology Partners").strip()
    DEFAULT_DELAY_SECONDS = int(os.getenv("DEFAULT_DELAY_SECONDS", "30").strip() or 30)
    DEFAULT_DAILY_LIMIT = int(os.getenv("DEFAULT_DAILY_LIMIT", "100").strip() or 100)

def save_env_file(key_values: dict):
    """Saves or updates environment variables in .env safely."""
    env_path = BASE_DIR / ".env"
    existing_lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    current_keys = set()
    new_lines = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _ = stripped.split("=", 1)
            k = k.strip()
            if k in key_values:
                new_lines.append(f"{k}={key_values[k]}\n")
                current_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in key_values.items():
        if k not in current_keys:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    
    reload_settings()

