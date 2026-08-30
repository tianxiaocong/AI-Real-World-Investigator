// AI Real-World Investigator — Professional Research Workstation Controller
// Architecture: Evidence First · Auditability First · Deterministic Verdict

const API_BASE = window.location.origin.includes(":8000") || window.location.origin.includes(":3000")
    ? `${window.location.origin}/api/v1`
    : "http://127.0.0.1:8000/api/v1";

// ──────────────────────────────────────────────
//  Global State
// ──────────────────────────────────────────────
let currentCoverage = null;
let selectedClaimId = null;
let selectedEvidenceId = null;
let selectedSourceId = null;
let activeInspectorTab = "audit"; // "audit" | "provenance" | "quote"
let currentInputMode = "TEXT";    // "TEXT" | "URL" | "IMAGE"
let currentUploadedImageBase64 = null;

// ──────────────────────────────────────────────
//  DOM Elements
// ──────────────────────────────────────────────
const viewHome = document.getElementById("view-home");
const viewLoading = document.getElementById("view-loading");
const viewWorkspace = document.getElementById("view-workspace");

// Header
const btnBrandHome = document.getElementById("btn-brand-home");
const btnEngineStatus = document.getElementById("btn-engine-status");
const headerEngineLabel = document.getElementById("header-engine-label");
const btnOpenArchive = document.getElementById("btn-open-archive");
const archiveCountBadge = document.getElementById("archive-count-badge");
const btnOpenSettings = document.getElementById("btn-open-settings");
const btnHeaderNewVerify = document.getElementById("btn-header-new-verify");

// Home View
const verifyForm = document.getElementById("verify-form");
const claimInput = document.getElementById("claim-input");
const btnSubmitVerify = document.getElementById("btn-submit-verify");
const imageFileInput = document.getElementById("image-file-input");
const imagePreviewContainer = document.getElementById("image-preview-container");
const imagePreviewEl = document.getElementById("image-preview-el");
const previewFilenameLabel = document.getElementById("preview-filename-label");
const btnRemoveImage = document.getElementById("btn-remove-image");

// Loading View
const loadingStageTitle = document.getElementById("loading-stage-title");
const loadingClaimText = document.getElementById("loading-claim-text");
const loadingSubstatusText = document.getElementById("loading-substatus-text");

// Workspace View
const wsOriginalClaimText = document.getElementById("ws-original-claim-text");
const wsOverallVerdictBadge = document.getElementById("ws-overall-verdict-badge");
const wsOverallVerdictText = document.getElementById("ws-overall-verdict-text");
const metricClaimsCount = document.getElementById("metric-claims-count");
const metricEvidenceCount = document.getElementById("metric-evidence-count");
const metricOriginsCount = document.getElementById("metric-origins-count");
const metricContradictionsCount = document.getElementById("metric-contradictions-count");
const btnWsCopyReport = document.getElementById("btn-ws-copy-report");
const btnWsExportMd = document.getElementById("btn-ws-export-md");
const btnWsNewInvestigation = document.getElementById("btn-ws-new-investigation");

// Column 1: Claims
const claimsExplorerCount = document.getElementById("claims-explorer-count");
const claimsNavList = document.getElementById("claims-nav-list");

// Column 2: Evidence Workspace
const wsClaimIndexTag = document.getElementById("ws-claim-index-tag");
const wsSelectedClaimStatement = document.getElementById("ws-selected-claim-statement");
const wsVerdictBanner = document.getElementById("ws-verdict-banner");
const wsVerdictStateChip = document.getElementById("ws-verdict-state-chip");
const wsVerdictSummaryHuman = document.getElementById("ws-verdict-summary-human");
const wsWhyReasonsList = document.getElementById("ws-why-reasons-list");
const wsGapsContainer = document.getElementById("ws-gaps-container");
const wsGapsList = document.getElementById("ws-gaps-list");
const wsAdviceContainer = document.getElementById("ws-advice-container");
const wsAdviceText = document.getElementById("ws-advice-text");
const wsSupportingCount = document.getElementById("ws-supporting-count");
const wsSupportingEvidenceList = document.getElementById("ws-supporting-evidence-list");
const wsContradictingCount = document.getElementById("ws-contradicting-count");
const wsContradictingEvidenceList = document.getElementById("ws-contradicting-evidence-list");
const wsContextSection = document.getElementById("ws-context-section");
const wsContextCount = document.getElementById("ws-context-count");
const wsContextEvidenceList = document.getElementById("ws-context-evidence-list");

// Column 3: Inspector
const auditMetricsGrid = document.getElementById("audit-metrics-grid");
const auditFactslotsCard = document.getElementById("audit-factslots-card");
const auditFactslotsContent = document.getElementById("audit-factslots-content");
const auditMultiroundCard = document.getElementById("audit-multiround-card");
const auditMultiroundContent = document.getElementById("audit-multiround-content");
const provenanceLineageContainer = document.getElementById("provenance-lineage-container");
const quoteInspectorContainer = document.getElementById("quote-inspector-container");

// Modals & Drawers
const settingsModal = document.getElementById("settings-modal");
const btnCloseSettingsX = document.getElementById("btn-close-settings-x");
const btnCancelSettings = document.getElementById("btn-cancel-settings");
const btnSaveSettings = document.getElementById("btn-save-settings");
const cfgLlmProvider = document.getElementById("cfg-llm-provider");
const cfgSearchProvider = document.getElementById("cfg-search-provider");
const cfgSensenovaKey = document.getElementById("cfg-sensenova-key");
const cfgOpenaiKey = document.getElementById("cfg-openai-key");
const cfgGeminiKey = document.getElementById("cfg-gemini-key");
const cfgTavilyKey = document.getElementById("cfg-tavily-key");

