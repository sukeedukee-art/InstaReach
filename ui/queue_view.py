import streamlit as st
import pandas as pd
from database.db import get_db
from database.models import EmailQueue, Campaign

def render_queue():
    st.title("⏳ Email Sending Queue")
    st.markdown("Real-time inspection of staged, in-flight, and completed email queue jobs.")

    with get_db() as db:
        campaigns = db.query(Campaign).all()
        camp_map = {"All Campaigns": None}
        for c in campaigns:
            camp_map[f"{c.name} (ID: {c.id})"] = c.id

        selected_camp = st.selectbox("Filter Queue by Campaign:", list(camp_map.keys()))
        selected_id = camp_map[selected_camp]

        query = db.query(EmailQueue)
        if selected_id:
            query = query.filter(EmailQueue.campaign_id == selected_id)

        queue_items = query.order_by(EmailQueue.scheduled_at.desc()).all()

        col_q1, col_q2, col_q3, col_q4 = st.columns(4)
        pending = sum(1 for q in queue_items if q.status == "PENDING")
        sending = sum(1 for q in queue_items if q.status == "SENDING")
        sent = sum(1 for q in queue_items if q.status == "SENT")
        failed = sum(1 for q in queue_items if q.status == "FAILED")

        col_q1.metric("Pending Dispatch", pending)
        col_q2.metric("In-Flight (Sending)", sending)
        col_q3.metric("Delivered (Sent)", sent)
        col_q4.metric("Failed / Errors", failed)

        st.markdown("---")
        if not queue_items:
            st.info("The dispatch queue is currently empty.")
            return

        data = []
        for q in queue_items:
            lead = q.lead
            data.append({
                "Queue ID": q.id,
                "Campaign ID": q.campaign_id,
                "Lead Email": lead.email if lead else "N/A",
                "Recipient Name": lead.contact_name if lead else "N/A",
                "Status": q.status,
                "Attempts": q.attempts,
                "Scheduled At": q.scheduled_at.strftime("%Y-%m-%d %H:%M:%S") if q.scheduled_at else "-",
                "Sent At": q.sent_at.strftime("%Y-%m-%d %H:%M:%S") if q.sent_at else "-",
                "Error": q.last_error or "-"
            })

        st.dataframe(pd.DataFrame(data), use_container_width=True)

        col_clr1, col_clr2 = st.columns([1, 4])
        with col_clr1:
            if st.button("🔄 Refresh Queue"):
                st.rerun()
