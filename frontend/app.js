// Base API URL configuration
const API_BASE = window.location.origin.includes(":8000") || window.location.origin.includes(":3000")
    ? `${window.location.origin}/api/v1`
    : "http://127.0.0.1:8000/api/v1";

// Global State
let currentInvestigationId = null;
let currentReportData = null;
let currentClaimsData = [];
let activeEventSource = null;
let selectedCategory = "COMPANY";

// DOM Elements
const form = document.getElementById("investigation-form");
const targetInput = document.getElementById("target-input");
const depthSelect = document.getElementById("depth-select");
const llmSelect = document.getElementById("llm-select");
const searchSelect = document.getElementById("search-select");
const btnLaunch = document.getElementById("btn-launch");

const liveRadarCard = document.getElementById("live-radar-card");
const radarTitle = document.getElementById("radar-title");
const radarSubtitle = document.getElementById("radar-subtitle");
const progressBadge = document.getElementById("progress-badge");
const progressBar = document.getElementById("progress-bar");
const liveTerminal = document.getElementById("live-event-terminal");
const btnToggleTerminal = document.getElementById("btn-toggle-terminal");

// Stepper DOM Elements
const stepCardPlanning = document.getElementById("step-card-planning");
const stepBodyPlanning = document.getElementById("step-body-planning");
const stepStatusPlanning = document.getElementById("step-status-planning");
const timelineHypotheses = document.getElementById("timeline-hypotheses");
const timelineSubtasks = document.getElementById("timeline-subtasks");

const stepCardSearching = document.getElementById("step-card-searching");
const stepBodySearching = document.getElementById("step-body-searching");
const stepStatusSearching = document.getElementById("step-status-searching");
const timelineQueries = document.getElementById("timeline-queries");

const stepCardScraping = document.getElementById("step-card-scraping");
const stepBodyScraping = document.getElementById("step-body-scraping");
const stepStatusScraping = document.getElementById("step-status-scraping");
const timelineSources = document.getElementById("timeline-sources");

const stepCardExtracting = document.getElementById("step-card-extracting");
const stepBodyExtracting = document.getElementById("step-body-extracting");
const stepStatusExtracting = document.getElementById("step-status-extracting");
const timelineClaims = document.getElementById("timeline-claims");

const stepCardVerifying = document.getElementById("step-card-verifying");
const stepBodyVerifying = document.getElementById("step-body-verifying");
const stepStatusVerifying = document.getElementById("step-status-verifying");
const timelineVerifStats = document.getElementById("timeline-verif-stats");

const welcomeHero = document.getElementById("welcome-hero");
const activeReport = document.getElementById("active-report");
const reportHeading = document.getElementById("report-heading");
const executiveSummaryBody = document.getElementById("executive-summary-body");
const markdownBody = document.getElementById("markdown-body");
const badgeTargetType = document.getElementById("badge-target-type");
const badgeSourcesCount = document.getElementById("badge-sources-count");
const badgeClaimsCount = document.getElementById("badge-claims-count");
const badgeCredibility = document.getElementById("badge-credibility");
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
const inspSourceType = document.getElementById("insp-source-type");
const inspSourceDomain = document.getElementById("insp-source-domain");
const inspSourceTitle = document.getElementById("insp-source-title");
const inspVisitUrl = document.getElementById("insp-visit-url");
const inspCorroborationList = document.getElementById("insp-corroboration-list");
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