const archiveDrawer = document.getElementById("archive-drawer");
const btnCloseArchive = document.getElementById("btn-close-archive");
const btnClearArchiveAll = document.getElementById("btn-clear-archive-all");
const archiveCardsList = document.getElementById("archive-cards-list");
const toastContainer = document.getElementById("toast-container");

// ──────────────────────────────────────────────
//  Initialization
// ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    lucide.createIcons();
    loadSettingsFromStorage();
    setupCoreListeners();
    updateArchiveCounter();
});

function loadSettingsFromStorage() {
    if (localStorage.getItem("INVESTIGATOR_LLM_PROVIDER")) {
        cfgLlmProvider.value = localStorage.getItem("INVESTIGATOR_LLM_PROVIDER");
    }
    if (localStorage.getItem("INVESTIGATOR_SEARCH_PROVIDER")) {
        cfgSearchProvider.value = localStorage.getItem("INVESTIGATOR_SEARCH_PROVIDER");
    }
    if (localStorage.getItem("INVESTIGATOR_SENSENOVA_KEY")) {
        cfgSensenovaKey.value = localStorage.getItem("INVESTIGATOR_SENSENOVA_KEY");
    }
    if (localStorage.getItem("INVESTIGATOR_OPENAI_KEY")) {
        cfgOpenaiKey.value = localStorage.getItem("INVESTIGATOR_OPENAI_KEY");
    }
    if (localStorage.getItem("INVESTIGATOR_GEMINI_KEY")) {
        cfgGeminiKey.value = localStorage.getItem("INVESTIGATOR_GEMINI_KEY");
    }
    if (localStorage.getItem("INVESTIGATOR_TAVILY_KEY")) {
        cfgTavilyKey.value = localStorage.getItem("INVESTIGATOR_TAVILY_KEY");
    }
    updateEngineIndicator();
}

function updateEngineIndicator() {
    const llm = cfgLlmProvider.value;
    const search = cfgSearchProvider.value;
    if (llm === "sensenova" && search === "duckduckgo") {
        headerEngineLabel.textContent = "Engine: SenseNova (GLM-5.2) + DuckDuckGo";
    } else if (llm === "mock" && search === "mock") {
        headerEngineLabel.textContent = "Engine: 离线拟真 (Mock)";
    } else {
        headerEngineLabel.textContent = `Engine: ${llm.toUpperCase()} + ${search.toUpperCase()}`;
    }
}

function getActiveApiKeys() {
    return {
        sensenova_api_key: localStorage.getItem("INVESTIGATOR_SENSENOVA_KEY") || "",
        openai_api_key: localStorage.getItem("INVESTIGATOR_OPENAI_KEY") || "",
        gemini_api_key: localStorage.getItem("INVESTIGATOR_GEMINI_KEY") || "",
        tavily_api_key: localStorage.getItem("INVESTIGATOR_TAVILY_KEY") || ""
    };
}

// ──────────────────────────────────────────────
//  Event Listeners
// ──────────────────────────────────────────────
function setupCoreListeners() {
    // Brand title click returns home
    btnBrandHome.addEventListener("click", () => {
        if (currentCoverage) {
            handleNewInvestigation();
        }
    });

    // Engine chip opens settings
    btnEngineStatus.addEventListener("click", () => openSettingsModal());
    btnOpenSettings.addEventListener("click", () => openSettingsModal());

    // Settings Modal
    btnCloseSettingsX.addEventListener("click", () => closeSettingsModal());
    btnCancelSettings.addEventListener("click", () => closeSettingsModal());
    btnSaveSettings.addEventListener("click", handleSaveSettings);

    // Archive Drawer
    btnOpenArchive.addEventListener("click", () => openArchiveDrawer());
    btnCloseArchive.addEventListener("click", () => closeArchiveDrawer());
    btnClearArchiveAll.addEventListener("click", handleClearArchive);

    // Escape closes modals & drawers
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeSettingsModal();
            closeArchiveDrawer();
        }
    });

    // Input Mode Tabs
    document.querySelectorAll(".input-mode-tabs .mode-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".input-mode-tabs .mode-tab").forEach(t => {
                t.classList.remove("active");
                t.setAttribute("aria-selected", "false");
            });
            tab.classList.add("active");
            tab.setAttribute("aria-selected", "true");
            currentInputMode = tab.dataset.mode;
            handleInputModeChange(currentInputMode);
        });
    });

    // Image Input
    imageFileInput.addEventListener("change", handleImageSelected);
    btnRemoveImage.addEventListener("click", handleRemoveImage);

    // Sample Chips (Only fill input, do NOT auto-submit)
    document.querySelectorAll(".sample-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            claimInput.value = chip.dataset.sample;
            claimInput.focus();
            showToast("已填入示例说法，点击“开始核验”展开调查", "info");
        });
    });

    // Form Submit
    verifyForm.addEventListener("submit", handleStartInvestigation);

    // Header & Summary Action Buttons
    btnHeaderNewVerify.addEventListener("click", handleNewInvestigation);
    btnWsNewInvestigation.addEventListener("click", handleNewInvestigation);
    btnWsCopyReport.addEventListener("click", handleCopyReport);
    btnWsExportMd.addEventListener("click", handleExportMarkdown);

    // Inspector Tabs
    document.querySelectorAll(".inspector-tabs .insp-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".inspector-tabs .insp-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            activeInspectorTab = tab.dataset.tab;
            switchInspectorTab(activeInspectorTab);
        });
    });
}

