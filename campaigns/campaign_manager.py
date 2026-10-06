import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models import Campaign, Lead, EmailTemplate
from ai.personalization import PersonalizationService
from campaigns.queue_manager import QueueManager

logger = logging.getLogger(__name__)

class CampaignManager:
    """Manages high-level campaign actions: creation, draft generation, lifecycle transitions."""

    @staticmethod
    def create_campaign(
        db: Session,
        name: str,
        description: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_email: Optional[str] = None,
        sender_company: Optional[str] = None,
        template_id: Optional[int] = None,
        ai_enabled: bool = False,
        test_mode: bool = True,
        test_recipient: Optional[str] = None,
        dry_run: bool = False,
        delay_seconds: int = 30,
        daily_limit: int = 100,
        max_emails_per_run: int = 50
    ) -> Campaign:
        """Creates and saves a new campaign."""
        campaign = Campaign(
            name=name,
            description=description,
            sender_name=sender_name,
            sender_email=sender_email,
            sender_company=sender_company,
            template_id=template_id,
            ai_enabled=ai_enabled,
            test_mode=test_mode,
            test_recipient=test_recipient,
            dry_run=dry_run,
            delay_seconds=delay_seconds,
            daily_limit=daily_limit,
            max_emails_per_run=max_emails_per_run,
            status="DRAFT"
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        logger.info(f"Created Campaign '{campaign.name}' (ID: {campaign.id})")
        return campaign

    @classmethod
    def generate_drafts_for_campaign(
        cls,
        db: Session,
        campaign_id: int,
        lead_ids: Optional[List[int]] = None,
        regenerate_existing: bool = False
    ) -> tuple[int, int, List[str]]:
        """
        Generates personalized draft subject and body for leads in campaign.
        Returns: (success_count, fail_count, errors)
        """
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return 0, 0, [f"Campaign {campaign_id} not found"]

        query = db.query(Lead).filter(Lead.campaign_id == campaign_id)
        if lead_ids:
            query = query.filter(Lead.id.in_(lead_ids))
        elif not regenerate_existing:
            query = query.filter(Lead.status == "NEW")

        leads = query.all()
        success_count = 0
        fail_count = 0
        errors = []

        for lead in leads:
            ok, subj, body, err = PersonalizationService.generate_draft_for_lead(
                db=db,
                lead=lead,
                campaign=campaign
            )
            lead.draft_subject = subj
            lead.draft_body = body
            lead.status = "DRAFTED"
            lead.updated_at = datetime.utcnow()

            if ok:
                success_count += 1
            else:
                fail_count += 1
                if err:
                    errors.append(f"Lead {lead.email}: {err}")

        if campaign.status == "DRAFT" and success_count > 0:
            campaign.status = "READY"

        db.commit()
        logger.info(f"Campaign {campaign_id}: Generated {success_count} drafts ({fail_count} with warnings).")
        return success_count, fail_count, errors

    @staticmethod
    def start_campaign(db: Session, campaign_id: int) -> tuple[bool, str]:
        """Transitions campaign to RUNNING and automatically enqueues approved leads if queue is empty."""
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return False, "Campaign not found"

        if campaign.status not in ("READY", "PAUSED", "STOPPED", "DRAFT"):
            return False, f"Cannot start campaign in status '{campaign.status}'"

        # Check if there are queued leads; if not, try to queue approved leads
        QueueManager.queue_approved_leads(db, campaign_id)

        campaign.status = "RUNNING"
        if not campaign.started_at:
            campaign.started_at = datetime.utcnow()
        db.commit()
        logger.info(f"Campaign {campaign_id} started (Status: RUNNING)")
        return True, "Campaign is now running."

    @staticmethod
    def pause_campaign(db: Session, campaign_id: int) -> tuple[bool, str]:
        """Pauses a running campaign."""
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return False, "Campaign not found"

        campaign.status = "PAUSED"
        db.commit()
        logger.info(f"Campaign {campaign_id} paused.")
        return True, "Campaign has been paused."

    @staticmethod
    def resume_campaign(db: Session, campaign_id: int) -> tuple[bool, str]:
        """Resumes a paused campaign."""
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return False, "Campaign not found"

        if campaign.status != "PAUSED":
            return False, f"Campaign is in status '{campaign.status}', cannot resume."

        campaign.status = "RUNNING"
        db.commit()
        logger.info(f"Campaign {campaign_id} resumed.")
        return True, "Campaign resumed."

    @staticmethod
    def stop_campaign(db: Session, campaign_id: int) -> tuple[bool, str]:
        """Stops a campaign and cancels any pending queue items while preserving leads."""
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return False, "Campaign not found"

        campaign.status = "STOPPED"
        campaign.stopped_at = datetime.utcnow()
        QueueManager.cancel_pending_queue(db, campaign_id)
        db.commit()
        logger.info(f"Campaign {campaign_id} stopped.")
        return True, "Campaign stopped and pending queue cancelled."
