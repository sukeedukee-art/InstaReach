import logging
import time
from datetime import datetime
from typing import Callable, Optional
from sqlalchemy.orm import Session
from database.models import Campaign, Lead, EmailQueue, SentEmail
from email_engine.base_provider import BaseEmailProvider
from email_engine.smtp_provider import SmtpEmailProvider
from attachments.manager import AttachmentManager
from leads.deduplicator import Deduplicator

logger = logging.getLogger(__name__)

class CampaignProcessor:
    """
    Controlled email sending processor.
    Strictly checks campaign state before EVERY send.
    Respects test mode, dry run, pacing delays, and daily limits.
    """

    def __init__(self, provider: Optional[BaseEmailProvider] = None):
        self.provider = provider or SmtpEmailProvider()

    def process_campaign_batch(
        self,
        db: Session,
        campaign_id: int,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        """
        Processes pending queue items for a campaign.
        Stops immediately if campaign status transitions to PAUSED or STOPPED.
        """
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"status": "error", "message": f"Campaign {campaign_id} not found."}

        if campaign.status != "RUNNING":
            return {"status": "aborted", "message": f"Campaign is in status {campaign.status}, cannot process."}

        # Fetch pending queue items up to max_emails_per_run
        limit = campaign.max_emails_per_run or 50
        pending_queue = db.query(EmailQueue).filter(
            EmailQueue.campaign_id == campaign_id,
            EmailQueue.status == "PENDING"
        ).order_by(EmailQueue.scheduled_at.asc()).limit(limit).all()

        if not pending_queue:
            # Check if all leads are processed
            remaining_unprocessed = db.query(Lead).filter(
                Lead.campaign_id == campaign_id,
                Lead.status.in_(["NEW", "DRAFTED", "APPROVED", "QUEUED", "SENDING"])
            ).count()

            if remaining_unprocessed == 0:
                campaign.status = "COMPLETED"
                campaign.stopped_at = datetime.utcnow()
                db.commit()
                return {"status": "completed", "message": "All campaign emails processed."}

            return {"status": "idle", "message": "No pending emails in queue."}

        # Retrieve selected campaign attachments
        campaign_attachments = AttachmentManager.get_campaign_attachments(db, campaign_id)
        attachment_paths = [att.path for att in campaign_attachments]

        total_in_batch = len(pending_queue)
        sent_count = 0
        failed_count = 0
        skipped_count = 0

        for index, queue_item in enumerate(pending_queue):
            # Refresh campaign status in DB to ensure immediate response to PAUSE/STOP
            db.refresh(campaign)
            if campaign.status in ("PAUSED", "STOPPED"):
                logger.info(f"Campaign {campaign_id} status changed to {campaign.status}. Stopping processing loop.")
                if campaign.status == "STOPPED":
                    campaign.stopped_at = datetime.utcnow()
                db.commit()
                return {
                    "status": campaign.status.lower(),
                    "message": f"Campaign {campaign.status}. Remaining items left untouched in queue.",
                    "sent": sent_count,
                    "failed": failed_count,
                    "skipped": skipped_count
                }

            lead = queue_item.lead
            if not lead:
                queue_item.status = "FAILED"
                queue_item.last_error = "Associated lead record missing"
                db.commit()
                continue

            # Re-verify suppression and duplicate protection before dispatch
            can_send, skip_reason = Deduplicator.can_send_to_lead(db, campaign_id, lead.email)
            if not can_send:
                lead.status = "SKIPPED"
                lead.error_message = skip_reason
                queue_item.status = "CANCELLED"
                queue_item.last_error = skip_reason
                skipped_count += 1
                db.commit()
                if progress_callback:
                    progress_callback(index + 1, total_in_batch, f"Skipped {lead.email}: {skip_reason}")
                continue

            queue_item.status = "SENDING"
            lead.status = "SENDING"
            queue_item.attempts += 1
            db.commit()

            # Determine actual destination
            recipient_address = lead.email
            is_test = bool(campaign.test_mode)
            is_dry_run = bool(campaign.dry_run)

            if is_test:
                actual_recipient = campaign.test_recipient or lead.email
            else:
                actual_recipient = recipient_address

            sender_name = campaign.sender_name or "UK Teleradiology Outreach"
            sender_email = campaign.sender_email or "outreach@uk-teleradiology-partners.co.uk"
            subject = lead.draft_subject or "UK Diagnostic Imaging Services"
            body = lead.draft_body or ""

            if is_test:
                subject = f"[TEST MODE -> {recipient_address}] {subject}"

            # Execute Send / Dry Run
            send_success = False
            err_msg = None

            if is_dry_run:
                # Dry run simulation
                send_success = True
                err_msg = None
                logger.info(f"[DRY RUN] Would send to {actual_recipient} (Subject: {subject})")
            else:
                send_success, err_msg = self.provider.send_email(
                    sender_name=sender_name,
                    sender_email=sender_email,
                    recipient_email=actual_recipient,
                    subject=subject,
                    body_text=body,
                    attachment_paths=attachment_paths
                )

            # Record SentEmail history
            sent_record = SentEmail(
                campaign_id=campaign_id,
                lead_id=lead.id,
                recipient_email=recipient_address,
                actual_recipient_email=actual_recipient,
                subject=subject,
                body=body,
                status="DRY_RUN" if is_dry_run else ("SENT" if send_success else "FAILED"),
                is_test=is_test,
                is_dry_run=is_dry_run,
                error_message=err_msg,
                sent_at=datetime.utcnow()
            )
            db.add(sent_record)

            if send_success:
                lead.status = "SENT"
                lead.sent_at = datetime.utcnow()
                lead.error_message = None
                queue_item.status = "SENT"
                queue_item.sent_at = datetime.utcnow()
                sent_count += 1
                msg = f"Sent to {actual_recipient}" if not is_dry_run else f"Dry Run simulated for {actual_recipient}"
            else:
                lead.status = "FAILED"
                lead.failed_at = datetime.utcnow()
                lead.error_message = err_msg
                queue_item.status = "FAILED"
                queue_item.last_error = err_msg
                failed_count += 1
                msg = f"Failed for {actual_recipient}: {err_msg}"

            db.commit()

            if progress_callback:
                progress_callback(index + 1, total_in_batch, msg)

            # Enforce pacing delay between consecutive sends (unless in dry run or last item)
            if not is_dry_run and index < total_in_batch - 1 and campaign.delay_seconds > 0:
                time.sleep(campaign.delay_seconds)

        # Check if campaign is finished
        remaining_count = db.query(EmailQueue).filter(
            EmailQueue.campaign_id == campaign_id,
            EmailQueue.status == "PENDING"
        ).count()

        if remaining_count == 0:
            campaign.status = "COMPLETED"
            campaign.stopped_at = datetime.utcnow()
            db.commit()

        return {
            "status": "success",
            "sent": sent_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "message": f"Processed batch: {sent_count} sent, {failed_count} failed, {skipped_count} skipped."
        }
