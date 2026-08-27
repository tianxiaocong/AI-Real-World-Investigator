// Base API URL configuration
const API_BASE = window.location.origin.includes(":8000") || window.location.origin.includes(":3000")
    ? `${window.location.origin}/api/v1`
    : "http://127.0.0.1:8000/api/v1";

// Global State
let currentInvestigationId = null;
let currentReportData = null;
let activeEventSource = null;
let selectedCategory = "COMPANY";

// DOM Elements
const form = document.getElementById("investigation-form");
const targetInput = document.getElementById("target-input");
const depthSelect = document.getElementById("depth-select");
const llmSelect = document.getElementById("llm-select");
const btnLaunch = document.getElementById("btn-launch");

const liveRadarCard = document.getElementById("live-radar-card");
const radarTitle = document.getElementById("radar-title");
const radarSubtitle = document.getElementById("radar-subtitle");
const progressBadge = document.getElementById("progress-badge");
const progressBar = document.getElementById("progress-bar");
const liveTerminal = document.getElementById("live-event-terminal");

const welcomeHero = document.getElementById("welcome-hero");
const activeReport = document.getElementById("active-report");
const reportHeading = document.getElementById("report-heading");
const executiveSummaryBody = document.getElementById("executive-summary-body");
const markdownBody = document.getElementById("markdown-body");
const badgeTargetType = document.getElementById("badge-target-type");
const badgeSourcesCount = document.getElementById("badge-sources-count");
const badgeClaimsCount = document.getElementById("badge-claims-count");
const dossierList = document.getElementById("dossier-list");

const activeTargetPill = document.getElementById("active-target-pill");
const currentTargetLabel = document.getElementById("current-target-label");

// Settings Modal Elements
const btnOpenSettings = document.getElementById("btn-open-settings");
const settingsModal = document.getElementById("settings-modal");
const btnCloseSettings = document.getElementById("btn-close-settings");
const btnCancelSettings = document.getElementById("btn-cancel-settings");
const btnSaveSettings = document.getElementById("btn-save-settings");
const setGeminiKey = document.getElementById("set-gemini-key");
const setOpenaiKey = document.getElementById("set-openai-key");
const setTavilyKey = document.getElementById("set-tavily-key");

// Evidence Drawer Elements
const evidenceDrawer = document.getElementById("evidence-drawer");
const inspectorCard = document.getElementById("inspector-card");
const drawerEmptyState = document.querySelector(".drawer-empty-state");
const btnCloseDrawer = document.getElementById("btn-close-drawer");

const inspClaimType = document.getElementById("insp-claim-type");
const inspVerifStatus = document.getElementById("insp-verif-status");
const inspClaimStatement = document.getElementById("insp-claim-statement");
const inspExactQuote = document.getElementById("insp-exact-quote");
const inspCtxPrefix = document.getElementById("insp-ctx-prefix");
const inspCtxSuffix = document.getElementById("insp-ctx-suffix");
const inspMeterBar = document.getElementById("insp-meter-bar");
const inspMeterVal = document.getElementById("insp-meter-val");
const inspSourceDomain = document.getElementById("insp-source-domain");
const inspSourceTitle = document.getElementById("insp-source-title");
const inspVisitUrl = document.getElementById("insp-visit-url");
const inspContradictionsSection = document.getElementById("insp-contradictions-section");
const inspContradictionBox = document.getElementById("insp-contradiction-box");

// Initialization
document.addEventListener("DOMContentLoaded", () => {
    lucide.createIcons();
    loadSavedSettings();
    setupEventListeners();
    loadInvestigationHistory();
});

function loadSavedSettings() {
    if (localStorage.getItem("INVESTIGATOR_GEMINI_KEY")) {
        setGeminiKey.value = localStorage.getItem("INVESTIGATOR_GEMINI_KEY");
    }
    if (localStorage.getItem("INVESTIGATOR_OPENAI_KEY")) {
        setOpenaiKey.value = localStorage.getItem("INVESTIGATOR_OPENAI_KEY");
    }
    if (localStorage.getItem("INVESTIGATOR_TAVILY_KEY")) {
        setTavilyKey.value = localStorage.getItem("INVESTIGATOR_TAVILY_KEY");
    }
}

