import streamlit as st
import pandas as pd
from pathlib import Path
from database.db import get_db
from database.models import Attachment
from attachments.manager import AttachmentManager, ALLOWED_EXTENSIONS

def render_attachments():
    st.title("📎 Attachment Manager")
    st.markdown("Upload, inspect, rename, and manage email brochures, audit SLAs, and case studies safely.")

    with get_db() as db:
        tab_list, tab_upload = st.tabs(["📂 All Stored Attachments", "📤 Upload New Attachment"])

        with tab_upload:
            st.info(f"Allowed file types: {', '.join(ALLOWED_EXTENSIONS.keys())}")
            uploaded_file = st.file_uploader(
                "Select document or brochure to upload",
                type=[ext.replace(".", "") for ext in ALLOWED_EXTENSIONS.keys()]
            )

            if uploaded_file and st.button("Save Attachment", type="primary"):
                try:
                    att = AttachmentManager.save_attachment(
                        db,
                        uploaded_file,
                        uploaded_file.name
                    )
                    st.success(f"Successfully uploaded and secured '{att.filename}' (ID: {att.id})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving attachment: {e}")

        with tab_list:
            attachments = AttachmentManager.list_attachments(db)
            if not attachments:
                st.info("No attachments uploaded yet.")
            else:
                for att in attachments:
                    with st.expander(f"📄 {att.filename} ({round(att.size / 1024, 1)} KB)", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            new_name = st.text_input("Filename", value=att.filename, key=f"att_rename_{att.id}")
                            st.write(f"**Path on Disk:** `{att.path}`")
                            st.write(f"**MIME Type:** `{att.mime_type}`")
                            st.write(f"**Uploaded At:** {att.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                        with col2:
                            # Provide download button for preview
                            try:
                                if Path(att.path).exists():
                                    with open(att.path, "rb") as f:
                                        file_bytes = f.read()
                                    st.download_button(
                                        label="⬇️ Download / View",
                                        data=file_bytes,
                                        file_name=att.filename,
                                        mime=att.mime_type or "application/octet-stream",
                                        key=f"dl_{att.id}"
                                    )
                                else:
                                    st.error("File missing on disk.")
                            except Exception as e:
                                st.error(f"Could not load file: {e}")

                        col_act1, col_act2 = st.columns([1, 4])
                        with col_act1:
                            if st.button("💾 Rename", key=f"save_att_{att.id}"):
                                AttachmentManager.rename_attachment(db, att.id, new_name)
                                st.success("Renamed attachment.")
                                st.rerun()
                        with col_act2:
                            if st.button("🗑️ Delete File", key=f"del_att_{att.id}"):
                                AttachmentManager.delete_attachment(db, att.id)
                                st.warning("Attachment deleted.")
                                st.rerun()
