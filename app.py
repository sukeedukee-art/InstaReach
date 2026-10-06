import logging
import sys
import streamlit as st
from config.security import verify_password
from config.settings import ADMIN_USERNAME, ADMIN_PASSWORD
from database.db import get_db, init_db
from database.schema import seed_default_data
from database.models import User

# UI Page Modules
from ui.dashboard import render_dashboard
from ui.leads import render_leads
from ui.campaigns import render_campaigns
from ui.templates import render_templates
from ui.drafts import render_drafts
from ui.attachments import render_attachments
from ui.queue_view import render_queue
from ui.sent import render_sent
from ui.suppression import render_suppression
from ui.settings import render_settings

# Configure Application Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("cold_mail_agent")

# Set Page Config
st.set_page_config(
    page_title="UK Teleradiology Cold Email Agent",
    page_icon="🩻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e3a8a;
    }
    /* Buttons */
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database schema and default seeds on startup
if "db_initialized" not in st.session_state:
    try:
        seed_default_data()
        st.session_state["db_initialized"] = True
    except Exception as e:
        st.error(f"Database initialization failed: {e}")

# Session State for Authentication
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

def check_login(username, password):
    if not username or not password:
        return False
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return True
    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if user and user.password_hash:
            try:
                if verify_password(password, user.password_hash):
                    return True
            except Exception as e:
                logger.error(f"Password verification error: {e}")
    return False

def render_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="color: #1e3a8a; margin-bottom: 0.2rem;">UK Teleradiology Agent</h2>
            <p style="color: #64748b;">Secure Administrator Portal</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", value=ADMIN_USERNAME)
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")

            if submit:
                if check_login(username, password):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

def main():
    if not st.session_state["authenticated"]:
        render_login()
        return

    # Sidebar Navigation
    with st.sidebar:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1.5rem;">
            <div style="font-size: 2rem;">🩻</div>
            <div>
                <h3 style="margin: 0; font-size: 1.15rem; color: #1e3a8a;">UK Teleradiology</h3>
                <span style="font-size: 0.8rem; color: #64748b;">Outreach Agent</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        page = st.radio(
            "Navigation",
            [
                "Dashboard",
                "Leads",
                "Campaigns",
                "Templates",
                "Drafts",
                "Attachments",
                "Sending Queue",
                "Sent Emails",
                "Suppression List",
                "Settings"
            ],
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.caption(f"Logged in as: **{st.session_state['username']}**")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["username"] = ""
            st.rerun()

    # Route to Selected Page
    if page == "Dashboard":
        render_dashboard()
    elif page == "Leads":
        render_leads()
    elif page == "Campaigns":
        render_campaigns()
    elif page == "Templates":
        render_templates()
    elif page == "Drafts":
        render_drafts()
    elif page == "Attachments":
        render_attachments()
    elif page == "Sending Queue":
        render_queue()
    elif page == "Sent Emails":
        render_sent()
    elif page == "Suppression List":
        render_suppression()
    elif page == "Settings":
        render_settings()

if __name__ == "__main__":
    main()
