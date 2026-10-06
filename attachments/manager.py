import logging
import mimetypes
import uuid
from pathlib import Path
from typing import BinaryIO, List, Optional
from sqlalchemy.orm import Session
from config.settings import ATTACHMENTS_DIR
from database.models import Attachment, CampaignAttachment

logger = logging.getLogger(__name__)

# Permitted MIME types / extensions for cold email outreach security
ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain"
}

class AttachmentManager:
    """Manages secure file uploads, association with campaigns, and cleanup."""

    @staticmethod
    def is_allowed_file(filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in ALLOWED_EXTENSIONS

    @classmethod
    def save_attachment(cls, db: Session, file_obj: BinaryIO, original_filename: str) -> Attachment:
        """
        Saves uploaded file securely using a sanitized UUID-based filename.
        Stores metadata in the database.
        """
        clean_name = Path(original_filename).name # Strips directory traversal attempts
        ext = Path(clean_name).suffix.lower()

        if not cls.is_allowed_file(clean_name):
            raise ValueError(f"File type '{ext}' is not permitted. Allowed: {', '.join(ALLOWED_EXTENSIONS.keys())}")

        # Unique storage filename
        stored_filename = f"{uuid.uuid4().hex}_{clean_name}"
        destination_path = ATTACHMENTS_DIR / stored_filename

        content = file_obj.read()
        file_size = len(content)

        with open(destination_path, "wb") as f:
            f.write(content)

        mime_type = ALLOWED_EXTENSIONS.get(ext) or mimetypes.guess_type(clean_name)[0] or "application/octet-stream"

        attachment = Attachment(
            filename=clean_name,
            path=str(destination_path),
            mime_type=mime_type,
            size=file_size
        )
        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        logger.info(f"Saved attachment '{clean_name}' (ID: {attachment.id}) to {destination_path}")
        return attachment

    @staticmethod
    def list_attachments(db: Session) -> List[Attachment]:
        """Returns all attachments stored in system."""
        return db.query(Attachment).order_by(Attachment.created_at.desc()).all()

    @staticmethod
    def rename_attachment(db: Session, attachment_id: int, new_name: str) -> Optional[Attachment]:
        """Renames the display filename for an attachment."""
        attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
        if attachment:
            clean_name = Path(new_name).name
            attachment.filename = clean_name
            db.commit()
            db.refresh(attachment)
            logger.info(f"Renamed attachment ID {attachment_id} to '{clean_name}'")
        return attachment

    @staticmethod
    def delete_attachment(db: Session, attachment_id: int) -> bool:
        """Deletes attachment from database and removes file from disk."""
        attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
        if not attachment:
            return False

        file_path = Path(attachment.path)
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Could not delete physical file {file_path}: {e}")

        db.delete(attachment)
        db.commit()
        logger.info(f"Deleted attachment ID {attachment_id}")
        return True

    @staticmethod
    def assign_to_campaign(db: Session, campaign_id: int, attachment_id: int):
        """Attaches an existing attachment to a campaign."""
        existing = db.query(CampaignAttachment).filter(
            CampaignAttachment.campaign_id == campaign_id,
            CampaignAttachment.attachment_id == attachment_id
        ).first()

        if not existing:
            ca = CampaignAttachment(campaign_id=campaign_id, attachment_id=attachment_id)
            db.add(ca)
            db.commit()
            logger.info(f"Attached file ID {attachment_id} to Campaign {campaign_id}")

    @staticmethod
    def remove_from_campaign(db: Session, campaign_id: int, attachment_id: int):
        """Removes an attachment from a campaign selection."""
        existing = db.query(CampaignAttachment).filter(
            CampaignAttachment.campaign_id == campaign_id,
            CampaignAttachment.attachment_id == attachment_id
        ).first()

        if existing:
            db.delete(existing)
            db.commit()
            logger.info(f"Removed attachment ID {attachment_id} from Campaign {campaign_id}")

    @staticmethod
    def get_campaign_attachments(db: Session, campaign_id: int) -> List[Attachment]:
        """Fetches all attachments currently selected for a campaign."""
        associations = db.query(CampaignAttachment).filter(
            CampaignAttachment.campaign_id == campaign_id
        ).all()
        return [assoc.attachment for assoc in associations if assoc.attachment]