function handleInputModeChange(mode) {
    if (mode === "IMAGE") {
        imageFileInput.click();
    } else if (mode === "URL") {
        imagePreviewContainer.style.display = "none";
        claimInput.style.display = "block";
        claimInput.placeholder = "粘贴待调查的新闻、公告或网页链接 (https://...)\n系统将自主抓取全文、解析核心主张并执行全网独立求证。";
    } else {
        imagePreviewContainer.style.display = "none";
        claimInput.style.display = "block";
        claimInput.placeholder = "输入一个具体的现实世界说法……\n例如：宇树科技于2024年完成近10亿元人民币B2轮融资，美团领投。";
    }
}

function handleImageSelected(e) {
    const file = e.target.files[0];
    if (!file) return;
    previewFilenameLabel.textContent = file.name;
    const reader = new FileReader();
    reader.onload = (evt) => {
        currentUploadedImageBase64 = evt.target.result;
        imagePreviewEl.src = evt.target.result;
        imagePreviewContainer.style.display = "flex";
        claimInput.style.display = "none";
    };
    reader.readAsDataURL(file);
}

function handleRemoveImage() {
    currentUploadedImageBase64 = null;
    imageFileInput.value = "";
    imagePreviewContainer.style.display = "none";
    claimInput.style.display = "block";
}

function openSettingsModal() {
    settingsModal.style.display = "flex";
}

function closeSettingsModal() {
    settingsModal.style.display = "none";
}

function handleSaveSettings() {
    localStorage.setItem("INVESTIGATOR_LLM_PROVIDER", cfgLlmProvider.value);
    localStorage.setItem("INVESTIGATOR_SEARCH_PROVIDER", cfgSearchProvider.value);
    localStorage.setItem("INVESTIGATOR_SENSENOVA_KEY", cfgSensenovaKey.value.trim());
    localStorage.setItem("INVESTIGATOR_OPENAI_KEY", cfgOpenaiKey.value.trim());
    localStorage.setItem("INVESTIGATOR_GEMINI_KEY", cfgGeminiKey.value.trim());
    localStorage.setItem("INVESTIGATOR_TAVILY_KEY", cfgTavilyKey.value.trim());
    closeSettingsModal();
    updateEngineIndicator();
    showToast("引擎与 API 配置已成功保存", "success");
}

function openArchiveDrawer() {
    renderArchiveList();
    archiveDrawer.style.display = "flex";
}

function closeArchiveDrawer() {
    archiveDrawer.style.display = "none";
}

