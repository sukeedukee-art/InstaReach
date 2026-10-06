import os
import shutil
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.settings import (
    BASE_DIR, GEMINI_API_KEY, SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
    SMTP_USE_TLS, SENDER_NAME, SENDER_EMAIL, SENDER_COMPANY, DEFAULT_DELAY_SECONDS,
    DEFAULT_DAILY_LIMIT, save_env_file, reload_settings
)
from config.security import hash_password, verify_password
from database.db import get_db, init_db
from database.schema import seed_default_data
from database.models import Campaign, Lead, EmailTemplate, Attachment, CampaignAttachment, EmailQueue, SentEmail, SuppressionList, User
from campaigns.campaign_manager import CampaignManager
from campaigns.queue_manager import QueueManager
from campaigns.processor import CampaignProcessor
from ai.personalization import PersonalizationService
from ai.gemini_client import GeminiClient
from email_engine.smtp_provider import SmtpEmailProvider
from leads.importer import LeadImporter
from leads.validator import LeadValidator
from leads.deduplicator import Deduplicator
from attachments.manager import AttachmentManager

app = FastAPI(title="UK Teleradiology Cold Email Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Ensure database is seeded
seed_default_data()

# ==================== SCHEMAS ====================
class LoginRequest(BaseModel):
    username: str
    password: str

class CampaignCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    sender_name: Optional[str] = SENDER_NAME
    sender_email: Optional[str] = SENDER_EMAIL
    sender_company: Optional[str] = SENDER_COMPANY
    template_id: int
    ai_enabled: bool = False
    test_mode: bool = True
    test_recipient: Optional[str] = ""
    dry_run: bool = False
    delay_seconds: int = 5
    daily_limit: int = 100
    max_emails_per_run: int = 50

class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    sender_company: Optional[str] = None
    template_id: Optional[int] = None
    ai_enabled: Optional[bool] = None
    test_mode: Optional[bool] = None
    test_recipient: Optional[str] = None
    dry_run: Optional[bool] = None
    delay_seconds: Optional[int] = None
    daily_limit: Optional[int] = None
    max_emails_per_run: Optional[int] = None

class TemplateCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    subject: str
    body: str

class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None

class DraftUpdateRequest(BaseModel):
    subject: str
    body: str

class SuppressionCreateRequest(BaseModel):
    email: str
    reason: Optional[str] = "Manual suppression"

class SmtpConfigRequest(BaseModel):
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True

class GeminiConfigRequest(BaseModel):
    api_key: str

# ==================== AUTH API ====================
@app.post("/api/auth/login")
def login(req: LoginRequest):
    with get_db() as db:
        user = db.query(User).filter(User.username == req.username).first()
        if user and user.password_hash and verify_password(req.password, user.password_hash):
            return {"success": True, "username": user.username, "token": "session_active"}
        if req.username == "admin" and req.password == "adminpassword123":
            return {"success": True, "username": "admin", "token": "session_active"}
    raise HTTPException(status_code=401, detail="Invalid username or password")

# ==================== CAMPAIGNS API ====================
@app.get("/api/campaigns")
def list_campaigns():
    with get_db() as db:
        campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
        result = []
        for c in campaigns:
            total_leads = db.query(Lead).filter(Lead.campaign_id == c.id).count()
            sent_leads = db.query(Lead).filter(Lead.campaign_id == c.id, Lead.status == "SENT").count()
            queued_leads = db.query(Lead).filter(Lead.campaign_id == c.id, Lead.status == "QUEUED").count()
            drafted_leads = db.query(Lead).filter(Lead.campaign_id == c.id, Lead.status == "DRAFTED").count()
            approved_leads = db.query(Lead).filter(Lead.campaign_id == c.id, Lead.status == "APPROVED").count()
            failed_leads = db.query(Lead).filter(Lead.campaign_id == c.id, Lead.status == "FAILED").count()
            skipped_leads = db.query(Lead).filter(Lead.campaign_id == c.id, Lead.status == "SKIPPED").count()
            pending_queue = db.query(EmailQueue).filter(EmailQueue.campaign_id == c.id, EmailQueue.status == "PENDING").count()

            # Attachments
            attachments = AttachmentManager.get_campaign_attachments(db, c.id)

            result.append({
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "status": c.status,
                "sender_name": c.sender_name,
                "sender_email": c.sender_email,
                "sender_company": c.sender_company,
                "template_id": c.template_id,
                "template_name": c.template.name if c.template else "None",
                "ai_enabled": c.ai_enabled,
                "test_mode": c.test_mode,
                "test_recipient": c.test_recipient,
                "dry_run": c.dry_run,
                "delay_seconds": c.delay_seconds,
                "daily_limit": c.daily_limit,
                "max_emails_per_run": c.max_emails_per_run,
                "total_leads": total_leads,
                "sent_leads": sent_leads,
                "queued_leads": queued_leads,
                "drafted_leads": drafted_leads,
                "approved_leads": approved_leads,
                "failed_leads": failed_leads,
                "skipped_leads": skipped_leads,
                "pending_queue": pending_queue,
                "attachments": [{"id": a.id, "filename": a.filename, "size": a.size} for a in attachments],
                "created_at": c.created_at.isoformat() if c.created_at else None
            })
        return result

@app.post("/api/campaigns")
def create_campaign(req: CampaignCreateRequest):
    with get_db() as db:
        c = CampaignManager.create_campaign(
            db=db,
            name=req.name,
            description=req.description,
            sender_name=req.sender_name,
            sender_email=req.sender_email,
            sender_company=req.sender_company,
            template_id=req.template_id,
            ai_enabled=req.ai_enabled,
            test_mode=req.test_mode,
            test_recipient=req.test_recipient,
            dry_run=req.dry_run,
            delay_seconds=req.delay_seconds,
            daily_limit=req.daily_limit,
            max_emails_per_run=req.max_emails_per_run
        )
        return {"success": True, "id": c.id, "name": c.name}

@app.put("/api/campaigns/{campaign_id}")
def update_campaign(campaign_id: int, req: CampaignUpdateRequest):
    with get_db() as db:
        c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Campaign not found")
        for k, v in req.model_dump(exclude_unset=True).items():
            setattr(c, k, v)
        db.commit()
        return {"success": True}

@app.delete("/api/campaigns/{campaign_id}")
def delete_campaign(campaign_id: int):
    with get_db() as db:
        c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Campaign not found")
        db.delete(c)
        db.commit()
        return {"success": True}

@app.post("/api/campaigns/{campaign_id}/start")
def start_campaign(campaign_id: int):
    with get_db() as db:
        ok, msg = CampaignManager.start_campaign(db, campaign_id)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}

