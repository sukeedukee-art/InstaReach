# 🩻 UK Teleradiology Cold Email Agent
### Complete User Guide, Operations Manual & System Reference

The **UK Teleradiology Cold Email Agent** is a professional, controlled, local-first B2B campaign management application. It is designed to run automated, compliant, and highly personalized cold outreach campaigns targeting UK diagnostic imaging departments, NHS trusts, and private diagnostic centres.

---

## 📑 Table of Contents
1. [🌟 System Capabilities & Features](#-system-capabilities--features)
2. [🚀 Quick Start: How to Run the Web Server](#-quick-start-how-to-run-the-web-server)
3. [📧 How to Link Your Gmail Account (Step-by-Step)](#-how-to-link-your-gmail-account-step-by-step)
4. [🔄 How to Change or Remove Your Email Account](#-how-to-change-or-remove-your-email-account)
5. [🧪 How to Safely Test the System (Zero-Risk Testing)](#-how-to-safely-test-the-system-zero-risk-testing)
6. [📋 Complete End-to-End Campaign Workflow](#-complete-end-to-end-campaign-workflow)
7. [⚙️ System Architecture & Directory Structure](#️-system-architecture--directory-structure)
8. [❓ Frequently Asked Questions & Troubleshooting](#-frequently-asked-questions--troubleshooting)

---

## 🌟 System Capabilities & Features

### 1. 📥 Smart Lead Ingestion & Auto-Mapping
- **File Support**: Upload contact lists in `.csv`, `.xlsx`, or `.xls` format.
- **Smart Column Detection**: Automatically detects common spreadsheet column names:
  - `Company Name`, `Organisation`, `Hospital`, `Clinic`, `Trust`
  - `Contact Name`, `First Name`, `Last Name`
  - `Email Address`, `Work Email`, `Contact Email`
  - `Job Title`, `Position`, `Role`
  - `Location`, `City`, `Region`, `County`
  - `Website`, `Company Description`, `Notes`
- **Validation**: Strict RFC-compliant email sanitization and validation before database storage.

### 2. ✍️ Email Drafting & Templates
- **Template Engine**: Reusable email templates supporting variable placeholders:
  - `{{contact_name}}`, `{{first_name}}`, `{{last_name}}`
  - `{{company_name}}`, `{{job_title}}`, `{{location}}`, `{{website}}`
  - `{{sender_name}}`, `{{sender_company}}`, `{{sender_email}}`
- **Graceful Fallbacks**: If a lead is missing a location or first name, the template engine cleanly replaces it with professional alternatives (e.g. *"Colleague"*, *"your organisation"*, *"the UK"*) rather than showing broken tags or throwing errors.

### 3. ✨ Gemini AI Personalization (Optional)
- **Zero-Hallucination Guardrails**: Powered by Gemini with clinical healthcare constraints. It tailors the subject line and body using **only verified lead facts provided in your spreadsheet**.
- **No Fabrications**: The AI is strictly instructed never to invent contracts, staff numbers, certifications, or previous communication history.
- **100% Offline Capability**: If no Gemini API key is provided, the system seamlessly operates in **Template Mode**.

### 4. 👁️ Draft Review & Approval Suite
- **Side-by-Side Review**: Inspect the generated subject and body for each lead before anything is queued.
- **In-Browser Editor**: Modify subject lines or body text directly in the browser with live saving.
- **Approval Actions**: **Approve**, **Reject**, or **Regenerate** individual drafts, or click **Approve All Drafted** for one-click bulk processing.

### 5. 📎 Attachment Manager
- **PDF & Brochure Support**: Upload brochures, NHS audit frameworks, pricing schedules, or case studies.
- **Campaign Binding**: Attach or remove documents per-campaign without altering historical sent logs.

### 6. 🛡️ Controlled Queue & Sending Engine
- **Lifecycle Queue**: Staged transitions (`PENDING` ➔ `SENDING` ➔ `SENT` / `FAILED` / `CANCELLED`).
- **Live Controls**: **Start Campaign**, **Pause**, **Resume**, and **Stop** (with confirmation safeguard).
- **Anti-Spam Pacing**: Configurable delay (e.g. 5 to 30 seconds between consecutive emails) to protect your domain and sender reputation.
- **Daily Limits**: Set hard caps on daily email volume.

### 7. 🔒 Compliance & Safety Safeguards
- **🧪 Test Mode (ON by Default)**: Intercepts all outbound messages and delivers them exclusively to your designated test inbox with lead context tagged in the subject line (e.g. `[TEST MODE -> lead@nhs.net] ...`). Real leads never receive emails in Test Mode.
- **📄 Dry-Run Simulation**: Simulates queue generation and database logging without transmitting network packets.
- **Duplicate Protection**: Automatically skips leads who have already been contacted in the active campaign.
- **Suppression List (Opt-Outs)**: Prevents sending to any email present in the suppression/unsubscribe database.

---

## 🚀 Quick Start: How to Run the Web Server

### 1. Prerequisites
Ensure you have **Python 3.12+** installed on your system.

### 2. Launch the Application
Open a terminal in the project folder and run:

```powershell
python -m uvicorn server:app --host 127.0.0.1 --port 8080 --reload
```

### 3. Open the Web Dashboard
Open your browser and navigate to:
👉 **[http://localhost:8080](http://localhost:8080)**

---

## 📧 How to Link Your Gmail Account (Step-by-Step)

To enable the agent to send emails from your personal or work Gmail / Google Workspace account:

### Step 1: Generate a Google App Password
> [!NOTE]
> Google requires an **App Password** (a 16-character security code) instead of your regular Gmail login password.

1. Open your browser and go to your **[Google Account Security Page](https://myaccount.google.com/security)**.
2. Under *"How you sign in to Google"*, make sure **2-Step Verification** is turned **ON**.
3. In the search bar at the top of your Google Account page, search for **App passwords** (or scroll to it under 2-Step Verification).
4. Enter an App Name (e.g. `UK Teleradiology Outreach`) and click **Create**.
5. Google will display a 16-character password in a yellow box (e.g., `abcd efgh ijkl mnop`). **Copy this code.**

### Step 2: Save Credentials in the Application
1. In the web dashboard, click **Settings & Email** in the left sidebar.
2. Under the **SMTP Email Account** card, enter:
   - **SMTP Host**: `smtp.gmail.com` *(for Outlook/Office 365, use `smtp.office365.com`)*
   - **SMTP Port**: `587`
   - **Your Email Address**: `your-email@gmail.com`
   - **Email Password**: Paste the 16-character App Password (spaces will be automatically handled).
   - **Enable TLS / STARTTLS**: Checked (ON).
3. Click **Save SMTP Credentials**.

### Step 3: Verify the Connection
- Click the **🧪 Test Connection** button.
- You will see a green toast notification: **`SMTP Connection Succeeded! Ready to send emails.`**
- The status badge will change to a green **Ready** indicator.

---

## 🔄 How to Change or Remove Your Email Account

### To Change to a Different Email Account:
1. Go to **Settings & Email** in the sidebar.
2. Type in the new email address and corresponding password/app password.
3. Click **Save SMTP Credentials**.
4. Click **Test Connection** to confirm the new mailbox is working.

### To Remove or Disconnect Your Email Account:
1. Go to **Settings & Email**.
2. Clear the **Your Email Address** and **Email Password** fields (leave them blank).
3. Click **Save SMTP Credentials**.
4. The system will revert to an unlinked state. You can still test the entire platform using **Dry-Run Mode**.

---

## 🧪 How to Safely Test the System (Zero-Risk Testing)

You can test the entire workflow with 100% confidence that no real leads will ever be emailed:

### Option A: Test Mode (Recommended — Delivers Emails to You)
1. Go to **Campaigns** -> Click **New Campaign** (or use the pre-seeded campaign).
2. Ensure **🧪 Test Mode** is checked.
3. In the **Test Recipient** field, enter your personal email address (e.g. `your-inbox@gmail.com`).
4. Import `demo_leads.csv` under **Leads & Import**.
5. Click **Generate Drafts** and then **Approve All Drafted**.
6. On the **Dashboard**, click **Start Campaign** and then **⚡ Dispatch Next Batch**.
7. **Result**: Check your inbox. All 5 outreach emails will be delivered directly to *your* inbox so you can review formatting, personalized variables, and layout.

### Option B: Dry-Run Simulation (No Emails Sent Anywhere)
1. When creating or editing a campaign, check **📄 Dry-Run Simulation**.
2. When you click **Dispatch Next Batch**, the system simulates the complete campaign lifecycle, validates emails, checks suppression, and logs entries in **Sent Logs** with status `DRY_RUN` without making any network connection.

---

## 📋 Complete End-to-End Campaign Workflow

```
[1. Upload Leads (CSV/XLSX)] 
       │
       ▼
[2. Select / Create Email Template] 
       │
       ▼
[3. Generate Drafts (Template or Gemini AI)] 
       │
       ▼
[4. Review, Edit & Approve Drafts] 
       │
       ▼
[5. Start Campaign -> Enqueue Approved Leads] 
       │
       ▼
[6. Controlled Dispatch with Pacing Delays] 
       │
       ▼
[7. Monitor Live Progress & Audit Sent Logs]
```

### Step-by-Step Instructions:

1. **Create an Outreach Campaign**:
   - Go to **Campaigns** -> **New Campaign**.
   - Name your campaign (e.g. `Q4 UK NHS Radiology Capacity`).
   - Select your base template.
   - Choose whether to enable AI Personalization.
   - Set pacing delay (e.g. `5` seconds for testing, `30` seconds for live outreach).

2. **Upload Your Contacts**:
   - Go to **Leads & Import**.
   - Select your campaign from the dropdown.
   - Click **Upload CSV / XLSX** and select your file (you can test with the included `demo_leads.csv`).
   - The system automatically detects and maps column headers.

3. **Generate & Review Drafts**:
   - Go to **Draft Review** in the sidebar.
   - Inspect the generated subject line and email body for each recipient.
   - Edit any text directly in the box and click **Save**.
   - Click **Approve** on individual leads or **Approve All Drafted**.

4. **Launch Dispatch**:
   - Go to **Dashboard**.
   - Click **Start Campaign** (this moves all approved leads into the active queue).
   - Click **⚡ Dispatch Next Batch**.
   - Watch the live queue counter and progress indicator update in real time.

5. **Review Sent Audit Logs**:
   - Click **Sent Logs** in the sidebar to view timestamps, delivery statuses, error reports, and full email body inspectors.

---

## ⚙️ System Architecture & Directory Structure

```
cold_mail_agent/
├── server.py                  # FastAPI high-performance REST API & static server
├── static/                    # Modern responsive frontend
│   ├── index.html             # HTML5 single-page application
│   ├── style.css              # Custom dark-mode design system & animations
│   └── app.js                 # Reactive frontend controller & API client
├── demo_leads.csv             # Fictional NHS & private diagnostic demo leads
├── requirements.txt           # Python dependencies
├── .env.example               # Environment configuration template
├── config/
│   ├── settings.py            # Environment settings loader & dynamic reloader
│   └── security.py            # PBKDF2-SHA256 authentication security
├── database/
│   ├── db.py                  # SQLAlchemy session manager & engine
│   ├── models.py              # Relational models (10 tables)
│   └── schema.py              # Schema seeding & default data
├── ai/
│   ├── prompts.py             # UK healthcare zero-hallucination prompts
│   ├── gemini_client.py       # Gemini API client with strict JSON validation
│   └── personalization.py     # Personalization coordinator
├── email_engine/
│   ├── base_provider.py       # Pluggable email interface
│   ├── smtp_provider.py       # SMTP gateway provider (TLS, timeouts, attachments)
│   └── sender.py              # Sender queue binding
├── campaigns/
│   ├── campaign_manager.py    # Campaign lifecycle transitions & draft batching
│   ├── queue_manager.py       # Staging queue & cancellation logic
│   └── processor.py           # Controlled dispatch loop with pacing & pausing
├── leads/
│   ├── validator.py           # RFC email validator & string sanitizers
│   ├── deduplicator.py        # Duplicate prevention & suppression checks
│   └── importer.py            # CSV/XLSX parser & auto-column mapper
├── templates/
│   └── template_engine.py     # Variable placeholder substitution & fallback engine
├── attachments/
│   └── manager.py             # Attachment file storage & campaign binder
└── storage/
    ├── attachments/           # Uploaded brochure & document files
    └── database/              # SQLite database storage
```

---

## ❓ Frequently Asked Questions & Troubleshooting

### Q1: Why does it say "SMTP credentials not configured" when I click Dispatch?
**A**: You have not yet saved your email address and password in the application. Go to **Settings & Email** in the sidebar, enter your email and App Password, click **Save SMTP Credentials**, and click **Test Connection**. Alternatively, enable **Dry-Run** on your campaign to test without sending real emails.

### Q2: What if a lead in my spreadsheet does not have a "First Name" or "Location"?
**A**: The template engine handles this gracefully. If `{{first_name}}` is missing, it inserts *"Colleague"*. If `{{company_name}}` is missing, it inserts *"your organisation"*. If `{{location}}` is missing, it inserts *"the UK"*. Your emails will never show raw `{}` brackets or error out.

### Q3: How do I stop a campaign that is currently sending?
**A**: On the **Dashboard**, click the **Stop Campaign** button and confirm. The processor immediately halts sending and marks pending queue items as `CANCELLED` while preserving all leads and drafts safely.

### Q4: How do I prevent sending to someone who unsubscribed?
**A**: Go to **Suppression List** in the sidebar, click **Suppress Email**, and add their email address. The system checks this list before every send; any matching lead is automatically marked `SKIPPED` and will never receive an email.

### Q5: How do I run the automated pytest test suite?
**A**: Run:
```powershell
python -m pytest
```
All 13 automated tests validate lead imports, template rendering, AI parsing, queue state transitions, test-mode redirection, and safety mechanisms.