function setupEventListeners() {
    // Settings Modal
    btnOpenSettings.addEventListener("click", () => settingsModal.style.display = "flex");
    btnCloseSettings.addEventListener("click", () => settingsModal.style.display = "none");
    btnCancelSettings.addEventListener("click", () => settingsModal.style.display = "none");
    btnSaveSettings.addEventListener("click", () => {
        localStorage.setItem("INVESTIGATOR_GEMINI_KEY", setGeminiKey.value.trim());
        localStorage.setItem("INVESTIGATOR_OPENAI_KEY", setOpenaiKey.value.trim());
        localStorage.setItem("INVESTIGATOR_TAVILY_KEY", setTavilyKey.value.trim());
        settingsModal.style.display = "none";
        alert("API 配置已保存！");
    });
    // Preset chip category selection
    document.querySelectorAll(".preset-chips .chip").forEach(chip => {
        chip.addEventListener("click", () => {
            document.querySelectorAll(".preset-chips .chip").forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            selectedCategory = chip.dataset.type;
        });
    });

    // Form submit
    form.addEventListener("submit", handleStartInvestigation);

    // Refresh history
    document.getElementById("btn-refresh-history").addEventListener("click", loadInvestigationHistory);

    // Close evidence drawer
    btnCloseDrawer.addEventListener("click", () => {
        inspectorCard.style.display = "none";
        drawerEmptyState.style.display = "block";
    });

    // Export buttons
    document.getElementById("btn-export-md").addEventListener("click", () => exportReport("markdown"));
    document.getElementById("btn-export-json").addEventListener("click", () => exportReport("json"));

    // Claim category filter buttons
    document.querySelectorAll(".claim-filter-bar .filter-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".claim-filter-bar .filter-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            applyClaimFilter(btn.dataset.filter);
        });
    });
}

