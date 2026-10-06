import pytest
import io
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Campaign, Lead, SuppressionList
from leads.importer import LeadImporter
from leads.validator import LeadValidator
from leads.deduplicator import Deduplicator

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_lead_validator():
    assert LeadValidator.is_valid_email("test@example.com") is True
    assert LeadValidator.is_valid_email("dr.smith@nhs.net") is True
    assert LeadValidator.is_valid_email("invalid-email") is False
    assert LeadValidator.is_valid_email("") is False
    assert LeadValidator.is_valid_email(None) is False
    assert LeadValidator.normalize_email("  User@Example.COM ") == "user@example.com"

def test_column_mapping_detection():
    df = pd.DataFrame({
        "Organisation": ["NHS Trust 1"],
        "E-mail Address": ["contact@nhs.uk"],
        "Contact": ["Dr. John Doe"],
        "Position": ["Clinical Director"],
        "City": ["London"]
    })
    mapping = LeadImporter.detect_column_mappings(df)
    assert mapping["company_name"] == "Organisation"
    assert mapping["email"] == "E-mail Address"
    assert mapping["contact_name"] == "Contact"
    assert mapping["job_title"] == "Position"
    assert mapping["location"] == "City"

def test_lead_import_csv(db_session):
    campaign = Campaign(name="Test Campaign")
    db_session.add(campaign)
    db_session.commit()

    csv_data = """Company,Email,Contact Name,Location
St. Mary Trust,stmary@example.com,Dr. Mary Jones,London
Invalid Row,not-an-email,Bad Record,Leeds
St. Mary Trust,stmary@example.com,Dr. Mary Jones,London
"""
    df = pd.read_csv(io.StringIO(csv_data))
    imported, skipped, reasons = LeadImporter.process_and_import(db_session, campaign.id, df)

    assert imported == 1
    assert skipped == 2
    leads = db_session.query(Lead).filter(Lead.campaign_id == campaign.id).all()
    assert len(leads) == 1
    assert leads[0].email == "stmary@example.com"
    assert leads[0].first_name == "Dr."
    assert leads[0].last_name == "Mary Jones"

def test_deduplication_and_suppression(db_session):
    campaign = Campaign(name="Deduplication Campaign")
    db_session.add(campaign)
    db_session.commit()

    # Add suppression
    supp = SuppressionList(email="optout@example.com", reason="User unsubscribed")
    db_session.add(supp)
    db_session.commit()

    can_send, reason = Deduplicator.can_send_to_lead(db_session, campaign.id, "optout@example.com")
    assert can_send is False
    assert "Suppressed" in reason

    can_send_ok, _ = Deduplicator.can_send_to_lead(db_session, campaign.id, "valid@example.com")
    assert can_send_ok is True
