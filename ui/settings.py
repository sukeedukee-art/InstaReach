import streamlit as st
from config.settings import (
    GEMINI_API_KEY, SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_USE_TLS,
    SENDER_NAME, SENDER_EMAIL, SENDER_COMPANY, DEFAULT_DELAY_SECONDS, DEFAULT_DAILY_LIMIT, DATABASE_URL
)
from ai.gemini_client import GeminiClient
from email_engine.smtp_provider import SmtpEmailProvider

def render_settings():
    st.title("⚙️ System Settings & Diagnostic Status")
    st.markdown("Check external integrations, safety controls, and system configuration.")

    # Status Health Check Cards
    col_stat1, col_stat2 = st.columns(2)

    ai_client = GeminiClient()
    smtp_provider = SmtpEmailProvider()

    with col_stat1:
        st.subheader("🤖 Gemini AI Integration")
        if ai_client.is_configured():
            st.success("✅ **Gemini API Configured**")
            st.caption("Model: `gemini-1.5-flash` with zero-hallucination constraint.")
        else:
            st.warning("⚠️ **Gemini API Not Configured**")

        with st.expander("🔑 Update Gemini API Key", expanded=not ai_client.is_configured()):
            new_gemini_key = st.text_input("Gemini API Key", value=GEMINI_API_KEY, type="password", help="Enter your Google AI Studio Gemini API Key")
            if st.button("Save Gemini API Key"):
                from config.settings import save_env_file
                save_env_file({"GEMINI_API_KEY": new_gemini_key.strip()})
                st.success("Gemini API Key saved! Refreshing...")
                st.rerun()

    with col_stat2:
        st.subheader("📧 SMTP Email Gateway")
        if smtp_provider.is_configured():
            st.success(f"✅ **SMTP Configured** ({SMTP_USERNAME} @ {SMTP_HOST})")
            if st.button("🧪 Test SMTP Server Connection"):
                with st.spinner("Connecting to SMTP server..."):
                    connected, err = smtp_provider.test_connection()
                    if connected:
                        st.success("SMTP Connection Succeeded!")
                    else:
                        st.error(f"SMTP Connection Failed: {err}")
        else:
            st.error("❌ **SMTP Not Configured / Incomplete** (Host, Username, or Password missing)")

        with st.expander("⚙️ Configure / Edit SMTP Credentials", expanded=not smtp_provider.is_configured()):
            st.info("💡 **Gmail Note:** Use a 16-character Google App Password (not your normal Gmail password).")
            with st.form("smtp_config_form"):
                host_val = st.text_input("SMTP Host", value=SMTP_HOST or "smtp.gmail.com")
                port_val = st.number_input("SMTP Port", value=SMTP_PORT or 587)
                user_val = st.text_input("SMTP Username / Email", value=SMTP_USERNAME, placeholder="your_email@gmail.com")
                pass_val = st.text_input("SMTP Password / App Password", value=SMTP_PASSWORD, type="password")
                tls_val = st.checkbox("Use TLS (STARTTLS)", value=SMTP_USE_TLS)

                submit_smtp = st.form_submit_button("💾 Save SMTP Credentials", type="primary")
                if submit_smtp:
                    from config.settings import save_env_file
                    save_env_file({
                        "SMTP_HOST": host_val.strip(),
                        "SMTP_PORT": str(port_val),
                        "SMTP_USERNAME": user_val.strip(),
                        "SMTP_PASSWORD": pass_val.strip(),
                        "SMTP_USE_TLS": str(tls_val)
                    })
                    st.success("SMTP Credentials saved to .env!")
                    st.rerun()

    st.markdown("---")
    st.subheader("🏢 Default Sender & Rate Defaults")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.text_input("Default Sender Name", value=SENDER_NAME, disabled=True)
        st.text_input("Default Sender Email", value=SENDER_EMAIL, disabled=True)
        st.text_input("Default Sender Company", value=SENDER_COMPANY, disabled=True)

    with col_d2:
        st.number_input("Default Delay Between Sends (seconds)", value=DEFAULT_DELAY_SECONDS, disabled=True)
        st.number_input("Default Daily Limit (emails/day)", value=DEFAULT_DAILY_LIMIT, disabled=True)
        st.text_input("Database Connection URI", value=DATABASE_URL, disabled=True)

    st.caption("Note: Configuration parameters are securely managed via `.env` file to prevent accidental credential leakage.")
