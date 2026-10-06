import streamlit as st
import pandas as pd
from datetime import datetime
from database.db import get_db
from database.models import SuppressionList
from leads.validator import LeadValidator

def render_suppression():
    st.title("🛡️ Unsubscribe & Suppression List")
    st.markdown("Maintain strict compliance by preventing outreach to opted-out or suppressed organizations and individuals.")

    with get_db() as db:
        tab_list, tab_add = st.tabs(["📋 Suppressed Contacts", "➕ Add Email to Suppression List"])

        with tab_add:
            with st.form("add_suppression_form"):
                email_input = st.text_input("Email Address to Suppress *", placeholder="optout@nhs-trust.co.uk")
                reason_input = st.text_input("Reason / Notes", value="Unsubscribe request received via email")

                submitted = st.form_submit_button("Add to Suppression List", type="primary")
                if submitted:
                    if not LeadValidator.is_valid_email(email_input):
                        st.error("Please enter a valid email address.")
                    else:
                        norm_email = LeadValidator.normalize_email(email_input)
                        existing = db.query(SuppressionList).filter(SuppressionList.email == norm_email).first()
                        if existing:
                            st.warning(f"'{norm_email}' is already in the suppression list.")
                        else:
                            entry = SuppressionList(
                                email=norm_email,
                                reason=reason_input.strip() or "Manual suppression"
                            )
                            db.add(entry)
                            db.commit()
                            st.success(f"Added '{norm_email}' to suppression list.")
                            st.rerun()

        with tab_list:
            entries = db.query(SuppressionList).order_by(SuppressionList.created_at.desc()).all()
            st.markdown(f"**Total Suppressed Addresses:** {len(entries)}")

            if not entries:
                st.info("The suppression list is currently empty.")
            else:
                data = []
                for e in entries:
                    data.append({
                        "ID": e.id,
                        "Email": e.email,
                        "Reason": e.reason,
                        "Added At": e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else "-"
                    })
                st.dataframe(pd.DataFrame(data), use_container_width=True)

                st.markdown("---")
                st.subheader("Remove Contact from Suppression List")
                email_map = {f"{e.email} (ID: {e.id})": e.id for e in entries}
                selected_supp = st.selectbox("Select address to remove:", list(email_map.keys()))
                supp_id = email_map[selected_supp]

                if st.button("🗑️ Remove Selected Suppression Entry"):
                    target = db.query(SuppressionList).filter(SuppressionList.id == supp_id).first()
                    if target:
                        db.delete(target)
                        db.commit()
                        st.success(f"Removed {target.email} from suppression list.")
                        st.rerun()