// 1. Start Investigation
async function handleStartInvestigation(e) {
    e.preventDefault();
    const query = targetInput.value.trim();
    if (!query) return;

    btnLaunch.disabled = true;
    btnLaunch.innerHTML = `<span class="radar-spinner" style="width:16px;height:16px;border-width:2px;"></span> 正在排队侦察任务...`;

    // Show radar card
    welcomeHero.style.display = "none";
    activeReport.style.display = "none";
    liveRadarCard.style.display = "block";
    liveTerminal.innerHTML = "";
    appendTerminalLog("SYS", `创建深度调查任务: "${query}" (类别: ${selectedCategory})`);

    // Target label pill
    activeTargetPill.style.display = "flex";
    currentTargetLabel.textContent = `调查目标: ${query}`;

    try {
        const payload = {
            target_query: query,
            target_type_hint: selectedCategory,
            depth: depthSelect.value,
            llm_provider: llmSelect.value
        };

        const response = await fetch(`${API_BASE}/investigations`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const invData = await response.json();
        currentInvestigationId = invData.id;
        appendTerminalLog("SYS", `任务 ID: ${invData.id} 已生成，正在建立实时 SSE 雷达事件总线...`);

        // Refresh sidebar history immediately so the new dossier shows up
        loadInvestigationHistory();

        // Connect SSE
        connectSSEStream(invData.id);

    } catch (err) {
        console.error("Failed to start investigation:", err);
        appendTerminalLog("ERR", `启动失败: ${err.message}`);
        btnLaunch.disabled = false;
        btnLaunch.innerHTML = `<i data-lucide="play"></i> 启动全网深度侦察`;
        lucide.createIcons();
    }
}

// 2. Connect Server-Sent Events (SSE)
function connectSSEStream(investigationId) {
    if (activeEventSource) {
        activeEventSource.close();
    }

    activeEventSource = new EventSource(`${API_BASE}/investigations/${investigationId}/stream`);

    activeEventSource.addEventListener("progress", (e) => {
        const payload = JSON.parse(e.data);
        updateProgressUI(payload.progress, payload.stage, payload.data.message);
        appendTerminalLog(payload.stage, payload.data.message);
    });

    activeEventSource.addEventListener("plan_generated", (e) => {
        const payload = JSON.parse(e.data);
        updateProgressUI(payload.progress, "PLANNING", "已生成子课题规划");
        appendTerminalLog("PLAN", `已规划 ${payload.data.sub_tasks.length} 个调查维度，假设: ${payload.data.key_hypotheses.join(" / ")}`);
    });

    activeEventSource.addEventListener("source_found", (e) => {
        const payload = JSON.parse(e.data);
        appendTerminalLog("SRC", `捕获信源 [${payload.data.source_type}]: ${payload.data.domain} (权威分: ${payload.data.credibility_score}) - ${payload.data.title || payload.data.url}`);
    });

    activeEventSource.addEventListener("claim_extracted", (e) => {
        const payload = JSON.parse(e.data);
        appendTerminalLog("CLAIM", `提取主张 [${payload.data.claim_type}]: "${payload.data.statement}" (${payload.data.source_domain})`);
    });

    activeEventSource.addEventListener("completed", (e) => {
        const payload = JSON.parse(e.data);
        updateProgressUI(100, "COMPLETED", "调查完成，正在呈现研报...");
        appendTerminalLog("SUCCESS", `调查完成！共提取 ${payload.data.total_claims} 条主张，绑定 ${payload.data.citation_count} 处可回溯引用。`);
        
        activeEventSource.close();
        btnLaunch.disabled = false;
        btnLaunch.innerHTML = `<i data-lucide="play"></i> 启动全网深度侦察`;
        lucide.createIcons();

        // Load & Render Completed Report
        setTimeout(() => {
            loadAndRenderReport(investigationId);
            loadInvestigationHistory();
        }, 800);
    });

    activeEventSource.addEventListener("error", (e) => {
        console.warn("SSE Error or task failed:", e);
        if (e.data) {
            try {
                const payload = JSON.parse(e.data);
                appendTerminalLog("ERR", `异常: ${payload.data?.error || "连接异常"}`);
            } catch (_) {}
        }
        btnLaunch.disabled = false;
        btnLaunch.innerHTML = `<i data-lucide="play"></i> 启动全网深度侦察`;
        lucide.createIcons();
    });
}

function updateProgressUI(percentage, stage, message) {
    progressBar.style.width = `${percentage}%`;
    progressBadge.textContent = `${percentage}%`;
    radarTitle.textContent = message || "正在深度侦察...";
    radarSubtitle.textContent = `当前阶段: ${stage}`;
}

function appendTerminalLog(tag, message) {
    const line = document.createElement("div");
    line.className = "terminal-line";
    line.innerHTML = `<span class="t-time">[${tag}]</span> ${escapeHtml(message)}`;
    liveTerminal.appendChild(line);
    liveTerminal.scrollTop = liveTerminal.scrollHeight;
}

// 3. Load & Render Report
async function loadAndRenderReport(investigationId) {
    try {
        const response = await fetch(`${API_BASE}/investigations/${investigationId}/report`);
        if (!response.ok) throw new Error("Report not ready yet.");

        currentReportData = await response.json();
        currentInvestigationId = investigationId;

        // Populate header & metadata
        reportHeading.textContent = currentReportData.title;
        executiveSummaryBody.textContent = currentReportData.executive_summary;

        const breakdown = currentReportData.credibility_breakdown || {};
        const claimsDist = breakdown.claims_distribution || {};
        badgeClaimsCount.textContent = `${claimsDist.total || Object.keys(currentReportData.citation_map).length} Claims`;
        badgeSourcesCount.textContent = `Avg Credibility: ${breakdown.average_credibility || 0.85}`;

        // Parse markdown and convert [1], [2] to interactive clickable badges
        let rawMarkdown = currentReportData.markdown_content;
        
        // Convert [1], [2] citation markers into HTML interactive buttons
        rawMarkdown = rawMarkdown.replace(/\[(\d+)\]/g, (match, p1) => {
            return `<button type="button" class="cite-badge" data-cite="${p1}">[${p1}]</button>`;
        });

        markdownBody.innerHTML = marked.parse(rawMarkdown);

        // Bind click events on all citation buttons
        document.querySelectorAll(".cite-badge").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                e.stopPropagation();
                const citeIndex = btn.dataset.cite;
                inspectCitation(citeIndex);
            });
        });

        // Show report UI
        welcomeHero.style.display = "none";
        liveRadarCard.style.display = "none";
        activeReport.style.display = "block";

    } catch (err) {
        console.error("Failed to load report:", err);
    }
}

