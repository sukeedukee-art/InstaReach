import streamlit as st
import pandas as pd
from datetime import datetime
from database.db import get_db
from database.models import Campaign, Lead
from ai.personalization import PersonalizationService

def render_drafts():
    st.title("✉️ Draft Review & Approval")
    st.markdown("Inspect, edit, regenerate, approve, or reject personalized email drafts before sending.")

    with get_db() as db:
        campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
        if not campaigns:
            st.warning("No campaigns available. Create one in the Campaigns page.")
            return

        campaign_map = {f"{c.name} (ID: {c.id})": c.id for c in campaigns}
        selected_label = st.selectbox("Select Campaign for Draft Review:", list(campaign_map.keys()))
        campaign_id = campaign_map[selected_label]
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

        # Status filter tabs
        filter_status = st.radio(
            "Filter Leads by Status:",
            ["ALL", "DRAFTED", "APPROVED", "NEW", "QUEUED", "SENT", "FAILED", "SKIPPED"],
            horizontal=True
        )

        query = db.query(Lead).filter(Lead.campaign_id == campaign_id)
        if filter_status != "ALL":
            query = query.filter(Lead.status == filter_status)

        leads = query.order_by(Lead.id.asc()).all()

        # Bulk Actions Toolbar
        st.markdown("---")
        st.subheader("🛠️ Bulk Actions")
        col_b1, col_b2, col_b3 = st.columns(3)

        with col_b1:
            if st.button("✅ Approve ALL 'Drafted' Leads", use_container_width=True):
                drafted_leads = db.query(Lead).filter(
                    Lead.campaign_id == campaign_id,
                    Lead.status == "DRAFTED"
                ).all()
                for l in drafted_leads:
                    l.status = "APPROVED"
                    l.approved = True
                db.commit()
                st.success(f"Approved {len(drafted_leads)} leads!")
                st.rerun()

        with col_b2:
            if st.button("✨ Regenerate ALL Drafts", use_container_width=True):
                with st.spinner("Regenerating all drafts..."):
                    all_leads = db.query(Lead).filter(Lead.campaign_id == campaign_id).all()
                    for l in all_leads:
                        ok, subj, body, err = PersonalizationService.generate_draft_for_lead(db, l, campaign)
                        l.draft_subject = subj
                        l.draft_body = body
                        l.status = "DRAFTED"
                    db.commit()
                    st.success(f"Regenerated {len(all_leads)} drafts!")
                    st.rerun()

        with col_b3:
            if st.button("❌ Reject / Reset ALL to New", use_container_width=True):
                all_leads = db.query(Lead).filter(Lead.campaign_id == campaign_id).all()
                for l in all_leads:
                    l.status = "NEW"
                    l.approved = False
                db.commit()
                st.warning(f"Reset {len(all_leads)} leads to NEW.")
                st.rerun()

        st.markdown("---")
        st.subheader(f"📋 Individual Drafts ({len(leads)} leads)")

        if not leads:
            st.info("No leads matching the current status filter.")
            return

        for lead in leads:
            status_emoji = {
                "NEW": "🆕",
                "DRAFTED": "📝",
                "APPROVED": "✅",
                "QUEUED": "⏳",
                "SENDING": "📤",
                "SENT": "📬",
                "FAILED": "❌",
                "SKIPPED": "⏭️"
            }.get(lead.status, "📄")

            header_label = f"{status_emoji} [{lead.status}] {lead.contact_name or 'Lead'} - {lead.company_name or 'Organisation'} ({lead.email})"
            with st.expander(header_label, expanded=(lead.status in ["DRAFTED", "NEW"])):
                col_info1, col_info2 = st.columns([1, 2])

                with col_info1:
                    st.markdown("##### Lead Details")
                    st.write(f"**Contact:** {lead.contact_name or '-'}")
                    st.write(f"**Role:** {lead.job_title or '-'}")
                    st.write(f"**Company:** {lead.company_name or '-'}")
                    st.write(f"**Location:** {lead.location or '-'}")
                    st.write(f"**Website:** {lead.website or '-'}")
                    if lead.company_description:
                        st.write(f"**Description:** {lead.company_description}")
                    if lead.notes:
                        st.write(f"**Notes:** {lead.notes}")
                    if lead.error_message:
                        st.error(f"**Issue/Error:** {lead.error_message}")

                with col_info2:
                    st.markdown("##### Draft Subject & Body")
                    edit_subject = st.text_input(
                        "Subject Line",
                        value=lead.draft_subject or "",
                        key=f"subj_{lead.id}"
                    )
                    edit_body = st.text_area(
                        "Email Body",
                        value=lead.draft_body or "",
                        height=220,
                        key=f"body_{lead.id}"
                    )

                    col_act1, col_act2, col_act3, col_act4 = st.columns(4)

                    with col_act1:
                        if st.button("💾 Save Edit", key=f"save_{lead.id}"):
                            lead.draft_subject = edit_subject
                            lead.draft_body = edit_body
                            db.commit()
                            st.success("Draft updated.")
                            st.rerun()

                    with col_act2:
                        if st.button("✅ Approve", key=f"appr_{lead.id}", disabled=(lead.status == "APPROVED")):
                            lead.draft_subject = edit_subject
                            lead.draft_body = edit_body
                            lead.status = "APPROVED"
                            lead.approved = True
                            db.commit()
                            st.success("Lead approved!")
                            st.rerun()

                    with col_act3:
                        if st.button("❌ Reject", key=f"rej_{lead.id}"):
                            lead.status = "SKIPPED"
                            lead.approved = False
                            lead.error_message = "Rejected by administrator during draft review"
                            db.commit()
                            st.warning("Draft rejected.")
                            st.rerun()

                    with col_act4:
                        if st.button("✨ Regenerate", key=f"regen_{lead.id}"):
                            with st.spinner("Regenerating..."):
                                ok, subj, body, err = PersonalizationService.generate_draft_for_lead(
                                    db, lead, campaign
                                )
                                lead.draft_subject = subj
                                lead.draft_body = body
                                lead.status = "DRAFTED"
                                db.commit()
                                st.rerun()
