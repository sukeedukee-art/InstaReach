import logging
from config.security import hash_password
from config.settings import ADMIN_USERNAME, ADMIN_PASSWORD, SENDER_NAME, SENDER_EMAIL, SENDER_COMPANY
from database.db import get_db, init_db
from database.models import User, EmailTemplate, SystemSetting

logger = logging.getLogger(__name__)

def seed_default_data():
    """Initializes schema and seeds initial admin user, default template, and system settings."""
    init_db()
    with get_db() as db:
        # 1. Seed Admin User if none exists
        existing_user = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if not existing_user:
            hashed = hash_password(ADMIN_PASSWORD or "adminpassword123")
            admin = User(username=ADMIN_USERNAME, password_hash=hashed)
            db.add(admin)
            logger.info(f"Seeded admin user: {ADMIN_USERNAME}")

        # 2. Seed Default Teleradiology Email Template if none exists
        template_count = db.query(EmailTemplate).count()
        if template_count == 0:
            default_template = EmailTemplate(
                name="UK Teleradiology Capacity & Out-of-Hours Support",
                description="Standard B2B outreach for NHS trusts and private clinical diagnostic centres.",
                subject="Diagnostic Reporting Capacity & Rapid Turnaround for {{company_name}}",
                body="""Dear {{first_name}},

I hope this message finds you well.

Given the growing reporting backlogs across diagnostic imaging departments in {{location}}, I am reaching out from {{sender_company}} to explore how we might assist {{company_name}} with clinical capacity.

We provide GMC-registered, UK-specialist consultant radiologists offering:
- Subspecialty MRI, CT, and plain film reporting
- Urgent 1-hour and routine 24/48-hour turnarounds
- Flexible overflow and out-of-hours coverage directly integrated into your PACS/RIS

Would you or the clinical lead at {{company_name}} be open to a brief 10-minute introductory conversation next week to review our compliance framework and audit-ready SLA?

Kind regards,

{{sender_name}}
{{sender_company}}
{{sender_email}}"""
            )
            db.add(default_template)
            logger.info("Seeded default UK teleradiology email template.")

        # 3. Seed Default System Settings if empty
        settings_defaults = {
            "default_sender_name": SENDER_NAME,
            "default_sender_email": SENDER_EMAIL,
            "default_sender_company": SENDER_COMPANY,
        }
        for key, val in settings_defaults.items():
            setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if not setting:
                db.add(SystemSetting(key=key, value=val, description=f"Default {key.replace('_', ' ')}"))

        db.commit()
