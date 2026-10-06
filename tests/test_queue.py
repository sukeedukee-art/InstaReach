import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Campaign, Lead, EmailQueue, EmailTemplate
from campaigns.queue_manager import QueueManager
from campaigns.campaign_manager import CampaignManager

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_queue_creation_and_lifecycle(db_session):
    tpl = EmailTemplate(name="Test Template", subject="Subj", body="Body")
    db_session.add(tpl)
    db_session.commit()

    campaign = Campaign(name="Queue Test Campaign", template_id=tpl.id, status="DRAFT")
    db_session.add(campaign)
    db_session.commit()

    # Add 2 leads: 1 approved with draft, 1 without draft
    lead1 = Lead(
        campaign_id=campaign.id,
        email="lead1@example.com",
        contact_name="Lead One",
        draft_subject="Subject 1",
        draft_body="Body 1",
        status="APPROVED",
        approved=True
    )
    lead2 = Lead(
        campaign_id=campaign.id,
        email="lead2@example.com",
        contact_name="Lead Two",
        status="DRAFTED",
        approved=False
    )
    db_session.add_all([lead1, lead2])
    db_session.commit()

    # Queue approved leads
    queued_cnt, skipped_cnt, reasons = QueueManager.queue_approved_leads(db_session, campaign.id)
    assert queued_cnt == 1
    assert skipped_cnt == 0

    items = QueueManager.get_queue_status(db_session, campaign.id)
    assert len(items) == 1
    assert items[0].status == "PENDING"
    assert items[0].lead_id == lead1.id

def test_stop_campaign_cancels_queue(db_session):
    campaign = Campaign(name="Stop Test", status="RUNNING")
    db_session.add(campaign)
    db_session.commit()

    lead = Lead(campaign_id=campaign.id, email="lead@example.com", status="QUEUED")
    db_session.add(lead)
    db_session.commit()

    q_item = EmailQueue(campaign_id=campaign.id, lead_id=lead.id, status="PENDING")
    db_session.add(q_item)
    db_session.commit()

    # Stop campaign
    CampaignManager.stop_campaign(db_session, campaign.id)
    db_session.refresh(campaign)
    db_session.refresh(q_item)
    db_session.refresh(lead)

    assert campaign.status == "STOPPED"
    assert q_item.status == "CANCELLED"
    assert lead.status == "STOPPED"