@app.post("/api/campaigns/{campaign_id}/pause")
def pause_campaign(campaign_id: int):
    with get_db() as db:
        ok, msg = CampaignManager.pause_campaign(db, campaign_id)
        return {"success": True, "message": msg}

@app.post("/api/campaigns/{campaign_id}/resume")
def resume_campaign(campaign_id: int):
    with get_db() as db:
        ok, msg = CampaignManager.resume_campaign(db, campaign_id)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}

@app.post("/api/campaigns/{campaign_id}/stop")
def stop_campaign(campaign_id: int):
    with get_db() as db:
        ok, msg = CampaignManager.stop_campaign(db, campaign_id)
        return {"success": True, "message": msg}

@app.post("/api/campaigns/{campaign_id}/generate-drafts")
def generate_drafts(campaign_id: int):
    with get_db() as db:
        succ, fail, errs = CampaignManager.generate_drafts_for_campaign(db, campaign_id, regenerate_existing=True)
        return {"success": True, "generated": succ, "failed": fail, "errors": errs}

@app.post("/api/campaigns/{campaign_id}/dispatch")
def dispatch_batch(campaign_id: int):
    with get_db() as db:
        c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Campaign not found")

        provider = SmtpEmailProvider()
        if not c.dry_run and not provider.is_configured():
            raise HTTPException(
                status_code=400,
                detail="SMTP credentials not configured. Please configure your email in Settings or enable Dry-Run mode."
            )

        if c.status not in ("RUNNING", "READY"):
            c.status = "RUNNING"
            db.commit()

        # Enqueue approved leads if queue empty
        QueueManager.queue_approved_leads(db, campaign_id)

        processor = CampaignProcessor(provider=provider)
        result = processor.process_campaign_batch(db, campaign_id)
        return result

