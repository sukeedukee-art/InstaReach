from sqlalchemy.orm import Session
from database.models import SuppressionList, SentEmail, Lead
from leads.validator import LeadValidator

class Deduplicator:
    """Checks whether a lead should be skipped due to suppression or prior contact."""

    @staticmethod
    def is_suppressed(db: Session, email: str) -> tuple[bool, str]:
        """Checks if email is present in the suppression / unsubscribe list."""
        norm_email = LeadValidator.normalize_email(email)
        suppressed = db.query(SuppressionList).filter(SuppressionList.email == norm_email).first()
        if suppressed:
            return True, f"Suppressed (Reason: {suppressed.reason})"
        return False, ""

    @staticmethod
    def is_already_sent_in_campaign(db: Session, campaign_id: int, email: str) -> tuple[bool, str]:
        """Checks if email has already been sent an email in the given campaign."""
        norm_email = LeadValidator.normalize_email(email)
        # Check in sent_emails table
        already_sent = db.query(SentEmail).filter(
            SentEmail.campaign_id == campaign_id,
            SentEmail.recipient_email == norm_email,
            SentEmail.status == "SENT"
        ).first()
        if already_sent:
            return True, "Email already sent in this campaign"
        
        # Check in leads table
        lead_sent = db.query(Lead).filter(
            Lead.campaign_id == campaign_id,
            Lead.email == norm_email,
            Lead.status == "SENT"
        ).first()
        if lead_sent:
            return True, "Lead marked as SENT in this campaign"

        return False, ""

    @classmethod
    def can_send_to_lead(cls, db: Session, campaign_id: int, email: str) -> tuple[bool, str]:
        """
        Runs comprehensive duplicate and suppression protection check.
        Returns (can_send, skip_reason).
        """
        if not LeadValidator.is_valid_email(email):
            return False, "Invalid email address format"

        is_supp, supp_reason = cls.is_suppressed(db, email)
        if is_supp:
            return False, supp_reason

        is_dup, dup_reason = cls.is_already_sent_in_campaign(db, campaign_id, email)
        if is_dup:
            return False, dup_reason

        return True, ""
