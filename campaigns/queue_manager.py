import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import Campaign, Lead, EmailQueue
from leads.deduplicator import Deduplicator

logger = logging.getLogger(__name__)

class QueueManager:
    """Manages scheduling, inspecting, and cancelling email queue items."""

    @staticmethod
    def queue_approved_leads(db: Session, campaign_id: int) -> tuple[int, int, List[str]]:
        """
        Enqueues all leads with status 'APPROVED' for a campaign.
        Runs deduplication and suppression checks before queuing.
        Returns: (queued_count, skipped_count, reasons)
        """
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return 0, 0, [f"Campaign {campaign_id} not found"]

        approved_leads = db.query(Lead).filter(
            Lead.campaign_id == campaign_id,
            Lead.status == "APPROVED"
        ).all()

        queued_count = 0
        skipped_count = 0
        reasons = []

        for lead in approved_leads:
            # Duplicate & Suppression Check
            can_send, reason = Deduplicator.can_send_to_lead(db, campaign_id, lead.email)
            if not can_send:
                lead.status = "SKIPPED"
                lead.error_message = reason
                skipped_count += 1
                reasons.append(f"Lead {lead.email} skipped: {reason}")
                continue

            # Ensure subject and body are present
            if not lead.draft_subject or not lead.draft_body:
                lead.status = "SKIPPED"
                lead.error_message = "Missing draft subject or body"
                skipped_count += 1
                reasons.append(f"Lead {lead.email} skipped: Missing draft content")
                continue

            # Check if already has an active queue entry
            existing_queue = db.query(EmailQueue).filter(
                EmailQueue.campaign_id == campaign_id,
                EmailQueue.lead_id == lead.id,
                EmailQueue.status.in_(["PENDING", "SENDING"])
            ).first()

            if not existing_queue:
                q_item = EmailQueue(
                    campaign_id=campaign_id,
                    lead_id=lead.id,
                    status="PENDING",
                    scheduled_at=datetime.utcnow()
                )
                db.add(q_item)

            lead.status = "QUEUED"
            queued_count += 1

        db.commit()
        logger.info(f"Campaign {campaign_id}: Queued {queued_count} leads, skipped {skipped_count}.")
        return queued_count, skipped_count, reasons

    @staticmethod
    def cancel_pending_queue(db: Session, campaign_id: int):
        """Cancels all pending queue items when campaign is stopped."""
        pending_items = db.query(EmailQueue).filter(
            EmailQueue.campaign_id == campaign_id,
            EmailQueue.status == "PENDING"
        ).all()

        for item in pending_items:
            item.status = "CANCELLED"
            if item.lead and item.lead.status == "QUEUED":
                item.lead.status = "STOPPED"

        db.commit()
        logger.info(f"Campaign {campaign_id}: Cancelled {len(pending_items)} pending queue items.")

    @staticmethod
    def get_queue_status(db: Session, campaign_id: Optional[int] = None) -> List[EmailQueue]:
        """Returns email queue items ordered by schedule."""
        query = db.query(EmailQueue)
        if campaign_id:
            query = query.filter(EmailQueue.campaign_id == campaign_id)
        return query.order_by(EmailQueue.scheduled_at.desc()).all()