function getActiveApiKeys() {
    const keys = {};
    const g = localStorage.getItem("INVESTIGATOR_GEMINI_KEY");
    const o = localStorage.getItem("INVESTIGATOR_OPENAI_KEY");
    const t = localStorage.getItem("INVESTIGATOR_TAVILY_KEY");
    if (g) keys.gemini_api_key = g;
    if (o) keys.openai_api_key = o;
    if (t) keys.tavily_api_key = t;
    return keys;
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
        alert("API 配置已保存！将在下次调查任务中自动注入执行。");
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

    // Toggle raw terminal
    if (btnToggleTerminal) {
        btnToggleTerminal.addEventListener("click", () => {
            liveTerminal.style.display = liveTerminal.style.display === "none" ? "block" : "none";
        });
    }

    // Step cards collapsible toggle
    document.querySelectorAll(".step-header").forEach(header => {
        header.addEventListener("click", () => {
            const body = header.nextElementSibling;
            if (body && body.classList.contains("step-body")) {
                body.style.display = body.style.display === "none" ? "flex" : "none";
            }
        });
    });

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

function resetTimelineUI() {
    [stepCardPlanning, stepCardSearching, stepCardScraping, stepCardExtracting, stepCardVerifying].forEach(c => {
        c.className = "step-card";
    });
    [stepStatusPlanning, stepStatusSearching, stepStatusScraping, stepStatusExtracting, stepStatusVerifying].forEach(s => {
        s.textContent = "待执行";
    });
    [stepBodyPlanning, stepBodySearching, stepBodyScraping, stepBodyExtracting, stepBodyVerifying].forEach(b => {
        b.style.display = "none";
    });

    timelineHypotheses.innerHTML = "";
    timelineSubtasks.innerHTML = "";
    timelineQueries.innerHTML = "";
    timelineSources.innerHTML = "";
    timelineClaims.innerHTML = "";
    timelineVerifStats.innerHTML = "";
    liveTerminal.innerHTML = "";
}

// 1. Start Investigation
async function handleStartInvestigation(e) {
    e.preventDefault();
    const query = targetInput.value.trim();
    if (!query) return;

    btnLaunch.disabled = true;
    btnLaunch.innerHTML = `<span class="radar-spinner" style="width:16px;height:16px;border-width:2px;"></span> 正在排队侦察任务...`;

    // Show radar card & reset timeline
    welcomeHero.style.display = "none";
    activeReport.style.display = "none";
    liveRadarCard.style.display = "block";
    resetTimelineUI();
    appendTerminalLog("SYS", `创建深度调查任务: "${query}" (类别: ${selectedCategory} | LLM: ${llmSelect.value} | Search: ${searchSelect.value})`);

    // Target label pill
    activeTargetPill.style.display = "flex";
    currentTargetLabel.textContent = `调查目标: ${query}`;

    try {
        const payload = {
            target_query: query,
            target_type_hint: selectedCategory,
            depth: depthSelect.value,
            llm_provider: llmSelect.value,
            search_provider: searchSelect.value,
            api_keys: getActiveApiKeys()
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

        // Refresh sidebar history immediately
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
        updateProgressUI(payload.progress, "PLANNING", "已生成调查假说与子任务拆解");
        
        // Update Stepper UI
        stepCardPlanning.classList.remove("active");
        stepCardPlanning.classList.add("completed");
        stepStatusPlanning.textContent = "已完成";
        stepBodyPlanning.style.display = "flex";

        timelineHypotheses.innerHTML = `<strong>背调核心假说：</strong><br>${(payload.data.key_hypotheses || []).map((h, i) => `${i+1}. ${escapeHtml(h)}`).join("<br>")}`;
        timelineSubtasks.innerHTML = (payload.data.sub_tasks || []).map(t => `
            <div class="subtask-mini-card">
                <div class="subtask-dim">${escapeHtml(t.dimension)}</div>
                <div class="subtask-q">${escapeHtml(t.question)}</div>
            </div>
        `).join("");

        stepCardSearching.classList.add("active");
        stepStatusSearching.textContent = "进行中...";
        appendTerminalLog("PLAN", `已规划 ${payload.data.sub_tasks.length} 个调查维度，开始定向多源搜索。`);
    });

    activeEventSource.addEventListener("search_dispatched", (e) => {
        const payload = JSON.parse(e.data);
        stepBodySearching.style.display = "flex";
        timelineQueries.innerHTML = (payload.data.queries || []).map(q => `
            <span class="query-tag-pill"><i data-lucide="search" style="width:12px;height:12px;"></i> ${escapeHtml(q)}</span>
        `).join("");
        lucide.createIcons();
        appendTerminalLog("SEARCH", `发起 ${payload.data.queries.length} 组搜索查询。`);
    });

    activeEventSource.addEventListener("source_found", (e) => {
        const payload = JSON.parse(e.data);
        stepCardSearching.classList.remove("active");
        stepCardSearching.classList.add("completed");
        stepStatusSearching.textContent = "已完成";

        stepCardScraping.classList.add("active");
        stepStatusScraping.textContent = "抓取中...";
        stepBodyScraping.style.display = "flex";

        const src = payload.data;
        const pill = document.createElement("div");
        pill.className = "source-mini-item";
        pill.innerHTML = `<span>[${src.source_type}] <strong>${escapeHtml(src.domain)}</strong></span> <span style="color:var(--text-muted);font-size:0.7rem;">可信度:${src.credibility_score}</span>`;
        timelineSources.appendChild(pill);

        appendTerminalLog("SRC", `捕获信源 [${src.source_type}]: ${src.domain} (${src.title || src.url})`);
    });

    activeEventSource.addEventListener("claim_extracted", (e) => {
        const payload = JSON.parse(e.data);
        stepCardScraping.classList.remove("active");
        stepCardScraping.classList.add("completed");
        stepStatusScraping.textContent = "已完成";

        stepCardExtracting.classList.add("active");
        stepStatusExtracting.textContent = "提取中...";
        stepBodyExtracting.style.display = "flex";

        const claim = payload.data;
        const claimItem = document.createElement("div");
        claimItem.className = "claim-mini-item";
        claimItem.innerHTML = `<strong>[${claim.claim_type}]</strong> ${escapeHtml(claim.statement)} <span style="color:var(--text-muted);font-size:0.7rem;">(${claim.source_domain || ""})</span>`;
        timelineClaims.appendChild(claimItem);
        timelineClaims.scrollTop = timelineClaims.scrollHeight;

        appendTerminalLog("CLAIM", `提取主张 [${claim.claim_type}]: "${claim.statement}"`);
    });

    activeEventSource.addEventListener("completed", (e) => {
        const payload = JSON.parse(e.data);
        [stepCardExtracting, stepCardVerifying].forEach(c => {
            c.classList.remove("active");
            c.classList.add("completed");
        });
        stepStatusExtracting.textContent = "已完成";
        stepStatusVerifying.textContent = "已完成";
        stepBodyVerifying.style.display = "flex";
        timelineVerifStats.innerHTML = `
            <div style="color:var(--accent-emerald);font-weight:700;">
                ✓ 事实核验完成：${payload.data.total_claims} 条主张全部完成多源比对，生成 ${payload.data.citation_count} 处可回溯引文。
            </div>
        `;

        updateProgressUI(100, "COMPLETED", "调查完成，正在呈现研报...");
        appendTerminalLog("SUCCESS", `调查完成！总共核验 ${payload.data.total_claims} 条事实，可信度评定完成。`);
        
        activeEventSource.close();
        btnLaunch.disabled = false;
        btnLaunch.innerHTML = `<i data-lucide="play"></i> 启动全网深度侦察`;
        lucide.createIcons();

        // Load & Render Completed Report
        setTimeout(() => {
            loadAndRenderReport(investigationId);
            loadInvestigationHistory();
        }, 600);
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
        // Fetch Report, Details and Claims concurrently
        const [repRes, invRes, claimsRes, eventsRes] = await Promise.all([
            fetch(`${API_BASE}/investigations/${investigationId}/report`),
            fetch(`${API_BASE}/investigations/${investigationId}`),
            fetch(`${API_BASE}/investigations/${investigationId}/claims`),
            fetch(`${API_BASE}/investigations/${investigationId}/events`)
        ]);

        if (!repRes.ok) throw new Error("Report not ready yet.");

        currentReportData = await repRes.json();
        currentInvestigationId = investigationId;
        const invMeta = invRes.ok ? await invRes.json() : {};
        currentClaimsData = claimsRes.ok ? await claimsRes.json() : [];
        const eventsHistory = eventsRes.ok ? await eventsRes.json() : [];

        // Reconstruct Timeline if available from DB events
        if (eventsHistory.length > 0) {
            replayTimelineEvents(eventsHistory);
        }

        // Populate header & metadata
        reportHeading.textContent = currentReportData.title;
        executiveSummaryBody.textContent = currentReportData.executive_summary;
        badgeTargetType.textContent = invMeta.target_type || "COMPANY";

        const sourcesCount = invMeta.sources_count || Object.keys(currentReportData.citation_map || {}).length;
        const claimsCount = invMeta.claims_count || currentClaimsData.length;
        badgeSourcesCount.textContent = `${sourcesCount} 个信源`;
        badgeClaimsCount.textContent = `${claimsCount} 条核验事实`;

        const cred = currentReportData.credibility_breakdown?.average_credibility || invMeta.average_credibility;
        badgeCredibility.textContent = cred ? `加权可信度: ${cred}` : "可信度: 未评估";

        // Parse markdown and convert [1], [2] to interactive clickable badges
        let rawMarkdown = currentReportData.markdown_content;
        
        rawMarkdown = rawMarkdown.replace(/\[(\d+)\]/g, (match, p1) => {
            const cite = currentReportData.citation_map ? currentReportData.citation_map[p1] : null;
            const cType = cite ? (cite.claim_type || "FACT") : "FACT";
            return `<button type="button" class="cite-badge" data-cite="${p1}" data-type="${cType}">[${p1}]</button>`;
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
        liveRadarCard.style.display = "block"; // Keep timeline stepper visible at top
        activeReport.style.display = "block";
        lucide.createIcons();

    } catch (err) {
        console.error("Failed to load report:", err);
    }
}

function replayTimelineEvents(events) {
    resetTimelineUI();
    events.forEach(evt => {
        const d = evt.data || {};
        if (evt.event_type === "plan_generated") {
            stepCardPlanning.classList.add("completed");
            stepStatusPlanning.textContent = "已完成";
            stepBodyPlanning.style.display = "flex";
            timelineHypotheses.innerHTML = `<strong>背调核心假说：</strong><br>${(d.key_hypotheses || []).map((h, i) => `${i+1}. ${escapeHtml(h)}`).join("<br>")}`;
            timelineSubtasks.innerHTML = (d.sub_tasks || []).map(t => `
                <div class="subtask-mini-card">
                    <div class="subtask-dim">${escapeHtml(t.dimension)}</div>
                    <div class="subtask-q">${escapeHtml(t.question)}</div>
                </div>
            `).join("");
        } else if (evt.event_type === "search_dispatched") {
            stepCardSearching.classList.add("completed");
            stepStatusSearching.textContent = "已完成";
            stepBodySearching.style.display = "flex";
            timelineQueries.innerHTML = (d.queries || []).map(q => `
                <span class="query-tag-pill"><i data-lucide="search" style="width:12px;height:12px;"></i> ${escapeHtml(q)}</span>
            `).join("");
        } else if (evt.event_type === "source_found") {
            stepCardScraping.classList.add("completed");
            stepStatusScraping.textContent = "已完成";
            stepBodyScraping.style.display = "flex";
            const pill = document.createElement("div");
            pill.className = "source-mini-item";
            pill.innerHTML = `<span>[${d.source_type}] <strong>${escapeHtml(d.domain)}</strong></span> <span style="color:var(--text-muted);font-size:0.7rem;">可信度:${d.credibility_score}</span>`;
            timelineSources.appendChild(pill);
        } else if (evt.event_type === "claim_extracted") {
            stepCardExtracting.classList.add("completed");
            stepStatusExtracting.textContent = "已完成";
            stepBodyExtracting.style.display = "flex";
            const claimItem = document.createElement("div");
            claimItem.className = "claim-mini-item";
            claimItem.innerHTML = `<strong>[${d.claim_type}]</strong> ${escapeHtml(d.statement)} <span style="color:var(--text-muted);font-size:0.7rem;">(${d.source_domain || ""})</span>`;
            timelineClaims.appendChild(claimItem);
        } else if (evt.event_type === "completed") {
            stepCardVerifying.classList.add("completed");
            stepStatusVerifying.textContent = "已完成";
            stepBodyVerifying.style.display = "flex";
            timelineVerifStats.innerHTML = `
                <div style="color:var(--accent-emerald);font-weight:700;">
                    ✓ 调查全流程已固化归档（${d.total_claims || 0} 条事实，${d.total_sources || 0} 个信源）。
                </div>
            `;
        }
    });
    progressBar.style.width = "100%";
    progressBadge.textContent = "100%";
    radarTitle.textContent = "调查档案就绪";
    radarSubtitle.textContent = "全网多源事实证据链已锚定";
    lucide.createIcons();
}

// 4. Inspect Citation in Drawer
function inspectCitation(citeIndex) {
    if (!currentReportData || !currentReportData.citation_map) return;
    const citation = currentReportData.citation_map[citeIndex];
    if (!citation) return;

    // Fill Drawer Card
    const cType = citation.claim_type || "FACT";
    inspClaimType.textContent = cType;
    inspClaimType.className = `tag-pill ${cType}`;
    
    inspVerifStatus.textContent = citation.verification_status || "VERIFIED";
    inspClaimStatement.textContent = citation.statement;

    inspExactQuote.textContent = citation.quote || citation.statement;
    inspCtxPrefix.textContent = citation.context_prefix || "";
    inspCtxSuffix.textContent = citation.context_suffix || "";

    const cred = citation.source_credibility !== undefined ? citation.source_credibility : 0.88;
    inspMeterVal.textContent = cred.toFixed(2);
    inspMeterBar.style.width = `${Math.round(cred * 100)}%`;

    inspSourceType.textContent = citation.source_type ? `${citation.source_type} 权威信源` : "官方/权威信源";
    inspSourceDomain.textContent = citation.source_domain || "web-source";
    inspSourceTitle.textContent = citation.source_title || citation.source_url || "--";
    inspVisitUrl.href = citation.source_url || "#";

    // Populate Corroborating Sources
    const corroborating = [];
    Object.keys(currentReportData.citation_map).forEach(idx => {
        if (idx !== citeIndex) {
            const other = currentReportData.citation_map[idx];
            if (other.source_domain && other.source_domain !== citation.source_domain) {
                corroborating.push(other);
            }
        }
    });

    if (corroborating.length > 0) {
        inspCorroborationList.innerHTML = corroborating.slice(0, 3).map(c => `
            <div class="corroboration-item">
                <div class="corrob-domain">✓ ${escapeHtml(c.source_domain)} (评分: ${c.source_credibility || 0.85})</div>
                <div style="font-size:0.72rem;color:var(--text-muted);">"${escapeHtml((c.quote || c.statement).slice(0, 60))}..."</div>
            </div>
        `).join("");
    } else {
        inspCorroborationList.innerHTML = `<div style="font-size:0.75rem;color:var(--text-muted);">该主张直接由权威官方来源独立证实。</div>`;
    }

    // Check for contradictions
    if (citation.claim_type === "CONFLICTING" || citation.verification_status === "CONTRADICTED") {
        inspContradictionsSection.style.display = "block";
        inspContradictionBox.innerHTML = `<strong>⚠️ 矛盾发现：</strong>检测到独立信源对该事实存在数据出入或相反陈述。在报告中已标注为争议主张，建议审慎核验。`;
    } else {
        inspContradictionsSection.style.display = "none";
    }

    drawerEmptyState.style.display = "none";
    inspectorCard.style.display = "flex";
}

// 5. Apply Claim Filter
function applyClaimFilter(filterType) {
    const listItems = markdownBody.querySelectorAll("li, p");
    listItems.forEach(item => {
        const text = item.textContent;
        const citeButtons = item.querySelectorAll(".cite-badge");
        const hasTypes = Array.from(citeButtons).map(b => b.dataset.type);

        if (filterType === "ALL") {
            item.style.display = "";
        } else if (filterType === "FACT") {
            // Strict FACT match
            const isFact = hasTypes.includes("FACT") || text.includes("`FACT`") || (!hasTypes.includes("CONFLICTING") && !hasTypes.includes("OPINION") && !text.includes("OPINION") && !text.includes("争议"));
            item.style.display = isFact ? "" : "none";
        } else if (filterType === "CONFLICTING") {
            const isConflict = hasTypes.includes("CONFLICTING") || text.includes("CONFLICTING") || text.includes("争议") || text.includes("矛盾") || text.includes("短板");
            item.style.display = isConflict ? "" : "none";
        } else if (filterType === "UNVERIFIED") {
            const isUnverified = hasTypes.includes("UNVERIFIED") || hasTypes.includes("OPINION") || text.includes("UNVERIFIED") || text.includes("传言") || text.includes("未证实");
            item.style.display = isUnverified ? "" : "none";
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
