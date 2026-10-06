import streamlit as st
import pandas as pd
from datetime import datetime
from database.db import get_db
from database.models import Campaign, EmailTemplate, Attachment, CampaignAttachment
from attachments.manager import AttachmentManager
from config.settings import SENDER_NAME, SENDER_EMAIL, SENDER_COMPANY, DEFAULT_DELAY_SECONDS, DEFAULT_DAILY_LIMIT

def render_campaigns():
    st.title("🎯 Campaign Manager")
    st.markdown("Create and configure targeted cold email outreach campaigns.")

    with get_db() as db:
        templates = db.query(EmailTemplate).all()
        all_attachments = db.query(Attachment).all()

        tab_create, tab_manage = st.tabs(["➕ Create Campaign", "⚙️ Manage Existing Campaigns"])

        with tab_create:
            with st.form("create_campaign_form"):
                name = st.text_input("Campaign Name *", placeholder="e.g. Q4 UK NHS Trust Diagnostic Outreach")
                description = st.text_area("Description / Clinical Context", placeholder="e.g. Outreach regarding overnight MRI/CT reporting capacity & 1-hour urgent SLA")

                col_s1, col_s2, col_s3 = st.columns(3)
                with col_s1:
                    sender_name = st.text_input("Sender Name", value=SENDER_NAME)
                with col_s2:
                    sender_email = st.text_input("Sender Email", value=SENDER_EMAIL)
                with col_s3:
                    sender_company = st.text_input("Sender Company", value=SENDER_COMPANY)

                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    template_map = {f"{t.name} (ID: {t.id})": t.id for t in templates}
                    if templates:
                        selected_tpl_name = st.selectbox("Base Email Template *", list(template_map.keys()))
                        template_id = template_map[selected_tpl_name]
                    else:
                        st.warning("No templates found! Go to the Templates page to create one.")
                        template_id = None

                with col_t2:
                    ai_enabled = st.checkbox("✨ Enable Gemini AI Personalization", value=False, help="Uses Gemini to personalize the subject and body based on lead information and facts.")

                st.markdown("---")
                st.subheader("🛡️ Safety & Safeguards")
                col_safe1, col_safe2 = st.columns(2)
                with col_safe1:
                    test_mode = st.checkbox("🧪 Test Mode (Recommended)", value=True, help="Redirects ALL outgoing emails to the test recipient address below.")
                    test_recipient = st.text_input("Test Recipient Address", value="test-review@uk-teleradiology.co.uk")
                with col_safe2:
                    dry_run = st.checkbox("📄 Dry-Run Simulation", value=False, help="Simulate email generation and queue processing without transmitting any SMTP packets.")

                col_rate1, col_rate2, col_rate3 = st.columns(3)
                with col_rate1:
                    delay_seconds = st.number_input("Delay Between Sends (Seconds)", min_value=0, max_value=300, value=DEFAULT_DELAY_SECONDS)
                with col_rate2:
                    daily_limit = st.number_input("Daily Email Limit", min_value=1, max_value=1000, value=DEFAULT_DAILY_LIMIT)
                with col_rate3:
                    max_emails_per_run = st.number_input("Max Emails Per Batch Run", min_value=1, max_value=200, value=50)

                submitted = st.form_submit_button("🚀 Create Campaign", type="primary")
                if submitted:
                    if not name.strip():
                        st.error("Please enter a campaign name.")
                    elif not template_id:
                        st.error("Please select a valid email template.")
                    else:
                        new_campaign = Campaign(
                            name=name.strip(),
                            description=description.strip(),
                            sender_name=sender_name.strip(),
                            sender_email=sender_email.strip(),
                            sender_company=sender_company.strip(),
                            template_id=template_id,
                            ai_enabled=ai_enabled,
                            test_mode=test_mode,
                            test_recipient=test_recipient.strip(),
                            dry_run=dry_run,
                            delay_seconds=delay_seconds,
                            daily_limit=daily_limit,
                            max_emails_per_run=max_emails_per_run,
                            status="DRAFT"
                        )
                        db.add(new_campaign)
                        db.commit()
                        st.success(f"Campaign '{name}' created successfully!")
                        st.rerun()

        with tab_manage:
            campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
            if not campaigns:
                st.info("No campaigns created yet.")
            else:
                for camp in campaigns:
                    with st.expander(f"📌 {camp.name} (Status: {camp.status})", expanded=False):
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            new_name = st.text_input("Name", value=camp.name, key=f"camp_name_{camp.id}")
                            new_desc = st.text_area("Description", value=camp.description or "", key=f"camp_desc_{camp.id}")
                            new_sname = st.text_input("Sender Name", value=camp.sender_name or "", key=f"camp_sname_{camp.id}")
                            new_semail = st.text_input("Sender Email", value=camp.sender_email or "", key=f"camp_semail_{camp.id}")

                        with col_e2:
                            new_ai = st.checkbox("AI Personalization", value=camp.ai_enabled, key=f"camp_ai_{camp.id}")
                            new_test = st.checkbox("Test Mode", value=camp.test_mode, key=f"camp_test_{camp.id}")
                            new_test_rec = st.text_input("Test Recipient", value=camp.test_recipient or "", key=f"camp_test_rec_{camp.id}")
                            new_dry = st.checkbox("Dry Run", value=camp.dry_run, key=f"camp_dry_{camp.id}")
                            new_delay = st.number_input("Delay (s)", value=camp.delay_seconds, key=f"camp_delay_{camp.id}")

                        # Manage Attachments for this Campaign
                        st.markdown("#### 📎 Campaign Attachments")
                        current_attachments = AttachmentManager.get_campaign_attachments(db, camp.id)
                        current_att_ids = {a.id for a in current_attachments}

                        if all_attachments:
                            st.write("Select attachments to include in every email sent from this campaign:")
                            for att in all_attachments:
                                is_selected = att.id in current_att_ids
                                checked = st.checkbox(f"{att.filename} ({round(att.size / 1024, 1)} KB)", value=is_selected, key=f"att_chk_{camp.id}_{att.id}")
                                if checked and not is_selected:
                                    AttachmentManager.assign_to_campaign(db, camp.id, att.id)
                                elif not checked and is_selected:
                                    AttachmentManager.remove_from_campaign(db, camp.id, att.id)
                        else:
                            st.caption("No attachments available in the system. Upload some in the Attachments page.")

                        st.markdown("---")
                        col_save, col_del = st.columns([1, 4])
                        with col_save:
                            if st.button("💾 Save Changes", key=f"save_camp_{camp.id}"):
                                camp.name = new_name
                                camp.description = new_desc
                                camp.sender_name = new_sname
                                camp.sender_email = new_semail
                                camp.ai_enabled = new_ai
                                camp.test_mode = new_test
                                camp.test_recipient = new_test_rec
                                camp.dry_run = new_dry
                                camp.delay_seconds = new_delay
                                db.commit()
                                st.success("Campaign settings updated.")
                                st.rerun()
                        with col_del:
                            if st.button("🗑️ Delete Campaign", key=f"del_camp_{camp.id}"):
                                db.delete(camp)
                                db.commit()
                                st.warning(f"Deleted campaign {camp.name}")
                                st.rerun()