// ──────────────────────────────────────────────
//  Investigation Request Lifecycle
// ──────────────────────────────────────────────
async function handleStartInvestigation(e) {
    e.preventDefault();
    let text = claimInput.value.trim();

    if (currentInputMode === "IMAGE") {
        if (!currentUploadedImageBase64) {
            showToast("请先选择待核验的截图证据文件", "error");
            return;
        }
        text = `[截图证据调查 - ${previewFilenameLabel.textContent}] (自动解析)`;
    }

    if (!text) {
        showToast("请输入待核验的陈述或事实说法", "error");
        return;
    }

    // Switch View to Loading Pipeline
    showView("loading");
    loadingClaimText.textContent = `“${text}”`;
    loadingStageTitle.textContent = "正在调查公开证据……";
    loadingSubstatusText.textContent = "已启动自主调查循环，正在解析调查目标并执行全网定向证据搜集...";
    animateInvestigationPipeline();

    try {
        const payload = {
            claim: text,
            input_type: currentInputMode,
            llm_provider: cfgLlmProvider.value || "sensenova",
            search_provider: cfgSearchProvider.value || "duckduckgo",
            api_keys: getActiveApiKeys()
        };

        const response = await fetch(`${API_BASE}/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`服务请求失败 (HTTP ${response.status}): ${errText}`);
        }

        const data = await response.json();
        currentCoverage = data;

        // Automatically persist to LocalStorage archive
        saveInvestigationToArchive({
            id: `INV-${Date.now().toString().slice(-6)}`,
            timestamp: new Date().toISOString(),
            original_input: text,
            coverage: data
        });

        // Render Comprehensive 3-Column Workspace
        renderInvestigationWorkspace(data);
        showView("workspace");
        showToast("调查完成，证据链已锁定", "success");

    } catch (err) {
        console.error("Investigation error:", err);
        showToast(`核验失败: ${err.message}`, "error");
        showView("home");
    }
}

function animateInvestigationPipeline() {
    const steps = [
        { id: "pipe-claim", text: "正在拆解声明事实点与约束槽位..." },
        { id: "pipe-source", text: "正在生成高信噪比定向搜索 Query 并执行检索..." },
        { id: "pipe-extract", text: "正在安全抓取网页全文并过滤无关噪音 (Relevance Gating)..." },
        { id: "pipe-quote", text: "正在执行物理字符级逐字引文锚定 (Raw-Text Locator)..." },
        { id: "pipe-provenance", text: "正在构建信源出处图谱，追溯同源转载与独立根节点..." },
        { id: "pipe-verdict", text: "确定性规则引擎正在裁决最终证据状态..." }
    ];

    let index = 0;
    const interval = setInterval(() => {
        if (index >= steps.length) {
            clearInterval(interval);
            return;
        }
        steps.forEach((s, idx) => {
            const el = document.getElementById(s.id);
            if (!el) return;
            if (idx < index) {
                el.className = "pipeline-step-node done";
            } else if (idx === index) {
                el.className = "pipeline-step-node active";
            } else {
                el.className = "pipeline-step-node";
            }
        });
        loadingSubstatusText.textContent = steps[index].text;
        index++;
    }, 1100);
}

function showView(viewName) {
    viewHome.style.display = (viewName === "home") ? "flex" : "none";
    viewLoading.style.display = (viewName === "loading") ? "flex" : "none";
    viewWorkspace.style.display = (viewName === "workspace") ? "flex" : "none";
    btnHeaderNewVerify.style.display = (viewName === "workspace") ? "inline-flex" : "none";
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function handleNewInvestigation() {
    currentCoverage = null;
    selectedClaimId = null;
    selectedEvidenceId = null;
    selectedSourceId = null;
    claimInput.value = "";
    currentUploadedImageBase64 = null;
    handleRemoveImage();
    showView("home");
    claimInput.focus();
}

// ──────────────────────────────────────────────
//  Render Investigation Workspace (3-Column)
// ──────────────────────────────────────────────
function renderInvestigationWorkspace(coverage) {
    if (!coverage) return;

    // 1. Top Summary Strip
    renderSummaryStrip(coverage);

    // 2. Column 1: Claims Explorer
    renderClaimsExplorer(coverage);

    // 3. Select first claim by default
    const claims = coverage.claims || [];
    if (claims.length > 0) {
        selectedClaimId = claims[0].id;
        selectClaim(selectedClaimId);
    }

    lucide.createIcons();
}

function renderSummaryStrip(coverage) {
    wsOriginalClaimText.textContent = `“${coverage.original_input}”`;

    // Overall State Badge
    const state = coverage.overall_state || "NOT_ASSESSABLE";
    wsOverallVerdictBadge.className = `overall-verdict-badge state-${state}`;
    wsOverallVerdictText.textContent = getOverallStateLabel(state);

    // Calculate Real Aggregated Metrics strictly from backend response
    const claims = coverage.claims || [];
    const verdicts = coverage.verdicts || [];

    let totalEvidences = 0;
    let totalContradictions = 0;
    const originSourcesSet = new Set();

    verdicts.forEach(v => {
        const evs = v.evidences || [];
        totalEvidences += evs.length;
        totalContradictions += evs.filter(e => e.contradicts_claim === true).length;
        
        // Count truly independent origin sources from assessment or provenance
        if (v.assessment && v.assessment.independent_source_count !== undefined) {
            originSourcesSet.add(v.assessment.independent_source_count);
        } else if (v.sources) {
            v.sources.forEach(s => originSourcesSet.add(s.domain || s.id));
        }
    });

    // Independent origins count
    let totalIndependentOrigins = 0;
    if (verdicts.length > 0 && verdicts[0].assessment && verdicts[0].assessment.independent_source_count !== undefined) {
        totalIndependentOrigins = verdicts[0].assessment.independent_source_count;
    } else {
        totalIndependentOrigins = originSourcesSet.size || 0;
    }

    metricClaimsCount.textContent = claims.length;
    metricEvidenceCount.textContent = totalEvidences;
    metricOriginsCount.textContent = totalIndependentOrigins;
    metricContradictionsCount.textContent = totalContradictions;
}

function renderClaimsExplorer(coverage) {
    claimsNavList.innerHTML = "";
    const claims = coverage.claims || [];
    claimsExplorerCount.textContent = claims.length;

    const verdictMap = new Map();
    (coverage.verdicts || []).forEach(v => verdictMap.set(v.claim_id, v));

    claims.forEach((claim, idx) => {
        const verdict = verdictMap.get(claim.id);
        const evidenceState = verdict ? verdict.evidence_state : "INSUFFICIENT";
        const evidenceCount = verdict && verdict.evidences ? verdict.evidences.length : 0;

        const navBtn = document.createElement("button");
        navBtn.type = "button";
        navBtn.className = `claim-nav-item ${claim.id === selectedClaimId ? 'active' : ''}`;
        navBtn.dataset.claimId = claim.id;

        navBtn.innerHTML = `
            <div class="nav-item-top">
                <span class="claim-order-tag">CLAIM ${String(idx + 1).padStart(2, '0')}</span>
                <span class="claim-state-pill-sm state-${evidenceState}">${getEvidenceStateShortLabel(evidenceState)}</span>
            </div>
            <p class="nav-item-statement">${escapeHtml(claim.statement)}</p>
            <div class="nav-item-footer">
                <span>${evidenceCount} 条证据</span>
                <span>${verdict && verdict.assessment ? `${verdict.assessment.independent_source_count || 0} 独立源` : ''}</span>
            </div>
        `;

        navBtn.addEventListener("click", () => {
            selectedClaimId = claim.id;
            selectClaim(selectedClaimId);
        });

        claimsNavList.appendChild(navBtn);
    });
}

function selectClaim(claimId) {
    if (!currentCoverage) return;

    // Update active class in Left Claims Explorer
    document.querySelectorAll(".claim-nav-item").forEach(item => {
        if (item.dataset.claimId === claimId) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    const claims = currentCoverage.claims || [];
    const claimIndex = claims.findIndex(c => c.id === claimId);
    const claim = claims[claimIndex] || null;
    const verdict = (currentCoverage.verdicts || []).find(v => v.claim_id === claimId) || null;

    if (!claim) return;

    // Render Column 2 (Evidence Workspace)
    renderClaimWorkspace(claim, verdict, claimIndex);

    // Render Column 3 (Inspector)
    renderInspector(verdict);

    lucide.createIcons();
}

function renderClaimWorkspace(claim, verdict, claimIndex) {
    wsClaimIndexTag.textContent = `CLAIM ${String(claimIndex + 1).padStart(2, '0')}`;
    wsSelectedClaimStatement.textContent = claim.statement;

    const evidenceState = verdict ? verdict.evidence_state : "INSUFFICIENT";
    wsVerdictStateChip.className = `verdict-state-chip state-${evidenceState}`;
    wsVerdictStateChip.textContent = getEvidenceStateLabel(evidenceState);

    // Human Explanation
    const reasons = verdict ? verdict.why_reasons : [];
    const humanSummary = reasons.length > 0 ? reasons[0].replace(/^[✓!ℹ️•]\s*/, '') : "完成公开资料核验。";
    wsVerdictSummaryHuman.textContent = humanSummary;

    // Why Reasons List
    wsWhyReasonsList.innerHTML = "";
    if (reasons.length === 0) {
        wsWhyReasonsList.innerHTML = `<li>检索范围内未发现直接支持或反驳该说法的公开证据。</li>`;
    } else {
        reasons.forEach(r => {
            const li = document.createElement("li");
            li.textContent = r;
            wsWhyReasonsList.appendChild(li);
        });
    }

    // Evidence Gaps List
    const gaps = verdict ? verdict.evidence_gaps : [];
    wsGapsList.innerHTML = "";
    if (!gaps || gaps.length === 0) {
        wsGapsContainer.style.display = "none";
    } else {
        wsGapsContainer.style.display = "flex";
        gaps.forEach(g => {
            const li = document.createElement("li");
            li.textContent = g;
            wsGapsList.appendChild(li);
        });
    }

    // Next Step Advice
    const advice = verdict ? verdict.next_step_advice : "";
    if (!advice) {
        wsAdviceContainer.style.display = "none";
    } else {
        wsAdviceContainer.style.display = "flex";
        wsAdviceText.textContent = advice;
    }

    // Categorize Evidences into Supporting, Contradictory, and Context
    const evidences = verdict ? verdict.evidences || [] : [];
    const sourceMap = new Map();
    (verdict && verdict.sources ? verdict.sources : []).forEach(s => sourceMap.set(s.id, s));

    const supporting = evidences.filter(e => e.supports_claim === true);
    const contradicting = evidences.filter(e => e.contradicts_claim === true);
    const context = evidences.filter(e => !e.supports_claim && !e.contradicts_claim);

    // Render Supporting Evidences
    wsSupportingCount.textContent = `${supporting.length} 条`;
    renderEvidenceCardList(supporting, sourceMap, wsSupportingEvidenceList, "supporting");

    // Render Contradicting Evidences (Strict Requirement: "未发现当前结果中记录的直接反驳证据。")
    wsContradictingCount.textContent = `${contradicting.length} 条`;
    if (contradicting.length === 0) {
        wsContradictingEvidenceList.innerHTML = `
            <div class="safe-empty-notice">
                未发现当前结果中记录的直接反驳证据。
            </div>
        `;
    } else {
        renderEvidenceCardList(contradicting, sourceMap, wsContradictingEvidenceList, "contradicting");
    }

    // Render Context Evidences
    wsContextCount.textContent = `${context.length} 条`;
    if (context.length === 0) {
        wsContextSection.style.display = "none";
    } else {
        wsContextSection.style.display = "flex";
        renderEvidenceCardList(context, sourceMap, wsContextEvidenceList, "context");
    }
}

function renderEvidenceCardList(evList, sourceMap, container, type) {
    container.innerHTML = "";
    if (evList.length === 0 && type !== "contradicting") {
        container.innerHTML = `<div class="safe-empty-notice">当前类别暂无关联证据。</div>`;
        return;
    }

    evList.forEach(ev => {
        const src = sourceMap.get(ev.source_id) || {
            title: "公开网络来源",
            domain: "web",
            url: "#",
            source_tier: "UNKNOWN"
        };

        const card = document.createElement("div");
        card.className = `evidence-card type-${type}`;

        const matchTier = ev.match_tier || "EXACT";
        const charCoords = (ev.char_start !== null && ev.char_end !== null)
            ? `[${ev.char_start} : ${ev.char_end}]`
            : "";

        // Warning banner for unverified / fuzzy per spec
        let warningBannerHtml = "";
        if (matchTier === "UNVERIFIED") {
            warningBannerHtml = `
                <div class="quote-warning-banner unverified">
                    <i data-lucide="alert-triangle"></i>
                    <span>⚠ 引文未能在原文中验证 · Not accepted as direct evidence</span>
                </div>
            `;
        } else if (matchTier === "FUZZY") {
            warningBannerHtml = `
                <div class="quote-warning-banner fuzzy">
                    <i data-lucide="alert-circle"></i>
                    <span>⚠ 模糊匹配 · Not an exact quote</span>
                </div>
            `;
        }

        card.innerHTML = `
            <div class="evidence-card-header">
                <div class="evidence-source-meta">
                    <div class="source-title-row">
                        <span class="source-title-text">${escapeHtml(src.title || "网页来源")}</span>
                        <span class="source-domain-tag">(${escapeHtml(src.domain)})</span>
                    </div>
                </div>
                <div class="source-badges-row">
                    <span class="tier-pill">${escapeHtml(src.source_tier || 'UNKNOWN')}</span>
                    <span class="directness-pill ${ev.directness || 'CONTEXTUAL'}">${ev.directness || 'CONTEXTUAL'}</span>
                </div>
            </div>

            <!-- Exact Quote Box -->
            <div class="quote-box">
                <div class="quote-box-header">
                    <span class="quote-label">EXACT QUOTE ${charCoords}</span>
                    <span class="quote-match-badge ${matchTier}">${matchTier}</span>
                </div>
                ${warningBannerHtml}
                <div class="quote-verbatim-content">
                    “${escapeHtml(ev.exact_quote || ev.context || '未提供逐字引用')}”
                </div>
            </div>

            <div class="evidence-card-footer">
                <div class="footer-actions-left">
                    <button type="button" class="btn-card-action" data-action="inspect-quote" data-evidence-id="${ev.id}">
                        <i data-lucide="crosshair"></i> <span>透视引文坐标</span>
                    </button>
                    <button type="button" class="btn-card-action" data-action="inspect-prov" data-source-id="${src.id}">
                        <i data-lucide="git-merge"></i> <span>查看来源链</span>
                    </button>
                </div>
                ${src.url && src.url !== '#' ? `
                    <a href="${src.url}" target="_blank" rel="noopener noreferrer" class="btn-open-source">
                        <span>打开原始网页</span> <i data-lucide="external-link"></i>
                    </a>
                ` : ''}
            </div>
        `;

        // Card action events
        card.querySelector('[data-action="inspect-quote"]').addEventListener("click", () => {
            selectedEvidenceId = ev.id;
            selectedSourceId = src.id;
            switchInspectorTab("quote");
            renderQuoteInspectorTab(ev, src);
        });

        card.querySelector('[data-action="inspect-prov"]').addEventListener("click", () => {
            selectedSourceId = src.id;
            switchInspectorTab("provenance");
        });

        container.appendChild(card);
    });
}

// ──────────────────────────────────────────────
//  Render Column 3: Inspector Panel
// ──────────────────────────────────────────────
function renderInspector(verdict) {
    if (!verdict) return;
    renderAuditTab(verdict);
    renderProvenanceTab(verdict.sources || [], verdict.provenances || []);
    switchInspectorTab(activeInspectorTab);
}

function switchInspectorTab(tabName) {
    activeInspectorTab = tabName;
    document.querySelectorAll(".inspector-tabs .insp-tab").forEach(t => {
        if (t.dataset.tab === tabName) {
            t.classList.add("active");
        } else {
            t.classList.remove("active");
        }
    });

    document.getElementById("pane-audit").style.display = (tabName === "audit") ? "block" : "none";
    document.getElementById("pane-provenance").style.display = (tabName === "provenance") ? "block" : "none";
    document.getElementById("pane-quote").style.display = (tabName === "quote") ? "block" : "none";
}

function renderAuditTab(verdict) {
    auditMetricsGrid.innerHTML = "";
    const ass = verdict ? verdict.assessment : null;

    if (!ass) {
        auditMetricsGrid.innerHTML = `<div style="grid-column:1/-1;color:var(--text-muted);font-size:12px;">暂无该主张的规则审计数据。</div>`;
        return;
    }

    const metrics = [
        { label: "检索候选信源", val: ass.total_sources_found, class: "" },
        { label: "独立原始信源", val: ass.independent_source_count, class: "highlight" },
        { label: "直接支持信源数", val: ass.direct_supporting_origin_count !== undefined ? ass.direct_supporting_origin_count : (ass.has_direct_support ? 1 : 0), class: "highlight" },
        { label: "官方/第一手直接支持", val: ass.has_supporting_official_source ? "是 (DIRECT)" : "否", class: ass.has_supporting_official_source ? "highlight" : "" },
        { label: "反驳与实质冲突", val: ass.has_credible_contradicting_evidence ? "检出明确反驳" : "未发现直接反驳", class: ass.has_credible_contradicting_evidence ? "warning" : "" },
        { label: "数值与口径一致性", val: ass.value_consistent === false ? "口径存在冲突" : "一致/未检出冲突", class: ass.value_consistent === false ? "warning" : "" },
        { label: "时序有效性", val: ass.time_consistent === false ? "已被后续信息覆盖" : "有效 / 当前", class: "" },
        { label: "核验时间戳", val: verdict.verified_as_of || new Date().toISOString().slice(0, 10), class: "" }
    ];

    metrics.forEach(m => {
        const cell = document.createElement("div");
        cell.className = "audit-metric-cell";
        cell.innerHTML = `
            <span class="cell-lbl">${m.label}</span>
            <span class="cell-val ${m.class}">${m.val}</span>
        `;
        auditMetricsGrid.appendChild(cell);
    });

    // FactSlots Table (if available from backend)
    if (verdict.fact_slots && verdict.fact_slots.compound_slots && verdict.fact_slots.compound_slots.length > 0) {
        auditFactslotsCard.style.display = "block";
        const slots = verdict.fact_slots.compound_slots;
        auditFactslotsContent.innerHTML = `
            <div style="font-size:12px;display:flex;flex-direction:column;gap:6px;">
                <div style="color:var(--accent-cyan);font-family:var(--font-mono);">主体实体: ${escapeHtml(verdict.fact_slots.entity || 'N/A')}</div>
                ${slots.map(s => `
                    <div style="display:flex;justify-content:space-between;color:var(--text-secondary);background:rgba(0,0,0,0.2);padding:4px 8px;border-radius:4px;">
                        <span>${escapeHtml(s.slot_name)}:</span>
                        <code style="color:var(--text-primary);">${escapeHtml(String(s.value))}${escapeHtml(s.unit || '')}</code>
                    </div>
                `).join('')}
            </div>
        `;
    } else {
        auditFactslotsCard.style.display = "none";
    }

    // Multi-round audit info
    if (verdict.multi_round_audit && verdict.multi_round_audit.round_count > 1) {
        auditMultiroundCard.style.display = "block";
        const mr = verdict.multi_round_audit;
        auditMultiroundContent.innerHTML = `
            <div style="font-size:12px;color:var(--text-secondary);display:flex;flex-direction:column;gap:4px;">
                <div>执行轮次: <strong>第 2 轮自主缺口检索</strong></div>
                <div>初始状态: <code>${mr.initial_state}</code> → 最终状态: <code>${mr.final_state}</code></div>
                <div>补充信源数: +${mr.new_sources_added || 0} 个</div>
            </div>
        `;
    } else {
        auditMultiroundCard.style.display = "none";
    }
}

function renderProvenanceTab(sources, provenances) {
    provenanceLineageContainer.innerHTML = "";
    if (!sources || sources.length === 0) {
        provenanceLineageContainer.innerHTML = `<div style="font-size:12px;color:var(--text-muted);padding:10px;">本次调查未收录外部来源节点。</div>`;
        return;
    }

    // Map origin clusters
    const provMap = new Map();
    (provenances || []).forEach(p => provMap.set(p.source_id, p));

    sources.forEach(src => {
        const prov = provMap.get(src.id);
        const card = document.createElement("div");
        card.className = "prov-cluster-card";

        const isOriginal = !prov || !prov.origin_source_id;
        const originLabel = isOriginal ? "ORIGINAL REPORTING (原创披露/一手信源)" : `REPUBLISHES / CITES (追溯至原始来源: ${prov.origin_source_id})`;

        card.innerHTML = `
            <div class="prov-origin-header">
                <span>[${src.source_tier}] ${escapeHtml(src.domain)}</span>
                <span>${isOriginal ? '● 独立根节点' : '○ 引用节点'}</span>
            </div>
            <div class="prov-source-item">
                <i data-lucide="${isOriginal ? 'shield-check' : 'corner-down-right'}" style="width:14px;height:14px;color:${isOriginal ? 'var(--state-sufficient-solid)' : 'var(--text-muted)'};"></i>
                <span style="font-weight:600;color:var(--text-primary);">${escapeHtml(src.title)}</span>
            </div>
            <div class="prov-arrow-cites">${originLabel}</div>
            ${prov && prov.explanation ? `<div style="font-size:11px;color:var(--text-muted);font-style:italic;padding-left:14px;">"${escapeHtml(prov.explanation)}"</div>` : ''}
        `;
        provenanceLineageContainer.appendChild(card);
    });
}

function renderQuoteInspectorTab(evidence, source) {
    if (!evidence) {
        quoteInspectorContainer.innerHTML = `
            <div class="empty-inspector-hint">
                <i data-lucide="mouse-pointer-click"></i>
                <p>在左侧证据卡片中点击“透视坐标”以检查该条证据的物理字符级定位坐标与 DOM 属性。</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    const matchTier = evidence.match_tier || "EXACT";
    quoteInspectorContainer.innerHTML = `
        <div class="quote-detailed-card">
            <div class="detail-row">
                <span class="detail-lbl">匹配层级 (Match Tier)</span>
                <span class="quote-match-badge ${matchTier}">${matchTier}</span>
            </div>
            <div class="detail-row">
                <span class="detail-lbl">物理字符坐标 [Start : End]</span>
                <span class="detail-val">[${evidence.char_start !== null ? evidence.char_start : 'N/A'} : ${evidence.char_end !== null ? evidence.char_end : 'N/A'}]</span>
            </div>
            <div class="detail-row">
                <span class="detail-lbl">DOM 元素语义角色</span>
                <span class="detail-val">${escapeHtml(evidence.element_role || 'MAIN')}</span>
            </div>
            <div class="detail-row">
                <span class="detail-lbl">证据直接性 (Directness)</span>
                <span class="detail-val">${escapeHtml(evidence.directness || 'CONTEXTUAL')}</span>
            </div>

            <div style="font-size:11px;font-weight:700;color:var(--text-muted);margin-top:4px;">逐字引文 (Verbatim Quote):</div>
            <div class="detail-text-block">“${escapeHtml(evidence.exact_quote || '')}”</div>

            ${evidence.context ? `
                <div style="font-size:11px;font-weight:700;color:var(--text-muted);">上下文语境 (Context):</div>
                <div class="detail-text-block" style="color:var(--text-secondary);font-size:11px;">${escapeHtml(evidence.context)}</div>
            ` : ''}

            <div style="font-size:11px;font-weight:700;color:var(--text-muted);margin-top:4px;">信源链接:</div>
            <a href="${source ? source.url : '#'}" target="_blank" rel="noopener noreferrer" class="btn-open-source" style="word-break:break-all;">
                <span>${escapeHtml(source ? source.url : '无链接')}</span>
                <i data-lucide="external-link"></i>
            </a>
        </div>
    `;
    lucide.createIcons();
}

// ──────────────────────────────────────────────
//  Export & Copy Handlers
// ──────────────────────────────────────────────
function handleCopyReport() {
    if (!currentCoverage) return;
    const md = buildMarkdownReport(currentCoverage);
    navigator.clipboard.writeText(md).then(() => {
        showToast("完整事实核验报告已复制到剪贴板", "success");
    }).catch(err => {
        console.error("Copy failed:", err);
        showToast("复制失败，请手动导出", "error");
    });
}

function handleExportMarkdown() {
    if (!currentCoverage) return;
    const md = buildMarkdownReport(currentCoverage);
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Investigation_Report_${Date.now().toString().slice(-6)}.md`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Markdown 调查报告已开始下载", "info");
}

function buildMarkdownReport(coverage) {
    const claims = coverage.claims || [];
    const verdicts = coverage.verdicts || [];
    const verdictMap = new Map();
    verdicts.forEach(v => verdictMap.set(v.claim_id, v));

    let report = `# 事实调查与核验报告 (AI Real-World Investigator)
- **调查目标**：${coverage.original_input}
- **整体裁决**：${getOverallStateLabel(coverage.overall_state)}
- **执行摘要**：${coverage.coverage_summary || "调查完成。"}
- **核验时间**：${new Date().toLocaleString("zh-CN")}

---

## 逐项事实裁决与证据链分析
`;

    claims.forEach((c, idx) => {
        const v = verdictMap.get(c.id);
        const state = v ? v.evidence_state : "INSUFFICIENT";
        report += `\n### 主张 ${idx + 1}: ${c.statement}\n`;
        report += `- **证据状态**：${getEvidenceStateLabel(state)}\n`;
        
        if (v && v.why_reasons && v.why_reasons.length > 0) {
            report += `- **判断依据**：\n`;
            v.why_reasons.forEach(r => report += `  - ${r}\n`);
        }
        if (v && v.evidence_gaps && v.evidence_gaps.length > 0) {
            report += `- **证据缺口**：\n`;
            v.evidence_gaps.forEach(g => report += `  - ⚠ ${g}\n`);
        }
        if (v && v.evidences && v.evidences.length > 0) {
            report += `- **核心逐字引文 (Exact Quotes)**：\n`;
            v.evidences.forEach(e => {
                const quoteStr = e.exact_quote || e.context;
                report += `  - [${e.match_tier || 'EXACT'}] [${e.directness || 'CONTEXTUAL'}] “${quoteStr}”\n`;
            });
        }
    });

    report += `\n---\n*由 AI Real-World Investigator 自动化系统生成 · Evidence before conclusions.*`;
    return report;
}

