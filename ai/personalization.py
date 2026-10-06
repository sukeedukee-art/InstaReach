import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from database.models import Lead, Campaign, EmailTemplate
from templates.template_engine import TemplateEngine
from ai.gemini_client import GeminiClient
from ai.prompts import build_personalization_prompt

logger = logging.getLogger(__name__)

class PersonalizationService:
    """Coordinates email drafting using either Standard Template rendering or Gemini AI Personalization."""

    @classmethod
    def generate_draft_for_lead(
        cls,
        db: Session,
        lead: Lead,
        campaign: Campaign,
        template: Optional[EmailTemplate] = None,
        force_template_mode: bool = False
    ) -> Tuple[bool, str, str, Optional[str]]:
        """
        Generates subject and body for a lead.
        Returns: (success: bool, subject: str, body: str, error: Optional[str])
        """
        # Resolve template
        selected_template = template or campaign.template
        if not selected_template:
            # Fallback to the first available template or a hardcoded default
            selected_template = db.query(EmailTemplate).first()
            if not selected_template:
                return False, "", "", "No email template available for this campaign."

        # Prepare context
        context = {
            "contact_name": lead.contact_name or "",
            "first_name": lead.first_name or "",
            "last_name": lead.last_name or "",
            "company_name": lead.company_name or "",
            "job_title": lead.job_title or "",
            "website": lead.website or "",
            "location": lead.location or "",
            "company_description": lead.company_description or "",
            "notes": lead.notes or "",
            "sender_name": campaign.sender_name or "Dr. Alistair Vance",
            "sender_company": campaign.sender_company or "UK Teleradiology Partners",
            "sender_email": campaign.sender_email or "outreach@uk-teleradiology-partners.co.uk",
        }

        # Case 1: Template Mode (or AI disabled or forced fallback)
        if not campaign.ai_enabled or force_template_mode:
            subject, body = TemplateEngine.render_email(
                selected_template.subject,
                selected_template.body,
                context
            )
            return True, subject, body, None

        # Case 2: AI Personalization Mode
        ai_client = GeminiClient()
        if not ai_client.is_configured():
            logger.warning(f"Campaign {campaign.id} requested AI mode but Gemini is not configured. Falling back to template mode.")
            subject, body = TemplateEngine.render_email(
                selected_template.subject,
                selected_template.body,
                context
            )
            return True, subject, body, "Gemini API key not configured: Generated using standard template mode."

        lead_data = {
            "contact_name": lead.contact_name,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "company_name": lead.company_name,
            "job_title": lead.job_title,
            "website": lead.website,
            "location": lead.location,
            "company_description": lead.company_description,
            "notes": lead.notes
        }

        campaign_data = {
            "sender_name": campaign.sender_name,
            "sender_company": campaign.sender_company,
            "sender_email": campaign.sender_email,
            "description": campaign.description or campaign.name
        }

        prompt = build_personalization_prompt(
            lead_data=lead_data,
            campaign_data=campaign_data,
            base_subject_template=selected_template.subject,
            base_body_template=selected_template.body
        )

        ai_result, err = ai_client.generate_email_content(prompt)
        if ai_result:
            return True, ai_result["subject"], ai_result["body"], None
        else:
            logger.error(f"AI Personalization failed for lead {lead.id}: {err}")
            # Fallback to standard template so user is not completely blocked, but report the AI error
            subject, body = TemplateEngine.render_email(
                selected_template.subject,
                selected_template.body,
                context
            )
            return False, subject, body, f"AI Error: {err}. Generated fallback template draft."
