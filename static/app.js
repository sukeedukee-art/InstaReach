// instaReach — Cold Email Outreach Platform Controller
const API_BASE = "/api";

const App = {
  state: {
    campaigns: [],
    currentCampaignId: null,
    leads: [],
    templates: [],
    attachments: [],
    sentLogs: [],
    suppression: [],
    systemStatus: null
  },

  async init() {
    this.setupNavigation();
    await this.loadInitialData();
  },

  setupNavigation() {
    document.querySelectorAll(".nav-item").forEach(item => {
      item.addEventListener("click", () => {
        const page = item.getAttribute("data-page");
        this.switchPage(page);
      });
    });

    document.getElementById("dash-campaign-select").addEventListener("change", (e) => {
      this.state.currentCampaignId = parseInt(e.target.value);
      this.renderDashboard();
    });

    document.getElementById("leads-campaign-select").addEventListener("change", (e) => {
      this.state.currentCampaignId = parseInt(e.target.value);
      this.loadLeads();
    });

    document.getElementById("drafts-campaign-select").addEventListener("change", (e) => {
      this.state.currentCampaignId = parseInt(e.target.value);
      this.loadDrafts();
    });
  },

  switchPage(pageId) {
    document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
    const activeNav = document.querySelector(`.nav-item[data-page="${pageId}"]`);
    if (activeNav) activeNav.classList.add("active");

    document.querySelectorAll(".page-view").forEach(p => p.style.display = "none");
    const targetPage = document.getElementById(`page-${pageId}`);
    if (targetPage) targetPage.style.display = "block";

    // Trigger page data loaders
    if (pageId === "dashboard") this.loadCampaigns();
    if (pageId === "campaigns") this.loadCampaigns();
    if (pageId === "leads") this.loadLeads();
    if (pageId === "drafts") this.loadDrafts();
    if (pageId === "templates") this.loadTemplates();
    if (pageId === "attachments") this.loadAttachments();
    if (pageId === "sent") this.loadSentLogs();
    if (pageId === "suppression") this.loadSuppression();
    if (pageId === "settings") this.loadSettings();
  },

  async loadInitialData() {
    await Promise.all([
      this.loadCampaigns(),
      this.loadTemplates(),
      this.loadSettings()
    ]);
  },

  // ==================== CAMPAIGNS & DASHBOARD ====================
  async loadCampaigns() {
    try {
      const res = await fetch(`${API_BASE}/campaigns`);
      this.state.campaigns = await res.json();
      
      if (this.state.campaigns.length > 0 && !this.state.currentCampaignId) {
        this.state.currentCampaignId = this.state.campaigns[0].id;
      }

      this.populateCampaignSelectors();
      this.renderDashboard();
      this.renderCampaignsTable();
    } catch (err) {
      this.toast("Failed to load campaigns", "error");
    }
  },

  populateCampaignSelectors() {
    const selectors = [
      document.getElementById("dash-campaign-select"),
      document.getElementById("leads-campaign-select"),
      document.getElementById("drafts-campaign-select")
    ];

    selectors.forEach(sel => {
      if (!sel) return;
      sel.innerHTML = "";
      this.state.campaigns.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = `${c.name} (${c.status})`;
        if (c.id === this.state.currentCampaignId) opt.selected = true;
        sel.appendChild(opt);
      });
    });
  },

  renderDashboard() {
    const c = this.state.campaigns.find(x => x.id === this.state.currentCampaignId);
    if (!c) return;

    document.getElementById("banner-campaign-name").textContent = c.name;
    document.getElementById("banner-campaign-desc").textContent = c.description || "No clinical description provided.";

    const badge = document.getElementById("banner-status-badge");
    badge.className = `badge badge-${c.status.toLowerCase()}`;
    badge.innerHTML = `<span class="badge-dot"></span> ${c.status}`;

    // Mode Indicators
    const modeContainer = document.getElementById("banner-mode-indicators");
    modeContainer.innerHTML = "";
    if (c.test_mode) {
      modeContainer.innerHTML += `<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;"><i class="fa-solid fa-flask" style="margin-right: 4px;"></i> Test Mode (${c.test_recipient || 'Default'})</span>`;
    }
    if (c.dry_run) {
      modeContainer.innerHTML += `<span class="badge" style="background: rgba(59, 130, 246, 0.2); color: #60a5fa;"><i class="fa-solid fa-file" style="margin-right: 4px;"></i> Dry-Run</span>`;
    }
    if (c.ai_enabled) {
      modeContainer.innerHTML += `<span class="badge" style="background: rgba(168, 85, 247, 0.2); color: #c084fc;"><i class="fa-solid fa-sparkles" style="margin-right: 4px;"></i> AI Active</span>`;
    }

    // Metrics
    document.getElementById("m-total").textContent = c.total_leads;
    document.getElementById("m-drafted").textContent = c.drafted_leads;
    document.getElementById("m-approved").textContent = c.approved_leads;
    document.getElementById("m-queued").textContent = c.queued_leads;
    document.getElementById("m-sent").textContent = c.sent_leads;
    document.getElementById("m-failed").textContent = c.failed_leads;
    document.getElementById("m-skipped").textContent = c.skipped_leads;

    document.getElementById("dispatch-queue-count").textContent = `${c.pending_queue} pending messages in queue`;

    // Button states
    document.getElementById("btn-start").disabled = (c.status === "RUNNING");
    document.getElementById("btn-pause").disabled = (c.status !== "RUNNING");
    document.getElementById("btn-resume").disabled = (c.status !== "PAUSED");

    this.loadRecentSentActivity(c.id);
  },

  async loadRecentSentActivity(campaignId) {
    try {
      const res = await fetch(`${API_BASE}/sent?campaign_id=${campaignId}`);
      const logs = await res.json();
      const tbody = document.querySelector("#dash-recent-table tbody");
      tbody.innerHTML = "";

      if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No messages dispatched yet.</td></tr>`;
        return;
      }

      logs.slice(0, 5).forEach(l => {
        const tr = document.createElement("tr");
        const statusBadge = l.status === "SENT" 
          ? `<span class="badge badge-completed">SENT</span>`
          : (l.status === "DRY_RUN" ? `<span class="badge badge-ready">DRY RUN</span>` : `<span class="badge badge-stopped">FAILED</span>`);

        tr.innerHTML = `
          <td>${new Date(l.sent_at).toLocaleTimeString()}</td>
          <td><b>${l.recipient_email}</b></td>
          <td><span style="color: #60a5fa;">${l.actual_recipient_email}</span></td>
          <td>${l.subject}</td>
          <td>${statusBadge}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {}
  },

  renderCampaignsTable() {
    const tbody = document.querySelector("#campaigns-table tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    this.state.campaigns.forEach(c => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><b>${c.name}</b><br><small style="color: var(--text-muted);">${c.description || ''}</small></td>
        <td><span class="badge badge-${c.status.toLowerCase()}">${c.status}</span></td>
        <td>${c.ai_enabled ? '<span style="color:#c084fc;">✨ Gemini</span>' : '📄 Template'}</td>
        <td>${c.test_mode ? '🧪 Test' : (c.dry_run ? '📄 Dry-Run' : '🚀 Live')}</td>
        <td>${c.delay_seconds}s</td>
        <td><b>${c.sent_leads} / ${c.total_leads}</b></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="App.selectCampaign(${c.id})"><i class="fa-solid fa-arrow-right"></i> Open</button>
          <button class="btn btn-danger btn-sm" onclick="App.deleteCampaign(${c.id})"><i class="fa-solid fa-trash"></i></button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  },

  selectCampaign(id) {
    this.state.currentCampaignId = id;
    this.populateCampaignSelectors();
    this.switchPage("dashboard");
  },

  // ==================== CAMPAIGN ACTIONS ====================
  async startCampaign() {
    const res = await fetch(`${API_BASE}/campaigns/${this.state.currentCampaignId}/start`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      this.toast("Campaign Started & Approved Leads Enqueued!", "success");
      this.loadCampaigns();
    } else {
      this.toast(data.detail || "Error starting campaign", "error");
    }
  },

  async pauseCampaign() {
    await fetch(`${API_BASE}/campaigns/${this.state.currentCampaignId}/pause`, { method: "POST" });
    this.toast("Campaign Paused", "info");
    this.loadCampaigns();
  },

  async resumeCampaign() {
    await fetch(`${API_BASE}/campaigns/${this.state.currentCampaignId}/resume`, { method: "POST" });
    this.toast("Campaign Resumed", "success");
    this.loadCampaigns();
  },

  async confirmStopCampaign() {
    if (confirm("Are you sure you want to stop this campaign? Pending queue items will be cancelled.")) {
      await fetch(`${API_BASE}/campaigns/${this.state.currentCampaignId}/stop`, { method: "POST" });
      this.toast("Campaign Stopped", "error");
      this.loadCampaigns();
    }
  },

  async generateDrafts() {
    this.toast("Generating personalized drafts...", "info");
    const res = await fetch(`${API_BASE}/campaigns/${this.state.currentCampaignId}/generate-drafts`, { method: "POST" });
    const data = await res.json();
    this.toast(`Generated ${data.generated} drafts!`, "success");
    this.loadCampaigns();
  },

  async dispatchBatch() {
    const statusLabel = document.getElementById("dispatch-live-status");
    statusLabel.textContent = "Connecting to mail gateway...";

    try {
      const res = await fetch(`${API_BASE}/campaigns/${this.state.currentCampaignId}/dispatch`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        this.toast(data.message || "Batch processed successfully", "success");
        statusLabel.textContent = `Completed: ${data.sent} sent, ${data.failed || 0} failed.`;
        this.loadCampaigns();
      } else {
        this.toast(data.detail || "Dispatch failed", "error");
        statusLabel.textContent = `Error: ${data.detail}`;
      }
    } catch (err) {
      this.toast("Network error during dispatch", "error");
      statusLabel.textContent = "Network error";
    }
  },

  // ==================== LEADS MANAGEMENT ====================
  async loadLeads() {
    if (!this.state.currentCampaignId) return;
    try {
      const res = await fetch(`${API_BASE}/campaigns/${this.state.currentCampaignId}/leads`);
      this.state.leads = await res.json();
      
      document.getElementById("leads-count-heading").textContent = `Leads in Campaign (${this.state.leads.length})`;
      const tbody = document.querySelector("#leads-table tbody");
      tbody.innerHTML = "";

      if (this.state.leads.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No leads uploaded yet. Use the Upload button above.</td></tr>`;
        return;
      }

      this.state.leads.forEach(l => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><b>${l.company_name || '-'}</b></td>
          <td>${l.contact_name || '-'}</td>
          <td><code>${l.email}</code></td>
          <td>${l.job_title || '-'}</td>
          <td>${l.location || '-'}</td>
          <td><span class="badge badge-${l.status.toLowerCase()}">${l.status}</span></td>
          <td>${l.approved ? '✅' : '❌'}</td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      this.toast("Failed to load leads", "error");
    }
  },

  async handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    this.toast(`Importing ${file.name}...`, "info");
    try {
      const res = await fetch(`${API_BASE}/campaigns/${this.state.currentCampaignId}/import-file`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        this.toast(`Imported ${data.imported} leads! (Skipped: ${data.skipped})`, "success");
        this.loadLeads();
        this.loadCampaigns();
      } else {
        this.toast(data.detail || "Import error", "error");
      }
    } catch (e) {
      this.toast("Failed to upload file", "error");
    }
  },

  // ==================== DRAFTS REVIEW ====================
  async loadDrafts() {
    if (!this.state.currentCampaignId) return;
    try {
      const res = await fetch(`${API_BASE}/campaigns/${this.state.currentCampaignId}/leads`);
      const leads = await res.json();
      const container = document.getElementById("drafts-container");
      container.innerHTML = "";

      if (leads.length === 0) {
        container.innerHTML = `<div class="glass-panel" style="text-align: center; color: var(--text-muted);">No leads in this campaign. Import some under Leads & Import.</div>`;
        return;
      }

      leads.forEach(l => {
        const card = document.createElement("div");
        card.className = "glass-panel";
        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div>
              <h3 style="font-size: 1.1rem; font-weight: 700;">${l.contact_name || 'Contact'} — ${l.company_name || 'Organisation'}</h3>
              <span style="font-size: 0.85rem; color: var(--text-muted);">${l.email} • ${l.job_title || ''} • ${l.location || ''}</span>
            </div>
            <span class="badge badge-${l.status.toLowerCase()}">${l.status}</span>
          </div>

          <div class="grid-2" style="margin-bottom: 1rem;">
            <div>
              <label class="form-label">Subject Line</label>
              <input type="text" class="form-control" id="draft-subj-${l.id}" value="${l.draft_subject || ''}">
            </div>
            <div>
              <label class="form-label">Email Body</label>
              <textarea class="form-control" id="draft-body-${l.id}" style="height: 120px;">${l.draft_body || ''}</textarea>
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; gap: 8px;">
            <button class="btn btn-secondary btn-sm" onclick="App.saveDraft(${l.id})"><i class="fa-solid fa-floppy-disk"></i> Save</button>
            <button class="btn btn-secondary btn-sm" onclick="App.regenerateDraft(${l.id})"><i class="fa-solid fa-wand-magic-sparkles"></i> Regenerate</button>
            <button class="btn btn-danger btn-sm" onclick="App.rejectLead(${l.id})"><i class="fa-solid fa-xmark"></i> Reject</button>
            <button class="btn btn-success btn-sm" onclick="App.approveLead(${l.id})"><i class="fa-solid fa-check"></i> Approve</button>
          </div>
        `;
        container.appendChild(card);
      });
    } catch (e) {
      this.toast("Failed to load drafts", "error");
    }
  },

  async saveDraft(leadId) {
    const subject = document.getElementById(`draft-subj-${leadId}`).value;
    const body = document.getElementById(`draft-body-${leadId}`).value;
    await fetch(`${API_BASE}/leads/${leadId}/draft`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject, body })
    });
    this.toast("Draft Saved", "success");
  },

  async approveLead(leadId) {
    await this.saveDraft(leadId);
    await fetch(`${API_BASE}/leads/${leadId}/approve`, { method: "POST" });
    this.toast("Lead Approved", "success");
    this.loadDrafts();
    this.loadCampaigns();
  },

  async rejectLead(leadId) {
    await fetch(`${API_BASE}/leads/${leadId}/reject`, { method: "POST" });
    this.toast("Lead Rejected", "info");
    this.loadDrafts();
    this.loadCampaigns();
  },

  async regenerateDraft(leadId) {
    this.toast("Regenerating draft...", "info");
    const res = await fetch(`${API_BASE}/leads/${leadId}/regenerate`, { method: "POST" });
    const data = await res.json();
    document.getElementById(`draft-subj-${leadId}`).value = data.subject;
    document.getElementById(`draft-body-${leadId}`).value = data.body;
    this.toast("Draft updated with fresh personalization!", "success");
  },

  async bulkApprove() {
    const res = await fetch(`${API_BASE}/campaigns/${this.state.currentCampaignId}/bulk-approve`, { method: "POST" });
    const data = await res.json();
    this.toast(`Approved ${data.count} drafts!`, "success");
    this.loadDrafts();
    this.loadCampaigns();
  },

  // ==================== TEMPLATES ====================
  async loadTemplates() {
    try {
      const res = await fetch(`${API_BASE}/templates`);
      this.state.templates = await res.json();

      // Populate campaign modal template dropdown
      const sel = document.getElementById("new-camp-template");
      if (sel) {
        sel.innerHTML = "";
        this.state.templates.forEach(t => {
          const opt = document.createElement("option");
          opt.value = t.id;
          opt.textContent = t.name;
          sel.appendChild(opt);
        });
      }

      const tbody = document.querySelector("#templates-table tbody");
      if (!tbody) return;
      tbody.innerHTML = "";

      this.state.templates.forEach(t => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><b>${t.name}</b></td>
          <td>${t.subject}</td>
          <td><small style="color: var(--text-muted);">${t.description || '-'}</small></td>
          <td>
            <button class="btn btn-danger btn-sm" onclick="App.deleteTemplate(${t.id})"><i class="fa-solid fa-trash"></i></button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {}
  },

  // ==================== ATTACHMENTS ====================
  async loadAttachments() {
    try {
      const res = await fetch(`${API_BASE}/attachments`);
      this.state.attachments = await res.json();
      const tbody = document.querySelector("#attachments-table tbody");
      tbody.innerHTML = "";

      if (this.state.attachments.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No attachments uploaded yet.</td></tr>`;
        return;
      }

      this.state.attachments.forEach(a => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><b>${a.filename}</b></td>
          <td>${(a.size / 1024).toFixed(1)} KB</td>
          <td><code>${a.mime_type || 'file'}</code></td>
          <td>${new Date(a.created_at).toLocaleDateString()}</td>
          <td>
            <button class="btn btn-danger btn-sm" onclick="App.deleteAttachment(${a.id})"><i class="fa-solid fa-trash"></i></button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {}
  },

  async handleAttachmentUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    this.toast(`Uploading ${file.name}...`, "info");
    const res = await fetch(`${API_BASE}/attachments`, { method: "POST", body: formData });
    if (res.ok) {
      this.toast("Attachment Saved!", "success");
      this.loadAttachments();
    }
  },

  async deleteAttachment(id) {
    if (confirm("Delete this attachment?")) {
      await fetch(`${API_BASE}/attachments/${id}`, { method: "DELETE" });
      this.toast("Attachment removed", "info");
      this.loadAttachments();
    }
  },

  // ==================== SENT LOGS ====================
  async loadSentLogs() {
    try {
      const res = await fetch(`${API_BASE}/sent`);
      const logs = await res.json();
      const tbody = document.querySelector("#sent-logs-table tbody");
      tbody.innerHTML = "";

      if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No sent logs recorded yet.</td></tr>`;
        return;
      }

      logs.forEach(l => {
        const tr = document.createElement("tr");
        const statusBadge = l.status === "SENT" 
          ? `<span class="badge badge-completed">SENT</span>`
          : (l.status === "DRY_RUN" ? `<span class="badge badge-ready">DRY RUN</span>` : `<span class="badge badge-stopped">FAILED</span>`);
        
        tr.innerHTML = `
          <td>${new Date(l.sent_at).toLocaleString()}</td>
          <td><b>${l.recipient_email}</b></td>
          <td><span style="color: #60a5fa;">${l.actual_recipient_email}</span></td>
          <td>${l.subject}</td>
          <td>${statusBadge}</td>
          <td>${l.is_test ? '🧪 Test' : (l.is_dry_run ? '📄 Dry-Run' : '🚀 Live')}</td>
          <td><small style="color: ${l.error_message ? '#f87171' : 'var(--text-muted)'};">${l.error_message || 'Delivered'}</small></td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {}
  },

  // ==================== SUPPRESSION ====================
  async loadSuppression() {
    try {
      const res = await fetch(`${API_BASE}/suppression`);
      const list = await res.json();
      const tbody = document.querySelector("#suppression-table tbody");
      tbody.innerHTML = "";

      if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Suppression list is empty.</td></tr>`;
        return;
      }

      list.forEach(s => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><b>${s.email}</b></td>
          <td>${s.reason}</td>
          <td>${new Date(s.created_at).toLocaleDateString()}</td>
          <td>
            <button class="btn btn-danger btn-sm" onclick="App.deleteSuppression(${s.id})"><i class="fa-solid fa-trash"></i></button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {}
  },

  async deleteSuppression(id) {
    await fetch(`${API_BASE}/suppression/${id}`, { method: "DELETE" });
    this.toast("Removed from suppression", "info");
    this.loadSuppression();
  },

  // ==================== SETTINGS & EMAIL ====================
  async loadSettings() {
    try {
      const res = await fetch(`${API_BASE}/settings/status`);
      const status = await res.json();
      this.state.systemStatus = status;

      // Populate SMTP Form
      const sBadge = document.getElementById("smtp-status-badge");
      if (status.smtp.configured) {
        sBadge.className = "badge badge-running";
        sBadge.innerHTML = `<span class="badge-dot"></span> Ready (${status.smtp.username})`;
      } else {
        sBadge.className = "badge badge-stopped";
        sBadge.innerHTML = `<span class="badge-dot"></span> Not Configured`;
      }

      document.getElementById("smtp-host").value = status.smtp.host || "smtp.gmail.com";
      document.getElementById("smtp-port").value = status.smtp.port || 587;
      document.getElementById("smtp-user").value = status.smtp.username || "";
      document.getElementById("smtp-tls").checked = status.smtp.use_tls;

      // Gemini
      const gBadge = document.getElementById("gemini-status-badge");
      if (status.gemini.configured) {
        gBadge.className = "badge badge-running";
        gBadge.innerHTML = `<span class="badge-dot"></span> Active (${status.gemini.masked_key})`;
      } else {
        gBadge.className = "badge badge-draft";
        gBadge.innerHTML = `<span class="badge-dot"></span> Not Configured`;
      }
    } catch (e) {}
  },

  async saveSmtp(event) {
    event.preventDefault();
    const payload = {
      host: document.getElementById("smtp-host").value,
      port: parseInt(document.getElementById("smtp-port").value),
      username: document.getElementById("smtp-user").value,
      password: document.getElementById("smtp-pass").value,
      use_tls: document.getElementById("smtp-tls").checked
    };

    const res = await fetch(`${API_BASE}/settings/smtp/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      this.toast("SMTP Credentials Saved!", "success");
      this.loadSettings();
    }
  },

  async testSmtp() {
    this.toast("Testing mail server connection...", "info");
    const payload = {
      host: document.getElementById("smtp-host").value,
      port: parseInt(document.getElementById("smtp-port").value),
      username: document.getElementById("smtp-user").value,
      password: document.getElementById("smtp-pass").value,
      use_tls: document.getElementById("smtp-tls").checked
    };

    const res = await fetch(`${API_BASE}/settings/smtp/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      this.toast("SMTP Connection Succeeded! Ready to send emails.", "success");
    } else {
      this.toast(`Connection Failed: ${data.error}`, "error");
    }
  },

  async saveGemini(event) {
    event.preventDefault();
    const key = document.getElementById("gemini-key").value;
    const res = await fetch(`${API_BASE}/settings/gemini/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: key })
    });
    if (res.ok) {
      this.toast("Gemini API Key Saved!", "success");
      this.loadSettings();
    }
  },

  // ==================== MODALS ====================
  openCreateCampaignModal() {
    document.getElementById("modal-create-campaign").style.display = "flex";
  },

  openCreateTemplateModal() {
    document.getElementById("modal-create-template").style.display = "flex";
  },

  openAddSuppressionModal() {
    document.getElementById("modal-add-suppression").style.display = "flex";
  },

  closeModals() {
    document.querySelectorAll(".modal-overlay").forEach(m => m.style.display = "none");
  },

  async submitCreateCampaign(event) {
    event.preventDefault();
    const payload = {
      name: document.getElementById("new-camp-name").value,
      description: document.getElementById("new-camp-desc").value,
      template_id: parseInt(document.getElementById("new-camp-template").value),
      sender_name: document.getElementById("new-camp-sender-name").value,
      sender_email: document.getElementById("new-camp-sender-email").value,
      ai_enabled: document.getElementById("new-camp-ai").checked,
      test_mode: document.getElementById("new-camp-test").checked,
      test_recipient: document.getElementById("new-camp-test-rec").value,
      dry_run: document.getElementById("new-camp-dry").checked,
      delay_seconds: parseInt(document.getElementById("new-camp-delay").value),
      daily_limit: parseInt(document.getElementById("new-camp-limit").value)
    };

    const res = await fetch(`${API_BASE}/campaigns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      this.toast("Campaign created successfully!", "success");
      this.closeModals();
      await this.loadCampaigns();
    }
  },

  async submitCreateTemplate(event) {
    event.preventDefault();
    const payload = {
      name: document.getElementById("new-tpl-name").value,
      description: document.getElementById("new-tpl-desc").value,
      subject: document.getElementById("new-tpl-subj").value,
      body: document.getElementById("new-tpl-body").value
    };

    const res = await fetch(`${API_BASE}/templates`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      this.toast("Template saved!", "success");
      this.closeModals();
      this.loadTemplates();
    }
  },

  async submitAddSuppression(event) {
    event.preventDefault();
    const email = document.getElementById("new-supp-email").value;
    const reason = document.getElementById("new-supp-reason").value;

    await fetch(`${API_BASE}/suppression`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, reason })
    });
    this.toast("Address Suppressed", "success");
    this.closeModals();
    this.loadSuppression();
  },

  // ==================== TOASTS ====================
  toast(msg, type = "info") {
    const container = document.getElementById("toast-container");
    const t = document.createElement("div");
    t.className = `toast toast-${type}`;
    const icon = type === "success" ? "fa-circle-check" : (type === "error" ? "fa-circle-exclamation" : "fa-circle-info");
    t.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${msg}</span>`;
    container.appendChild(t);
    setTimeout(() => {
      t.remove();
    }, 4000);
  }
};

document.addEventListener("DOMContentLoaded", () => {
  App.init();
});