// ──────────────────────────────────────────────
//  Archive Storage & Rendering
// ──────────────────────────────────────────────
function saveInvestigationToArchive(item) {
    try {
        const raw = localStorage.getItem("INVESTIGATION_ARCHIVE") || "[]";
        let list = JSON.parse(raw);
        list.unshift(item);
        if (list.length > 20) list = list.slice(0, 20);
        localStorage.setItem("INVESTIGATION_ARCHIVE", JSON.stringify(list));
        updateArchiveCounter();
    } catch (e) {
        console.warn("Archive save failed:", e);
    }
}

function updateArchiveCounter() {
    try {
        const raw = localStorage.getItem("INVESTIGATION_ARCHIVE") || "[]";
        const list = JSON.parse(raw);
        archiveCountBadge.textContent = list.length;
    } catch (e) {
        archiveCountBadge.textContent = "0";
    }
}

function renderArchiveList() {
    archiveCardsList.innerHTML = "";
    let list = [];
    try {
        list = JSON.parse(localStorage.getItem("INVESTIGATION_ARCHIVE") || "[]");
    } catch (e) { list = []; }

    if (list.length === 0) {
        archiveCardsList.innerHTML = `<div style="text-align:center;padding:40px 10px;color:var(--text-muted);font-size:13px;">暂无已保存的调查档案。</div>`;
        return;
    }

    list.forEach(item => {
        const card = document.createElement("div");
        card.className = "archive-card";
        const cov = item.coverage || {};
        const state = cov.overall_state || "INSUFFICIENT";

        card.innerHTML = `
            <div class="archive-card-header">
                <span class="claim-state-pill-sm state-${state}">${getOverallStateLabel(state)}</span>
                <span style="font-size:11px;font-family:var(--font-mono);color:var(--text-muted);">${item.id}</span>
            </div>
            <p class="archive-claim-snippet">${escapeHtml(item.original_input || "")}</p>
            <div class="archive-meta-row">
                <span>${new Date(item.timestamp).toLocaleDateString("zh-CN")}</span>
                <span style="color:var(--accent-cyan);">打开核验工作台 →</span>
            </div>
        `;

        card.addEventListener("click", () => {
            currentCoverage = cov;
            closeArchiveDrawer();
            renderInvestigationWorkspace(cov);
            showView("workspace");
            showToast("已恢复历史调查档案", "info");
        });

        archiveCardsList.appendChild(card);
    });
}

