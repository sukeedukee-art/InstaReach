import pytest
import io
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Campaign, Lead, EmailQueue, SentEmail, Attachment
from campaigns.processor import CampaignProcessor
from attachments.manager import AttachmentManager
from email_engine.base_provider import BaseEmailProvider

class MockEmailProvider(BaseEmailProvider):
    def __init__(self, should_succeed=True):
        self.should_succeed = should_succeed
        self.sent_emails = []

    def send_email(self, sender_name, sender_email, recipient_email, subject, body_text, attachment_paths=None, body_html=None):
        if self.should_succeed:
            self.sent_emails.append({
                "recipient": recipient_email,
                "subject": subject,
                "attachments": attachment_paths or []
            })
            return True, None
        return False, "Simulated SMTP timeout error"

    def test_connection(self):
        return self.should_succeed, None if self.should_succeed else "Connection failed"

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_test_mode_redirection(db_session):
    campaign = Campaign(
        name="Test Mode Campaign",
        status="RUNNING",
        test_mode=True,
        test_recipient="internal-reviewer@example.com",
        dry_run=False,
        delay_seconds=0
    )
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(
        campaign_id=campaign.id,
        email="real-client@example.co.uk",
        contact_name="Dr. Real",
        draft_subject="Diagnostic inquiry",
        draft_body="Hello Doctor",
        status="QUEUED",
        approved=True
    )
    db_session.add(lead)
    db_session.commit()

    q_item = EmailQueue(campaign_id=campaign.id, lead_id=lead.id, status="PENDING")
    db_session.add(q_item)
    db_session.commit()

    mock_provider = MockEmailProvider(should_succeed=True)
    processor = CampaignProcessor(provider=mock_provider)

    result = processor.process_campaign_batch(db_session, campaign.id)
    assert result["sent"] == 1
    assert len(mock_provider.sent_emails) == 1
    # Check that email was sent to test recipient and NOT real client
    assert mock_provider.sent_emails[0]["recipient"] == "internal-reviewer@example.com"
    assert "[TEST MODE -> real-client@example.co.uk]" in mock_provider.sent_emails[0]["subject"]

def test_dry_run_mode_does_not_call_provider(db_session):
    campaign = Campaign(
        name="Dry Run Campaign",
        status="RUNNING",
        test_mode=False,
        dry_run=True,
        delay_seconds=0
    )
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(
        campaign_id=campaign.id,
        email="client@example.co.uk",
        draft_subject="Subject",
        draft_body="Body",
        status="QUEUED"
    )
    db_session.add(lead)
    db_session.commit()

    q_item = EmailQueue(campaign_id=campaign.id, lead_id=lead.id, status="PENDING")
    db_session.add(q_item)
    db_session.commit()

    mock_provider = MockEmailProvider(should_succeed=True)
    processor = CampaignProcessor(provider=mock_provider)

    result = processor.process_campaign_batch(db_session, campaign.id)
    assert result["sent"] == 1
    # Provider must NOT have been called in dry-run
    assert len(mock_provider.sent_emails) == 0

    sent_record = db_session.query(SentEmail).filter(SentEmail.lead_id == lead.id).first()
    assert sent_record.status == "DRY_RUN"

def test_attachment_handling_and_removal(db_session):
    campaign = Campaign(name="Attachment Campaign")
    db_session.add(campaign)
    db_session.commit()

    # Upload dummy attachment
    dummy_file = io.BytesIO(b"%PDF-1.4 dummy pdf content")
    att = AttachmentManager.save_attachment(db_session, dummy_file, "sla_document.pdf")
    
    # Assign to campaign
    AttachmentManager.assign_to_campaign(db_session, campaign.id, att.id)
    attached = AttachmentManager.get_campaign_attachments(db_session, campaign.id)
    assert len(attached) == 1
    assert attached[0].filename == "sla_document.pdf"

    # Remove from campaign
    AttachmentManager.remove_from_campaign(db_session, campaign.id, att.id)
    attached_after = AttachmentManager.get_campaign_attachments(db_session, campaign.id)
    assert len(attached_after) == 0