// 4. Inspect Citation in Drawer
function inspectCitation(citeIndex) {
    if (!currentReportData || !currentReportData.citation_map) return;
    const citation = currentReportData.citation_map[citeIndex];
    if (!citation) return;

    // Fill Drawer Card
    inspClaimType.textContent = citation.claim_type || "FACT";
    inspClaimType.className = `tag-pill ${citation.claim_type || "FACT"}`;
    
    inspVerifStatus.textContent = citation.verification_status || "VERIFIED";
    inspClaimStatement.textContent = citation.statement;

    inspExactQuote.textContent = citation.quote || citation.statement;
    inspCtxPrefix.textContent = citation.context_prefix || "";
    inspCtxSuffix.textContent = citation.context_suffix || "";

    const cred = citation.source_credibility || 0.5;
    inspMeterVal.textContent = cred.toFixed(2);
    inspMeterBar.style.width = `${Math.round(cred * 100)}%`;

    inspSourceDomain.textContent = citation.source_domain || "web-source";
    inspSourceTitle.textContent = citation.source_title || citation.source_url || "--";
    inspVisitUrl.href = citation.source_url || "#";

    // Check for contradictions
    if (citation.claim_type === "CONFLICTING" || citation.verification_status === "CONTRADICTED") {
        inspContradictionsSection.style.display = "block";
        inspContradictionBox.innerHTML = `<strong>⚠️ 矛盾发现：</strong>该陈述存在相互对立或数据不一的独立来源，建议重点参考权威官方披露。`;
    } else {
        inspContradictionsSection.style.display = "none";
    }

    drawerEmptyState.style.display = "none";
    inspectorCard.style.display = "flex";
}

// 5. Apply Claim Filter
function applyClaimFilter(filterType) {
    const listItems = markdownBody.querySelectorAll("li");
    listItems.forEach(item => {
        const text = item.textContent;
        if (filterType === "ALL") {
            item.style.display = "";
        } else if (filterType === "FACT") {
            item.style.display = text.includes("FACT") || !text.includes("CONFLICTING") ? "" : "none";
        } else if (filterType === "CONFLICTING") {
            item.style.display = text.includes("CONFLICTING") || text.includes("CONTRADICTED") || text.includes("争议") || text.includes("矛盾") ? "" : "none";
        } else if (filterType === "UNVERIFIED") {
            item.style.display = text.includes("UNVERIFIED") || text.includes("传言") || text.includes("未验证") ? "" : "none";
        }
    });
}

// 6. Export Report
function exportReport(format) {
    if (!currentInvestigationId) return;
    window.open(`${API_BASE}/investigations/${currentInvestigationId}/export?format=${format}`, "_blank");
}

// 7. Load History Dossiers
async function loadInvestigationHistory() {
    try {
        const response = await fetch(`${API_BASE}/investigations?limit=15`);
        if (!response.ok) return;

        const history = await response.json();
        if (!history || history.length === 0) {
            dossierList.innerHTML = `<div class="empty-state"><i data-lucide="inbox"></i><p>暂无历史调查档案</p></div>`;
            lucide.createIcons();
            return;
        }

        dossierList.innerHTML = "";
        history.forEach(item => {
            const card = document.createElement("div");
            card.className = `dossier-item ${item.id === currentInvestigationId ? "active" : ""}`;
            
            let statusBadge = "";
            if (item.status === "COMPLETED") {
                statusBadge = `<span style="color:var(--accent-emerald);font-size:0.7rem;font-weight:700;">● 已完成</span>`;
            } else if (item.status === "FAILED") {
                statusBadge = `<span style="color:var(--accent-rose);font-size:0.7rem;font-weight:700;">● 异常</span>`;
            } else {
                statusBadge = `<span style="color:var(--accent-cyan);font-size:0.7rem;font-weight:700;">● 侦察中 (${item.progress_percentage}%)</span>`;
            }

            card.innerHTML = `
                <div class="dossier-title">${escapeHtml(item.title || item.target_query)}</div>
                <div class="dossier-meta">
                    <span>${item.target_type} • ${item.sources_count || 0} 信源 • ${item.claims_count || 0} 事实</span>
                    ${statusBadge}
                </div>
            `;
            card.addEventListener("click", () => {
                document.querySelectorAll(".dossier-item").forEach(d => d.classList.remove("active"));
                card.classList.add("active");
                if (item.status === "COMPLETED") {
                    loadAndRenderReport(item.id);
                } else if (item.status === "FAILED") {
                    alert(`该调查未成功完成: ${item.error_message || "未知原因"}`);
                } else {
                    currentInvestigationId = item.id;
                    activeTargetPill.style.display = "flex";
                    currentTargetLabel.textContent = `调查目标: ${item.target_query}`;
                    welcomeHero.style.display = "none";
                    activeReport.style.display = "none";
                    liveRadarCard.style.display = "block";
                    connectSSEStream(item.id);
                }
            });
            dossierList.appendChild(card);
        });

    } catch (err) {
        console.warn("Failed to load history:", err);
    }
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