function handleClearArchive() {
    if (confirm("确定要清空所有已保存的历史调查记录吗？此操作无法撤销。")) {
        localStorage.removeItem("INVESTIGATION_ARCHIVE");
        updateArchiveCounter();
        renderArchiveList();
        showToast("历史调查档案已清空", "info");
    }
}

// ──────────────────────────────────────────────
//  Toast Notification Utility
// ──────────────────────────────────────────────
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast-item ${type}`;

    let iconName = "info";
    if (type === "success") iconName = "check-circle";
    if (type === "error") iconName = "alert-octagon";

    toast.innerHTML = `<i data-lucide="${iconName}" style="width:16px;height:16px;flex-shrink:0;"></i> <span>${escapeHtml(message)}</span>`;
    toastContainer.appendChild(toast);
    lucide.createIcons();

    setTimeout(() => {
        toast.style.transition = "opacity 0.25s ease, transform 0.25s ease";
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        setTimeout(() => toast.remove(), 260);
    }, 3200);
}

// ──────────────────────────────────────────────
//  Label & Text Utilities (Strict Domain Mapping)
// ──────────────────────────────────────────────
function getOverallStateLabel(state) {
    const map = {
        "FULLY_SUPPORTED": "🟢 全部证实 (Fully Supported)",
        "PARTIALLY_SUPPORTED": "🟢 部分证实 (Partially Supported)",
        "MIXED": "🟠 存在争议与分歧 (Mixed)",
        "FULLY_UNSUPPORTED": "🔴 有可靠证据反驳 (Fully Unsupported)",
        "NOT_ASSESSABLE": "⚪ 无法有效评估 (Not Assessable)"
    };
    return map[state] || state;
}

function getEvidenceStateLabel(state) {
    const map = {
        "SUFFICIENT": "🟢 证据充分 (Sufficient Evidence)",
        "STRONG": "🟢 证据较强 (Strong Support)",
        "INSUFFICIENT": "🟡 证据不足 (Insufficient Evidence)",
        "CONFLICTING": "🟠 存在直接冲突 (Conflicting)",
        "UNSUPPORTED": "🔴 有可靠证据反驳 (Unsupported)",
        "NOT_ASSESSABLE": "⚪ 公开资料无法核验 (Not Assessable)"
    };
    return map[state] || state;
}

function getEvidenceStateShortLabel(state) {
    const map = {
        "SUFFICIENT": "充分",
        "STRONG": "较强",
        "INSUFFICIENT": "不足",
        "CONFLICTING": "冲突",
        "UNSUPPORTED": "反驳",
        "NOT_ASSESSABLE": "无法评估"
    };
    return map[state] || state;
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
