import streamlit as st
import pandas as pd
from database.db import get_db
from database.models import SentEmail, Campaign

def render_sent():
    st.title("📬 Sent & Dispatched Emails")
    st.markdown("Complete audit log of all outgoing B2B outreach messages with delivery status and payload records.")

    with get_db() as db:
        campaigns = db.query(Campaign).all()
        camp_map = {"All Campaigns": None}
        for c in campaigns:
            camp_map[f"{c.name} (ID: {c.id})"] = c.id

        selected_camp = st.selectbox("Filter Sent Logs by Campaign:", list(camp_map.keys()))
        selected_id = camp_map[selected_camp]

        query = db.query(SentEmail)
        if selected_id:
            query = query.filter(SentEmail.campaign_id == selected_id)

        sent_records = query.order_by(SentEmail.sent_at.desc()).all()

        if not sent_records:
            st.info("No sent email records logged yet.")
            return

        st.markdown(f"**Total Sent Records Logged:** {len(sent_records)}")

        # Table summary
        summary_data = []
        for s in sent_records:
            summary_data.append({
                "ID": s.id,
                "Sent At": s.sent_at.strftime("%Y-%m-%d %H:%M:%S") if s.sent_at else "-",
                "Intended Lead": s.recipient_email,
                "Actual Destination": s.actual_recipient_email,
                "Subject": s.subject,
                "Status": s.status,
                "Test Mode": "🧪 Yes" if s.is_test else "No",
                "Dry Run": "📄 Yes" if s.is_dry_run else "No",
                "Error": s.error_message or "None"
            })
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

        st.markdown("---")
        st.subheader("🔍 Message Content Inspector")
        rec_ids = [s.id for s in sent_records]
        selected_rec_id = st.selectbox("Inspect Individual Dispatched Email Payload:", rec_ids)
        target = db.query(SentEmail).filter(SentEmail.id == selected_rec_id).first()

        if target:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.write(f"**Intended Recipient:** `{target.recipient_email}`")
                st.write(f"**Dispatched To:** `{target.actual_recipient_email}`")
                st.write(f"**Delivery Timestamp:** {target.sent_at}")
                st.write(f"**Status:** {target.status}")
                if target.error_message:
                    st.error(f"**Error Details:** {target.error_message}")

            with col2:
                st.write(f"**Subject:** `{target.subject}`")
                st.markdown(f"""
                <div style="background-color: #f8fafc; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0; white-space: pre-wrap; font-family: sans-serif; font-size: 0.95rem; color: #1e293b;">
{target.body}
                </div>
                """, unsafe_allow_html=True)
