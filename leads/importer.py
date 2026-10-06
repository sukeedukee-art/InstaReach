import logging
from io import BytesIO
from typing import BinaryIO, Dict, List, Tuple, Union
import pandas as pd
from sqlalchemy.orm import Session
from database.models import Lead
from leads.validator import LeadValidator
from leads.deduplicator import Deduplicator

logger = logging.getLogger(__name__)

# Standard column normalization dictionary
COLUMN_MAPPINGS = {
    "email": ["email", "e-mail", "email address", "e-mail address", "contact email", "primary email", "work email", "e_mail", "e mail"],
    "company_name": ["company", "company name", "organisation", "organization", "organisation name", "organization name", "hospital", "clinic", "trust", "account name", "client"],
    "contact_name": ["contact name", "contact", "full name", "name", "person", "lead name"],
    "first_name": ["first name", "firstname", "given name", "first", "forename"],
    "last_name": ["last name", "lastname", "surname", "family name", "last"],
    "job_title": ["job title", "job", "title", "position", "role", "designation"],
    "website": ["website", "url", "web", "domain", "company website", "site"],
    "location": ["location", "city", "region", "country", "address", "area", "county", "town"],
    "company_description": ["company description", "description", "about", "overview", "specialty"],
    "notes": ["notes", "note", "comments", "extra", "context"]
}

class LeadImporter:
    """Handles importing CSV and XLSX leads files, auto-detecting schema and inserting into database."""

    @staticmethod
    def read_file(file_obj: Union[BinaryIO, BytesIO, str], filename: str) -> pd.DataFrame:
        """Reads CSV or Excel file into a pandas DataFrame."""
        if filename.lower().endswith(".csv"):
            return pd.read_csv(file_obj)
        elif filename.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(file_obj)
        else:
            raise ValueError("Unsupported file format. Please upload a .csv or .xlsx file.")

    @staticmethod
    def detect_column_mappings(df: pd.DataFrame) -> Dict[str, str]:
        """
        Automatically detects matching columns in the DataFrame.
        Returns a dictionary: {standard_field_name: matched_column_name_in_df}
        """
        matched: Dict[str, str] = {}
        cleaned_df_cols = {col: str(col).strip().lower() for col in df.columns}

        for standard_field, aliases in COLUMN_MAPPINGS.items():
            for alias in aliases:
                for orig_col, clean_col in cleaned_df_cols.items():
                    if clean_col == alias:
                        matched[standard_field] = orig_col
                        break
                if standard_field in matched:
                    break

        return matched

    @classmethod
    def process_and_import(
        cls,
        db: Session,
        campaign_id: int,
        df: pd.DataFrame,
        custom_mapping: Dict[str, str] = None
    ) -> Tuple[int, int, List[str]]:
        """
        Imports leads into the database for a campaign using detected or custom column mappings.
        Returns (imported_count, skipped_count, list_of_reasons).
        """
        mapping = custom_mapping or cls.detect_column_mappings(df)

        if "email" not in mapping or not mapping["email"]:
            raise ValueError("An 'Email' column is required to import leads.")

        email_col = mapping["email"]
        imported_count = 0
        skipped_count = 0
        reasons: List[str] = []

        for index, row in df.iterrows():
            raw_email = row.get(email_col)
            clean_email = LeadValidator.clean_text(raw_email)

            if not LeadValidator.is_valid_email(clean_email):
                skipped_count += 1
                reasons.append(f"Row {index + 1}: Invalid email '{clean_email}'")
                continue

            normalized_email = LeadValidator.normalize_email(clean_email)

            # Check if this email is already loaded into this specific campaign
            existing_lead = db.query(Lead).filter(
                Lead.campaign_id == campaign_id,
                Lead.email == normalized_email
            ).first()

            if existing_lead:
                skipped_count += 1
                reasons.append(f"Row {index + 1}: Email '{normalized_email}' already exists in this campaign")
                continue

            # Extract fields
            def get_val(field: str) -> str:
                col = mapping.get(field)
                if col and col in row:
                    return LeadValidator.clean_text(row[col])
                return ""

            contact_name = get_val("contact_name")
            first_name = get_val("first_name")
            last_name = get_val("last_name")

            # Infer first/last name if contact_name exists but first/last do not
            if contact_name and not first_name and not last_name:
                parts = contact_name.split(None, 1)
                first_name = parts[0]
                if len(parts) > 1:
                    last_name = parts[1]
            elif (first_name or last_name) and not contact_name:
                contact_name = f"{first_name} {last_name}".strip()

            lead = Lead(
                campaign_id=campaign_id,
                email=normalized_email,
                company_name=get_val("company_name"),
                contact_name=contact_name,
                first_name=first_name,
                last_name=last_name,
                job_title=get_val("job_title"),
                website=get_val("website"),
                location=get_val("location"),
                company_description=get_val("company_description"),
                notes=get_val("notes"),
                status="NEW"
            )
            db.add(lead)
            imported_count += 1

        db.commit()
        logger.info(f"Campaign {campaign_id}: Imported {imported_count} leads, skipped {skipped_count}.")
        return imported_count, skipped_count, reasons
