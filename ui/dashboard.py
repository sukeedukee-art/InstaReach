import streamlit as st
import pandas as pd
from datetime import datetime
from database.db import get_db
from database.models import Campaign, Lead, EmailQueue, SentEmail
from campaigns.campaign_manager import CampaignManager
from campaigns.processor import CampaignProcessor
from campaigns.queue_manager import QueueManager

def render_dashboard():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%); padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 2rem; color: white;">
        <h1 style="margin: 0; font-size: 2.2rem; font-weight: 700; color: #f8fafc;">UK Teleradiology Cold Email Agent</h1>
        <p style="margin-top: 0.5rem; margin-bottom: 0; font-size: 1.05rem; color: #cbd5e1;">
            Autonomous, compliant B2B clinical outreach and capacity reporting campaigns for UK diagnostic imaging providers.
        </p>
    </div>
    """, unsafe_allow_html=True)

    with get_db() as db:
        campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()

        if not campaigns:
            st.info("No campaigns found. Head over to the **Campaigns** tab in the sidebar to create your first outreach campaign!")
            return

        # Campaign Selector
        campaign_map = {f"{c.id}: {c.name} ({c.status})": c.id for c in campaigns}
        selected_label = st.selectbox("Select Active Campaign for Monitoring & Controls:", list(campaign_map.keys()))
        selected_campaign_id = campaign_map[selected_label]
        campaign = db.query(Campaign).filter(Campaign.id == selected_campaign_id).first()

        # Status & Alerts Banner
        col_banner1, col_banner2 = st.columns([2, 1])
        with col_banner1:
            status_colors = {
                "DRAFT": "#64748b",
                "READY": "#0284c7",
                "RUNNING": "#16a34a",
                "PAUSED": "#d97706",
                "STOPPED": "#dc2626",
                "COMPLETED": "#059669"
            }
            bg = status_colors.get(campaign.status, "#64748b")
            st.markdown(f"""
            <div style="background-color: {bg}; color: white; padding: 0.6rem 1.2rem; border-radius: 8px; font-weight: 600; display: inline-block;">
                Campaign Status: {campaign.status}
            </div>
            """, unsafe_allow_html=True)

            if campaign.test_mode:
                st.warning(f"⚠️ **TEST MODE ENABLED** — All outgoing emails are safely redirected to: `{campaign.test_recipient or 'Configured Test Email'}`")
            if campaign.dry_run:
                st.info("ℹ️ **DRY RUN ENABLED** — System will simulate and log queue transitions without dispatching emails.")

        with col_banner2:
            st.write(f"**Sender:** {campaign.sender_name or 'Dr. Alistair Vance'}")
            st.write(f"**AI Personalization:** {'✨ Active (Gemini)' if campaign.ai_enabled else '📄 Template Mode'}")

        st.markdown("---")

        # Metric Cards Calculation
        total_leads = db.query(Lead).filter(Lead.campaign_id == campaign.id).count()
        leads_new = db.query(Lead).filter(Lead.campaign_id == campaign.id, Lead.status == "NEW").count()
        leads_drafted = db.query(Lead).filter(Lead.campaign_id == campaign.id, Lead.status == "DRAFTED").count()
        leads_approved = db.query(Lead).filter(Lead.campaign_id == campaign.id, Lead.status == "APPROVED").count()
        leads_queued = db.query(Lead).filter(Lead.campaign_id == campaign.id, Lead.status == "QUEUED").count()
        leads_sent = db.query(Lead).filter(Lead.campaign_id == campaign.id, Lead.status == "SENT").count()
        leads_failed = db.query(Lead).filter(Lead.campaign_id == campaign.id, Lead.status == "FAILED").count()
        leads_skipped = db.query(Lead).filter(Lead.campaign_id == campaign.id, Lead.status == "SKIPPED").count()

        # Metrics Row
        m1, m2, m3, m4, m5, m6, m7, m8 = st.columns(8)
        m1.metric("Total Leads", total_leads)
        m2.metric("New", leads_new)
        m3.metric("Drafted", leads_drafted)
        m4.metric("Approved", leads_approved)
        m5.metric("Queued", leads_queued)
        m6.metric("Sent", leads_sent)
        m7.metric("Failed", leads_failed)
        m8.metric("Skipped", leads_skipped)

        # Progress Bar
        completed_count = leads_sent + leads_failed + leads_skipped
        progress_val = completed_count / total_leads if total_leads > 0 else 0.0
        st.progress(progress_val, text=f"Campaign Dispatch Progress: {completed_count}/{total_leads} ({int(progress_val * 100)}%)")

        st.markdown("### 🎮 Campaign Control Centre")
        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            if st.button("✨ Generate Drafts", use_container_width=True, help="Generates draft subject and body for un-drafted leads."):
                with st.spinner("Generating drafts..."):
                    succ, fail, errs = CampaignManager.generate_drafts_for_campaign(db, campaign.id)
                    st.success(f"Generated {succ} drafts!")
                    if fail:
                        st.warning(f"{fail} drafts had warnings or fallbacks.")
                    st.rerun()

        with c2:
            start_disabled = campaign.status == "RUNNING"
            if st.button("🚀 Start / Enqueue", use_container_width=True, disabled=start_disabled):
                # Queue approved leads and set campaign to RUNNING
                q_count, sk_count, q_reasons = QueueManager.queue_approved_leads(db, campaign.id)
                CampaignManager.start_campaign(db, campaign.id)
                st.success(f"Campaign started! {q_count} leads queued.")
                st.rerun()

        with c3:
            pause_disabled = campaign.status != "RUNNING"
            if st.button("⏸️ Pause Campaign", use_container_width=True, disabled=pause_disabled):
                CampaignManager.pause_campaign(db, campaign.id)
                st.warning("Campaign paused.")
                st.rerun()

        with c4:
            resume_disabled = campaign.status != "PAUSED"
            if st.button("▶️ Resume Campaign", use_container_width=True, disabled=resume_disabled):
                CampaignManager.resume_campaign(db, campaign.id)
                st.success("Campaign resumed.")
                st.rerun()

        with c5:
            # Stop button with confirmation
            with st.popover("🛑 Stop Campaign", use_container_width=True):
                st.write("Are you sure you want to stop this campaign? Pending queue items will be cancelled and untouched leads preserved.")
                if st.button("Confirm STOP Campaign", type="primary"):
                    CampaignManager.stop_campaign(db, campaign.id)
                    st.error("Campaign has been stopped.")
                    st.rerun()

        # Batch Processor Trigger
        st.markdown("---")
        st.subheader("⚡ Queue Dispatch Runner")
        st.write("Execute sending batch for queued leads according to campaign delay and pacing settings:")

        pending_in_queue = db.query(EmailQueue).filter(
            EmailQueue.campaign_id == campaign.id,
            EmailQueue.status == "PENDING"
        ).count()

        col_proc1, col_proc2 = st.columns([2, 1])
        with col_proc1:
            st.info(f"**{pending_in_queue}** pending messages waiting in dispatch queue.")
        with col_proc2:
            if st.button("⚡ Dispatch Next Batch", type="primary", use_container_width=True, disabled=(pending_in_queue == 0 or campaign.status not in ("RUNNING", "READY"))):
                from email_engine.smtp_provider import SmtpEmailProvider
                test_prov = SmtpEmailProvider()
                
                # Check if SMTP is configured (unless in Dry Run)
                if not campaign.dry_run and not test_prov.is_configured():
                    st.error("❌ **Cannot send emails**: SMTP credentials (Username or Password) are not configured! Please go to **Settings** in the sidebar to configure your email credentials, or enable **Dry-Run** on the campaign.")
                else:
                    if campaign.status != "RUNNING":
                        campaign.status = "RUNNING"
                        db.commit()

                    prog_bar = st.progress(0, text="Initializing dispatch...")
                    status_text = st.empty()

                    def update_progress(current, total, msg):
                        pct = current / total if total > 0 else 1.0
                        prog_bar.progress(pct, text=f"Processing {current}/{total}: {msg}")
                        status_text.write(f"`{msg}`")

                    processor = CampaignProcessor(provider=test_prov)
                    result = processor.process_campaign_batch(
                        db,
                        campaign.id,
                        progress_callback=update_progress
                    )
                    st.success(result.get("message", "Batch processed."))
                    st.rerun()

        # Recent Activity Log
        st.markdown("---")
        st.subheader("📋 Recent Outgoing Emails")
        recent_sent = db.query(SentEmail).filter(SentEmail.campaign_id == campaign.id).order_by(SentEmail.sent_at.desc()).limit(10).all()
        if recent_sent:
            data = []
            for item in recent_sent:
                data.append({
                    "Timestamp": item.sent_at.strftime("%Y-%m-%d %H:%M:%S") if item.sent_at else "-",
                    "Recipient": item.recipient_email,
                    "Delivered To": item.actual_recipient_email,
                    "Subject": item.subject,
                    "Status": item.status,
                    "Test": "Yes" if item.is_test else "No",
                    "Dry Run": "Yes" if item.is_dry_run else "No",
                    "Error": item.error_message or "None"
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.write("No emails dispatched yet.")
