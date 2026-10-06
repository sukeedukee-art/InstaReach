from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class EmailTemplate(Base):
    __tablename__ = "email_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaigns = relationship("Campaign", back_populates="template")

class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=True)
    size = Column(Integer, nullable=False) # Size in bytes
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign_associations = relationship("CampaignAttachment", back_populates="attachment", cascade="all, delete-orphan")

class CampaignAttachment(Base):
    __tablename__ = "campaign_attachments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    attachment_id = Column(Integer, ForeignKey("attachments.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="attachment_associations")
    attachment = relationship("Attachment", back_populates="campaign_associations")

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="DRAFT") # DRAFT, READY, RUNNING, PAUSED, STOPPED, COMPLETED
    sender_name = Column(String(150), nullable=True)
    sender_email = Column(String(150), nullable=True)
    sender_company = Column(String(150), nullable=True)
    template_id = Column(Integer, ForeignKey("email_templates.id"), nullable=True)
    ai_enabled = Column(Boolean, default=False)
    test_mode = Column(Boolean, default=True)
    test_recipient = Column(String(150), nullable=True)
    dry_run = Column(Boolean, default=False)
    max_emails_per_run = Column(Integer, default=50)
    delay_seconds = Column(Integer, default=30)
    daily_limit = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)

    template = relationship("EmailTemplate", back_populates="campaigns")
    leads = relationship("Lead", back_populates="campaign", cascade="all, delete-orphan")
    queue_items = relationship("EmailQueue", back_populates="campaign", cascade="all, delete-orphan")
    sent_items = relationship("SentEmail", back_populates="campaign", cascade="all, delete-orphan")
    attachment_associations = relationship("CampaignAttachment", back_populates="campaign", cascade="all, delete-orphan")

class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True)
    email = Column(String(255), nullable=False)
    job_title = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    company_description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="NEW") # NEW, DRAFTED, APPROVED, QUEUED, SENDING, SENT, FAILED, SKIPPED, STOPPED
    draft_subject = Column(String(255), nullable=True)
    draft_body = Column(Text, nullable=True)
    approved = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="leads")
    queue_items = relationship("EmailQueue", back_populates="lead", cascade="all, delete-orphan")
    sent_items = relationship("SentEmail", back_populates="lead", cascade="all, delete-orphan")

class EmailQueue(Base):
    __tablename__ = "email_queue"
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    scheduled_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="PENDING") # PENDING, SENDING, SENT, FAILED, CANCELLED
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)

    campaign = relationship("Campaign", back_populates="queue_items")
    lead = relationship("Lead", back_populates="queue_items")

class SentEmail(Base):
    __tablename__ = "sent_emails"
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    actual_recipient_email = Column(String(255), nullable=False) # For test mode inspection
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(50), default="SENT") # SENT, FAILED, DRY_RUN
    is_test = Column(Boolean, default=False)
    is_dry_run = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="sent_items")
    lead = relationship("Lead", back_populates="sent_items")

class SuppressionList(Base):
    __tablename__ = "suppression_list"
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    reason = Column(String(255), default="Unsubscribed / Manual Suppression")
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemSetting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
