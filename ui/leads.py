import streamlit as st
import pandas as pd
from database.db import get_db
from database.models import Campaign, Lead
from leads.importer import LeadImporter, COLUMN_MAPPINGS
from leads.validator import LeadValidator

def render_leads():
    st.title("👥 Lead Management & Upload")
    st.markdown("Upload CSV or XLSX contact files with automatic field detection, validation, and deduplication.")

    with get_db() as db:
        campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
        if not campaigns:
            st.warning("Please create a campaign first under the Campaigns page before importing leads.")
            return

        campaign_map = {f"{c.name} (ID: {c.id})": c.id for c in campaigns}
        selected_label = st.selectbox("Assign Leads to Campaign:", list(campaign_map.keys()))
        campaign_id = campaign_map[selected_label]

        tab_upload, tab_view = st.tabs(["📤 Upload New Leads", "📋 View Campaign Leads"])

        with tab_upload:
            uploaded_file = st.file_uploader("Upload Leads (.csv or .xlsx)", type=["csv", "xlsx", "xls"])
            if uploaded_file:
                try:
                    df = LeadImporter.read_file(uploaded_file, uploaded_file.name)
                    st.write(f"Detected **{len(df)}** rows in file.")
                    st.dataframe(df.head(5), use_container_width=True)

                    # Auto-detect column mapping
                    detected_mapping = LeadImporter.detect_column_mappings(df)

                    st.markdown("#### 🔍 Column Field Mapping")
                    st.caption("Verify or adjust how the uploaded columns match the standard outreach lead fields:")

                    df_cols = ["-- Unmapped / None --"] + list(df.columns)
                    final_mapping = {}

                    col_grid1, col_grid2 = st.columns(2)
                    standard_fields = list(COLUMN_MAPPINGS.keys())

                    for idx, field in enumerate(standard_fields):
                        target_col = col_grid1 if idx % 2 == 0 else col_grid2
                        default_val = detected_mapping.get(field, "-- Unmapped / None --")
                        default_idx = df_cols.index(default_val) if default_val in df_cols else 0

                        with target_col:
                            required_star = " *" if field == "email" else ""
                            selected_col = st.selectbox(
                                f"Map **{field.replace('_', ' ').title()}{required_star}**:",
                                options=df_cols,
                                index=default_idx,
                                key=f"mapping_{field}"
                            )
                            if selected_col != "-- Unmapped / None --":
                                final_mapping[field] = selected_col

                    if "email" not in final_mapping:
                        st.error("⚠️ An 'Email' column mapping is strictly required to proceed.")
                    else:
                        if st.button("📥 Import Leads into Campaign", type="primary"):
                            with st.spinner("Importing and validating leads..."):
                                imported, skipped, reasons = LeadImporter.process_and_import(
                                    db,
                                    campaign_id=campaign_id,
                                    df=df,
                                    custom_mapping=final_mapping
                                )
                                st.success(f"✅ Successfully imported {imported} leads! (Skipped: {skipped})")
                                if reasons:
                                    with st.expander("View Skipped Reasons"):
                                        for r in reasons[:50]:
                                            st.write(f"- {r}")
                                        if len(reasons) > 50:
                                            st.caption(f"...and {len(reasons) - 50} more")
                                st.rerun()

                except Exception as e:
                    st.error(f"Failed to read file: {e}")

        with tab_view:
            leads = db.query(Lead).filter(Lead.campaign_id == campaign_id).order_by(Lead.id.desc()).all()
            st.markdown(f"**Total Leads in Campaign:** {len(leads)}")

            if leads:
                lead_data = []
                for l in leads:
                    lead_data.append({
                        "ID": l.id,
                        "Company": l.company_name or "-",
                        "Contact Name": l.contact_name or "-",
                        "Email": l.email,
                        "Job Title": l.job_title or "-",
                        "Location": l.location or "-",
                        "Status": l.status,
                        "Approved": "✅" if l.approved else "❌",
                        "Error / Reason": l.error_message or "-"
                    })
                st.dataframe(pd.DataFrame(lead_data), use_container_width=True)

                col_actions1, col_actions2 = st.columns([1, 4])
                with col_actions1:
                    with st.popover("🗑️ Clear All Leads in Campaign"):
                        st.write("Are you sure? This will remove all leads and draft data for this campaign.")
                        if st.button("Confirm Delete All Leads", type="primary"):
                            db.query(Lead).filter(Lead.campaign_id == campaign_id).delete()
                            db.commit()
                            st.success("All leads deleted.")
                            st.rerun()
            else:
                st.info("No leads found for this campaign yet. Use the Upload tab to add leads.")