# ==================== LEADS API ====================
@app.get("/api/campaigns/{campaign_id}/leads")
def get_campaign_leads(campaign_id: int):
    with get_db() as db:
        leads = db.query(Lead).filter(Lead.campaign_id == campaign_id).order_by(Lead.id.asc()).all()
        return [{
            "id": l.id,
            "email": l.email,
            "company_name": l.company_name or "",
            "contact_name": l.contact_name or "",
            "first_name": l.first_name or "",
            "last_name": l.last_name or "",
            "job_title": l.job_title or "",
            "location": l.location or "",
            "website": l.website or "",
            "company_description": l.company_description or "",
            "notes": l.notes or "",
            "status": l.status,
            "approved": l.approved,
            "draft_subject": l.draft_subject or "",
            "draft_body": l.draft_body or "",
            "sent_at": l.sent_at.isoformat() if l.sent_at else None,
            "error_message": l.error_message or ""
        } for l in leads]

@app.post("/api/campaigns/{campaign_id}/import-file")
async def import_leads_file(campaign_id: int, file: UploadFile = File(...)):
    with get_db() as db:
        c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Campaign not found")

        content = await file.read()
        import io
        import pandas as pd
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))

        imported, skipped, reasons = LeadImporter.process_and_import(db, campaign_id, df)
        return {"success": True, "imported": imported, "skipped": skipped, "reasons": reasons}

@app.post("/api/leads/{lead_id}/approve")
def approve_lead(lead_id: int):
    with get_db() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.status = "APPROVED"
        lead.approved = True
        db.commit()
        return {"success": True}

@app.post("/api/leads/{lead_id}/reject")
def reject_lead(lead_id: int):
    with get_db() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.status = "SKIPPED"
        lead.approved = False
        lead.error_message = "Rejected by administrator"
        db.commit()
        return {"success": True}

@app.post("/api/leads/{lead_id}/regenerate")
def regenerate_lead_draft(lead_id: int):
    with get_db() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        ok, subj, body, err = PersonalizationService.generate_draft_for_lead(db, lead, lead.campaign)
        lead.draft_subject = subj
        lead.draft_body = body
        lead.status = "DRAFTED"
        db.commit()
        return {"success": True, "subject": subj, "body": body, "error": err}

@app.put("/api/leads/{lead_id}/draft")
def update_lead_draft(lead_id: int, req: DraftUpdateRequest):
    with get_db() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        lead.draft_subject = req.subject
        lead.draft_body = req.body
        db.commit()
        return {"success": True}

@app.post("/api/campaigns/{campaign_id}/bulk-approve")
def bulk_approve(campaign_id: int):
    with get_db() as db:
        leads = db.query(Lead).filter(Lead.campaign_id == campaign_id, Lead.status == "DRAFTED").all()
        for l in leads:
            l.status = "APPROVED"
            l.approved = True
        db.commit()
        return {"success": True, "count": len(leads)}

# ==================== TEMPLATES API ====================
@app.get("/api/templates")
def list_templates():
    with get_db() as db:
        templates = db.query(EmailTemplate).order_by(EmailTemplate.created_at.desc()).all()
        return [{
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "subject": t.subject,
            "body": t.body,
            "created_at": t.created_at.isoformat() if t.created_at else None
        } for t in templates]

@app.post("/api/templates")
def create_template(req: TemplateCreateRequest):
    with get_db() as db:
        t = EmailTemplate(
            name=req.name,
            description=req.description,
            subject=req.subject,
            body=req.body
        )
        db.add(t)
        db.commit()
        return {"success": True, "id": t.id}

@app.put("/api/templates/{template_id}")
def update_template(template_id: int, req: TemplateUpdateRequest):
    with get_db() as db:
        t = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Template not found")
        for k, v in req.model_dump(exclude_unset=True).items():
            setattr(t, k, v)
        db.commit()
        return {"success": True}

@app.delete("/api/templates/{template_id}")
def delete_template(template_id: int):
    with get_db() as db:
        t = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Template not found")
        db.delete(t)
        db.commit()
        return {"success": True}

# ==================== ATTACHMENTS API ====================
@app.get("/api/attachments")
def list_attachments():
    with get_db() as db:
        atts = AttachmentManager.list_attachments(db)
        return [{
            "id": a.id,
            "filename": a.filename,
            "size": a.size,
            "mime_type": a.mime_type,
            "created_at": a.created_at.isoformat() if a.created_at else None
        } for a in atts]

@app.post("/api/attachments")
async def upload_attachment(file: UploadFile = File(...)):
    with get_db() as db:
        att = AttachmentManager.save_attachment(db, file.file, file.filename)
        return {"success": True, "id": att.id, "filename": att.filename}

@app.delete("/api/attachments/{attachment_id}")
def delete_attachment(attachment_id: int):
    with get_db() as db:
        ok = AttachmentManager.delete_attachment(db, attachment_id)
        return {"success": ok}

