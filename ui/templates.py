import streamlit as st
import pandas as pd
from database.db import get_db
from database.models import EmailTemplate
from templates.template_engine import TemplateEngine

def render_templates():
    st.title("📝 Email Templates")
    st.markdown("Create and manage base email templates with dynamic placeholder variables.")

    with get_db() as db:
        templates = db.query(EmailTemplate).order_by(EmailTemplate.created_at.desc()).all()

        tab_list, tab_create, tab_preview = st.tabs(["📚 All Templates", "➕ Create Template", "🔍 Live Variable Previewer"])

        with tab_list:
            if not templates:
                st.info("No email templates created yet. Use the Create Template tab.")
            else:
                for tpl in templates:
                    with st.expander(f"✉️ {tpl.name}", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            new_name = st.text_input("Template Name", value=tpl.name, key=f"tpl_name_{tpl.id}")
                            new_desc = st.text_input("Description", value=tpl.description or "", key=f"tpl_desc_{tpl.id}")
                            new_subj = st.text_input("Subject Line", value=tpl.subject, key=f"tpl_subj_{tpl.id}")
                            new_body = st.text_area("Body Text", value=tpl.body, height=250, key=f"tpl_body_{tpl.id}")

                        with col2:
                            st.markdown("#### Available Variables")
                            st.caption("""
                            - `{{contact_name}}`
                            - `{{first_name}}`
                            - `{{last_name}}`
                            - `{{company_name}}`
                            - `{{job_title}}`
                            - `{{website}}`
                            - `{{location}}`
                            - `{{sender_name}}`
                            - `{{sender_company}}`
                            - `{{sender_email}}`
                            """)

                        col_btn1, col_btn2 = st.columns([1, 4])
                        with col_btn1:
                            if st.button("💾 Update Template", key=f"update_tpl_{tpl.id}"):
                                tpl.name = new_name
                                tpl.description = new_desc
                                tpl.subject = new_subj
                                tpl.body = new_body
                                db.commit()
                                st.success("Template updated!")
                                st.rerun()
                        with col_btn2:
                            if st.button("🗑️ Delete Template", key=f"del_tpl_{tpl.id}"):
                                db.delete(tpl)
                                db.commit()
                                st.warning("Template deleted.")
                                st.rerun()

        with tab_create:
            with st.form("create_template_form"):
                name = st.text_input("Template Title *", placeholder="e.g. Urgent Diagnostic Teleradiology Reporting")
                description = st.text_input("Short Description", placeholder="e.g. For NHS Clinical Imaging Leads")
                subject = st.text_input("Subject Line *", placeholder="Overnight Radiology Coverage for {{company_name}}")
                body = st.text_area("Body Content *", height=300, placeholder="""Dear {{first_name}},

I am reaching out regarding diagnostic capacity support for {{company_name}} in {{location}}...

Kind regards,
{{sender_name}}
{{sender_company}}""")

                st.markdown("""
                **Quick Tip:** Use double curly braces like `{{first_name}}`, `{{company_name}}`, `{{location}}`.
                Missing lead variables are automatically handled with clean, professional fallbacks.
                """)

                submitted = st.form_submit_button("Create Template", type="primary")
                if submitted:
                    if not name.strip() or not subject.strip() or not body.strip():
                        st.error("Please fill in the title, subject, and body.")
                    else:
                        new_tpl = EmailTemplate(
                            name=name.strip(),
                            description=description.strip(),
                            subject=subject.strip(),
                            body=body.strip()
                        )
                        db.add(new_tpl)
                        db.commit()
                        st.success(f"Template '{name}' created successfully!")
                        st.rerun()

        with tab_preview:
            st.subheader("🧪 Live Template Variable Sandbox")
            col_in, col_out = st.columns(2)
            with col_in:
                st.write("**Mock Lead Context Data:**")
                mock_ctx = {
                    "first_name": st.text_input("first_name", "Eleanor"),
                    "last_name": st.text_input("last_name", "Smith"),
                    "contact_name": st.text_input("contact_name", "Dr. Eleanor Smith"),
                    "company_name": st.text_input("company_name", "St. Jude Diagnostic Trust"),
                    "job_title": st.text_input("job_title", "Clinical Imaging Director"),
                    "location": st.text_input("location", "Manchester"),
                    "sender_name": "Dr. Alistair Vance",
                    "sender_company": "UK Teleradiology Partners",
                    "sender_email": "outreach@uk-teleradiology.co.uk"
                }
                sample_subj = st.text_input("Test Subject Line", "Urgent reporting SLA for {{company_name}}")
                sample_body = st.text_area("Test Body", "Dear {{first_name}},\n\nWe provide 1-hour reporting coverage for hospitals in {{location}}.\n\nBest,\n{{sender_name}}")

            with col_out:
                st.write("**Rendered Result:**")
                rendered_subj, rendered_body = TemplateEngine.render_email(sample_subj, sample_body, mock_ctx)
                st.info(f"**Subject:** {rendered_subj}")
                st.markdown(f"""
                <div style="background-color: #f1f5f9; padding: 1.2rem; border-radius: 8px; color: #0f172a; white-space: pre-wrap; font-family: monospace;">
{rendered_body}
                </div>
                """, unsafe_allow_html=True)