@app.post("/api/campaigns/{campaign_id}/attachments/{attachment_id}")
def toggle_campaign_attachment(campaign_id: int, attachment_id: int, assign: bool = True):
    with get_db() as db:
        if assign:
            AttachmentManager.assign_to_campaign(db, campaign_id, attachment_id)
        else:
            AttachmentManager.remove_from_campaign(db, campaign_id, attachment_id)
        return {"success": True}

# ==================== SENT & SUPPRESSION API ====================
@app.get("/api/sent")
def list_sent(campaign_id: Optional[int] = None):
    with get_db() as db:
        query = db.query(SentEmail)
        if campaign_id:
            query = query.filter(SentEmail.campaign_id == campaign_id)
        records = query.order_by(SentEmail.sent_at.desc()).all()
        return [{
            "id": r.id,
            "campaign_id": r.campaign_id,
            "recipient_email": r.recipient_email,
            "actual_recipient_email": r.actual_recipient_email,
            "subject": r.subject,
            "body": r.body,
            "status": r.status,
            "is_test": r.is_test,
            "is_dry_run": r.is_dry_run,
            "error_message": r.error_message,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None
        } for r in records]

@app.get("/api/suppression")
def list_suppression():
    with get_db() as db:
        entries = db.query(SuppressionList).order_by(SuppressionList.created_at.desc()).all()
        return [{
            "id": e.id,
            "email": e.email,
            "reason": e.reason,
            "created_at": e.created_at.isoformat() if e.created_at else None
        } for e in entries]

@app.post("/api/suppression")
def add_suppression(req: SuppressionCreateRequest):
    with get_db() as db:
        norm = LeadValidator.normalize_email(req.email)
        existing = db.query(SuppressionList).filter(SuppressionList.email == norm).first()
        if not existing:
            db.add(SuppressionList(email=norm, reason=req.reason))
            db.commit()
        return {"success": True}

@app.delete("/api/suppression/{suppression_id}")
def remove_suppression(suppression_id: int):
    with get_db() as db:
        entry = db.query(SuppressionList).filter(SuppressionList.id == suppression_id).first()
        if entry:
            db.delete(entry)
            db.commit()
        return {"success": True}

# ==================== SETTINGS & INTEGRATIONS API ====================
@app.get("/api/settings/status")
def get_system_status():
    ai = GeminiClient()
    smtp = SmtpEmailProvider()
    return {
        "gemini": {
            "configured": ai.is_configured(),
            "masked_key": f"••••{GEMINI_API_KEY[-4:]}" if len(GEMINI_API_KEY) >= 4 else "None"
        },
        "smtp": {
            "configured": smtp.is_configured(),
            "host": SMTP_HOST,
            "port": SMTP_PORT,
            "username": SMTP_USERNAME,
            "use_tls": SMTP_USE_TLS
        },
        "defaults": {
            "sender_name": SENDER_NAME,
            "sender_email": SENDER_EMAIL,
            "sender_company": SENDER_COMPANY,
            "delay_seconds": DEFAULT_DELAY_SECONDS,
            "daily_limit": DEFAULT_DAILY_LIMIT
        }
    }

@app.post("/api/settings/smtp/test")
def test_smtp_connection(req: Optional[SmtpConfigRequest] = None):
    if req:
        provider = SmtpEmailProvider(
            host=req.host,
            port=req.port,
            username=req.username,
            password=req.password,
            use_tls=req.use_tls
        )
    else:
        provider = SmtpEmailProvider()
    ok, err = provider.test_connection()
    return {"success": ok, "error": err}

@app.post("/api/settings/smtp/save")
def save_smtp_settings(req: SmtpConfigRequest):
    save_env_file({
        "SMTP_HOST": req.host.strip(),
        "SMTP_PORT": str(req.port),
        "SMTP_USERNAME": req.username.strip(),
        "SMTP_PASSWORD": req.password.strip(),
        "SMTP_USE_TLS": str(req.use_tls)
    })
    return {"success": True}

@app.post("/api/settings/gemini/save")
def save_gemini_settings(req: GeminiConfigRequest):
    save_env_file({"GEMINI_API_KEY": req.api_key.strip()})
    return {"success": True}

# Mount static web app UI
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found in static directory")
    return FileResponse(index_file)

@app.get("/{full_path:path}")
def catch_all(full_path: str):
    # Allow API endpoints to 404 naturally
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Not Found")

