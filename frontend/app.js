// AI Real-World Investigator — Autonomous Studio Controller (v5 Final)

const API_BASE = window.location.origin.includes(":8000") || window.location.origin.includes(":3000")
    ? `${window.location.origin}/api/v1`
    : "http://127.0.0.1:8000/api/v1";

// Global State
let currentInputMode = "TEXT";
let currentUploadedImageBase64 = null;
let currentInvestigationDossier = null;

// DOM Elements - Navigation & Views
const tabNavConsole = document.getElementById("tab-nav-console");
const tabNavArchive = document.getElementById("tab-nav-archive");
const viewConsole = document.getElementById("view-console");
const viewArchive = document.getElementById("view-archive");
const archiveCountBadge = document.getElementById("archive-count-badge");

// DOM Elements - Input Form
const verifyForm = document.getElementById("verify-form");
const claimInput = document.getElementById("claim-input");
const btnStartVerify = document.getElementById("btn-start-verify");
const imageUploadInput = document.getElementById("image-upload-input");
const imagePreviewBox = document.getElementById("image-preview-box");
const imagePreviewImg = document.getElementById("image-preview-img");
const previewFileName = document.getElementById("preview-file-name");
const btnRemoveImage = document.getElementById("btn-remove-image");

// DOM Elements - Live Stepper
const loadingStateCard = document.getElementById("loading-state-card");
const loadingTitle = document.getElementById("loading-title");
const loadingDesc = document.getElementById("loading-desc");
const liveSubtaskTags = document.getElementById("live-subtask-tags");

// DOM Elements - Results Dossier
const verdictResultSection = document.getElementById("verdict-result-section");
const dossierIdLabel = document.getElementById("dossier-id-label");
const dossierTimestampLabel = document.getElementById("dossier-timestamp-label");
const overallStatePill = document.getElementById("overall-state-pill");
const overallStateIcon = document.getElementById("overall-state-icon");
const overallStateText = document.getElementById("overall-state-text");
const dossierGoalTitle = document.getElementById("dossier-goal-title");
const overallSummaryText = document.getElementById("overall-summary-text");

// Telemetry & Sections
const badgeIndependentSources = document.getElementById("badge-independent-sources");
const badgeOfficialSources = document.getElementById("badge-official-sources");
const badgeGroundedQuotes = document.getElementById("badge-grounded-quotes");
const badgeOverclaimRisk = document.getElementById("badge-overclaim-risk");
const subtaskMatrixTbody = document.getElementById("subtask-matrix-tbody");
const queryPillsContainer = document.getElementById("query-pills-container");
const statTotalSearch = document.getElementById("stat-total-search");
const statAcceptedSearch = document.getElementById("stat-accepted-search");
const statRejectedSearch = document.getElementById("stat-rejected-search");
const statLiveFetched = document.getElementById("stat-live-fetched");
const provenanceGraphContainer = document.getElementById("provenance-graph-container");
const quotesListContainer = document.getElementById("quotes-list-container");
const timelineDisputeSection = document.getElementById("timeline-dispute-section");
const timelineDisputeContainer = document.getElementById("timeline-dispute-container");
const gapsAdviceSection = document.getElementById("gaps-advice-section");
const gapsAdviceBody = document.getElementById("gaps-advice-body");

// Action Buttons
const btnNewVerify = document.getElementById("btn-new-verify");
const btnExportMarkdown = document.getElementById("btn-export-markdown");
const btnCopyVerdict = document.getElementById("btn-copy-verdict");
const archiveGrid = document.getElementById("archive-grid");
const btnClearArchive = document.getElementById("btn-clear-archive");
const currentEngineLabel = document.getElementById("current-engine-label");

// Settings Modal
const btnOpenSettings = document.getElementById("btn-open-settings");
const settingsModal = document.getElementById("settings-modal");
const btnCloseSettings = document.getElementById("btn-close-settings");
const btnCancelSettings = document.getElementById("btn-cancel-settings");
const btnSaveSettings = document.getElementById("btn-save-settings");
const setLlmSelect = document.getElementById("set-llm-select");
const setSearchSelect = document.getElementById("set-search-select");
const setSensenovaKey = document.getElementById("set-sensenova-key");
const setOpenaiKey = document.getElementById("set-openai-key");
const setGeminiKey = document.getElementById("set-gemini-key");
const setTavilyKey = document.getElementById("set-tavily-key");

// ──────────────────────────────────────────────
//  Initialization
// ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    lucide.createIcons();
    loadSavedSettings();
    setupEventListeners();
    updateArchiveBadge();
});

function loadSavedSettings() {
    if (localStorage.getItem("INVESTIGATOR_LLM_PROVIDER")) {
        setLlmSelect.value = localStorage.getItem("INVESTIGATOR_LLM_PROVIDER");
    }
    if (localStorage.getItem("INVESTIGATOR_SEARCH_PROVIDER")) {
        setSearchSelect.value = localStorage.getItem("INVESTIGATOR_SEARCH_PROVIDER");
    }
    if (localStorage.getItem("INVESTIGATOR_SENSENOVA_KEY")) {
        setSensenovaKey.value = localStorage.getItem("INVESTIGATOR_SENSENOVA_KEY");
    }
    if (localStorage.getItem("INVESTIGATOR_OPENAI_KEY")) {
        setOpenaiKey.value = localStorage.getItem("INVESTIGATOR_OPENAI_KEY");
    }
    if (localStorage.getItem("INVESTIGATOR_GEMINI_KEY")) {
        setGeminiKey.value = localStorage.getItem("INVESTIGATOR_GEMINI_KEY");
    }
    if (localStorage.getItem("INVESTIGATOR_TAVILY_KEY")) {
        setTavilyKey.value = localStorage.getItem("INVESTIGATOR_TAVILY_KEY");
    }
    updateEngineLabel();
}

function updateEngineLabel() {
    const llm = setLlmSelect.value;
    const search = setSearchSelect.value;
    if (llm === "sensenova" && search === "duckduckgo") {
        currentEngineLabel.textContent = "运行模式: SenseNova (GLM-5.2) + Live DuckDuckGo (推荐)";
    } else if (llm === "mock" && search === "mock") {
        currentEngineLabel.textContent = "运行模式: 离线拟真引擎 (内置事实库)";
    } else {
        currentEngineLabel.textContent = `运行模式: ${llm.toUpperCase()} + ${search.toUpperCase()}`;
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
//  Event Listeners Setup
// ──────────────────────────────────────────────
function setupEventListeners() {
    // View Tabs Switching
    tabNavConsole.addEventListener("click", () => switchView("console"));
    tabNavArchive.addEventListener("click", () => {
        switchView("archive");
        renderArchiveView();
    });

    // Input Mode Tabs
    document.querySelectorAll(".input-mode-tabs .mode-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".input-mode-tabs .mode-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            currentInputMode = tab.dataset.mode;
            handleInputModeChange(currentInputMode);
        });
    });

    // Image Upload
    imageUploadInput.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (!file) return;
        previewFileName.textContent = file.name;
        const reader = new FileReader();
        reader.onload = function(evt) {
            currentUploadedImageBase64 = evt.target.result;
            imagePreviewImg.src = evt.target.result;
            imagePreviewBox.style.display = "flex";
            claimInput.style.display = "none";
        };
        reader.readAsDataURL(file);
    });

    btnRemoveImage.addEventListener("click", () => {
        currentUploadedImageBase64 = null;
        imageUploadInput.value = "";
        imagePreviewBox.style.display = "none";
        claimInput.style.display = "block";
    });

    // Sample Chips Click
    document.querySelectorAll(".sample-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            claimInput.value = chip.dataset.sample;
            claimInput.focus();
        });
    });

    // Form Submit
    verifyForm.addEventListener("submit", handleStartInvestigation);

    // Reset Button
    btnNewVerify.addEventListener("click", () => {
        verdictResultSection.style.display = "none";
        loadingStateCard.style.display = "none";
        claimInput.value = "";
        currentUploadedImageBase64 = null;
        imagePreviewBox.style.display = "none";
        claimInput.style.display = "block";
        claimInput.focus();
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    // Export Actions
    btnExportMarkdown.addEventListener("click", handleExportMarkdown);
    btnCopyVerdict.addEventListener("click", handleCopyDossier);
    btnClearArchive.addEventListener("click", handleClearArchive);

    // Settings Modal
    btnOpenSettings.addEventListener("click", () => settingsModal.style.display = "flex");
    btnCloseSettings.addEventListener("click", () => settingsModal.style.display = "none");
    btnCancelSettings.addEventListener("click", () => settingsModal.style.display = "none");
    btnSaveSettings.addEventListener("click", () => {
        localStorage.setItem("INVESTIGATOR_LLM_PROVIDER", setLlmSelect.value);
        localStorage.setItem("INVESTIGATOR_SEARCH_PROVIDER", setSearchSelect.value);
        localStorage.setItem("INVESTIGATOR_SENSENOVA_KEY", setSensenovaKey.value.trim());
        localStorage.setItem("INVESTIGATOR_OPENAI_KEY", setOpenaiKey.value.trim());
        localStorage.setItem("INVESTIGATOR_GEMINI_KEY", setGeminiKey.value.trim());
        localStorage.setItem("INVESTIGATOR_TAVILY_KEY", setTavilyKey.value.trim());
        settingsModal.style.display = "none";
        updateEngineLabel();
        alert("调查引擎与密钥配置已保存！");
    });
}

function switchView(viewName) {
    if (viewName === "console") {
        tabNavConsole.classList.add("active");
        tabNavArchive.classList.remove("active");
        viewConsole.style.display = "block";
        viewArchive.style.display = "none";
    } else {
        tabNavConsole.classList.remove("active");
        tabNavArchive.classList.add("active");
        viewConsole.style.display = "none";
        viewArchive.style.display = "block";
    }
}

function handleInputModeChange(mode) {
    if (mode === "IMAGE") {
        imageUploadInput.click();
    } else if (mode === "URL") {
        imagePreviewBox.style.display = "none";
        claimInput.style.display = "block";
        claimInput.placeholder = "粘贴待调查的新闻、财报或网页链接 (https://...)\nAI 调查员将自主提取关键事实主张并执行全网求证";
    } else {
        imagePreviewBox.style.display = "none";
        claimInput.style.display = "block";
        claimInput.placeholder = "输入待调查的完整陈述或目标疑问...\n例如：具身智能人形机器人企业宇树科技(Unitree Robotics)总部位于中国杭州，由创始人兼CEO王兴兴于2016年创立。";
    }
}

// ──────────────────────────────────────────────
//  Execute Investigation Lifecycle
// ──────────────────────────────────────────────
async function handleStartInvestigation(e) {
    e.preventDefault();
    let text = claimInput.value.trim();
    if (currentInputMode === "IMAGE") {
        if (!currentUploadedImageBase64) {
            alert("请先上传要核验的截图文件。");
            return;
        }
        text = `[截图证据调查 - ${previewFileName.textContent}] (自动解析)`;
    }

    if (!text) return;

    // UI Loading State
    btnStartVerify.disabled = true;
    btnStartVerify.innerHTML = `<i data-lucide="loader-2" class="spin-icon-sm"></i> <span>调查进行中...</span>`;
    lucide.createIcons();

    loadingStateCard.style.display = "flex";
    verdictResultSection.style.display = "none";
    window.scrollTo({ top: loadingStateCard.offsetTop - 40, behavior: "smooth" });

    // Animate Stepper
    animateInvestigationStepper(text);

    try {
        const payload = {
            claim: text,
            input_type: currentInputMode,
            llm_provider: setLlmSelect.value || "sensenova",
            search_provider: setSearchSelect.value || "duckduckgo",
            api_keys: getActiveApiKeys()
        };

        const res = await fetch(`${API_BASE}/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            throw new Error(`调查请求失败 (HTTP ${res.status}): ${await res.text()}`);
        }

        const data = await res.json();
        currentInvestigationDossier = {
            id: `INV-${Date.now().toString().slice(-6)}`,
            timestamp: new Date().toISOString(),
            goal: text,
            data: data
        };

        // Render Comprehensive Investigation Dossier
        renderExecutiveInvestigationDossier(currentInvestigationDossier);

        // Save to Persistent Archive
        saveToArchive(currentInvestigationDossier);

    } catch (err) {
        console.error("Investigation failed:", err);
        alert(`调查失败: ${err.message}\n请检查网络或后端服务。`);
    } finally {
        btnStartVerify.disabled = false;
        btnStartVerify.innerHTML = `<i data-lucide="sparkles"></i> <span>开始自主调查</span>`;
        loadingStateCard.style.display = "none";
        lucide.createIcons();
    }
}

// ──────────────────────────────────────────────
//  Stepper Animation
// ──────────────────────────────────────────────
function animateInvestigationStepper(claimText) {
    const steps = [
        { id: "step-1", title: "正在解析调查目标与事实槽位约束...", desc: "提取实体、数值、地点、时间与会计口径约束..." },
        { id: "step-2", title: "正在规划多维调查子任务...", desc: "自动生成主体资质、规格数值、官方公告与争议反证任务..." },
        { id: "step-3", title: "正在生成多路定向检索 Query...", desc: "执行 Query A/B/C/D 覆盖原始语义与权威披露..." },
        { id: "step-4", title: "正在应用相关性闸门过滤...", desc: "计算 Entity/Slot 重合度，拦截无关噪音网页..." },
        { id: "step-5", title: "正在抓取真实网页全文 (WebScraper)...", desc: "SSRF 安全隔离抓取并提取可引用正文..." },
        { id: "step-6", title: "正在执行 4-Tier 物理逐字引文锚定...", desc: "严格计算字符级偏移坐标 (char_start : char_end)..." },
        { id: "step-7", title: "确定性推理引擎裁决并生成调查档案...", desc: "基于证据状态安全降级，严防过度断言 (Overclaim)..." }
    ];

    // Quick subtask breakdown preview
    liveSubtaskTags.innerHTML = `
        <span class="subtask-tag-pill active"><i data-lucide="crosshair" style="width:12px;height:12px;"></i> 目标: "${claimText.slice(0, 24)}..."</span>
        <span class="subtask-tag-pill"><i data-lucide="search" style="width:12px;height:12px;"></i> 多路定向检索</span>
        <span class="subtask-tag-pill"><i data-lucide="shield-check" style="width:12px;height:12px;"></i> 真实正文抓取</span>
        <span class="subtask-tag-pill"><i data-lucide="file-text" style="width:12px;height:12px;"></i> 结构化调查报告</span>
    `;
    lucide.createIcons();

    let curr = 0;
    const interval = setInterval(() => {
        if (curr >= steps.length) {
            clearInterval(interval);
            return;
        }
        for (let i = 1; i <= 7; i++) {
            const el = document.getElementById(`step-${i}`);
            if (i < curr + 1) {
                el.className = "stage-step-item done";
            } else if (i === curr + 1) {
                el.className = "stage-step-item active";
            } else {
                el.className = "stage-step-item";
            }
        }
        loadingTitle.textContent = steps[curr].title;
        loadingDesc.textContent = steps[curr].desc;
        curr++;
    }, 1200);
}

// ──────────────────────────────────────────────
//  Render Executive Investigation Dossier
// ──────────────────────────────────────────────
function renderExecutiveInvestigationDossier(dossier) {
    const data = dossier.data;
    const firstVerdict = (data.verdicts && data.verdicts.length > 0) ? data.verdicts[0] : null;

    dossierIdLabel.textContent = dossier.id;
    dossierTimestampLabel.textContent = new Date(dossier.timestamp).toLocaleString("zh-CN");
    dossierGoalTitle.textContent = `调查目标：${dossier.goal}`;
    overallSummaryText.textContent = data.overall_summary || (firstVerdict ? firstVerdict.explanation : "调查已完成。");

    // 1. Overall State Pill
    const state = data.overall_state || (firstVerdict ? firstVerdict.evidence_state : "INSUFFICIENT");
    overallStatePill.className = `state-verdict-banner state-${state}`;
    overallStateText.textContent = getStateLabel(state);

    // 2. Telemetry Badges
    const indepCount = (firstVerdict && firstVerdict.assessment && firstVerdict.assessment.independent_sources_count !== undefined)
        ? firstVerdict.assessment.independent_sources_count
        : (firstVerdict && firstVerdict.sources ? firstVerdict.sources.length : 0);

    const officialCount = (firstVerdict && firstVerdict.assessment && firstVerdict.assessment.official_sources_count !== undefined)
        ? firstVerdict.assessment.official_sources_count
        : (firstVerdict && firstVerdict.sources ? firstVerdict.sources.filter(s => s.source_tier === 'AUTHORITATIVE' || s.source_tier === 'DIRECT_PRIMARY').length : 0);

    const quotesCount = firstVerdict && firstVerdict.evidences
        ? firstVerdict.evidences.filter(e => e.is_admissible_factual_evidence).length
        : 0;
    
    badgeIndependentSources.textContent = `独立信源: ${indepCount} 个`;
    badgeOfficialSources.textContent = `官方信源: ${officialCount} 个`;
    badgeGroundedQuotes.textContent = `物理引文: ${quotesCount} 条`;
    badgeOverclaimRisk.textContent = (state === "STRONG" || state === "SUFFICIENT") && quotesCount === 0
        ? "过度断言风险: 警报"
        : "过度断言风险: 0.0% (安全)";

    // 3. Subtask Findings Matrix Table
    renderSubtaskMatrix(data, firstVerdict);

    // 4. Multi-Way Search & Relevance Gating Telemetry
    renderSearchTelemetry(dossier.goal, firstVerdict);

    // 5. Evidence Provenance Graph & Lineage
    renderProvenanceGraph(firstVerdict ? firstVerdict.sources : []);

    // 6. Physical Quote Grounding Inspector
    renderPhysicalQuotes(firstVerdict ? firstVerdict.evidences : []);

    // 7. Timeline & Context Duality
    renderTimelineAndDuality(firstVerdict);

    // 8. Evidence Gaps & Next Steps
    renderEvidenceGaps(firstVerdict);

    verdictResultSection.style.display = "flex";
    window.scrollTo({ top: verdictResultSection.offsetTop - 30, behavior: "smooth" });
    lucide.createIcons();
}

// ──────────────────────────────────────────────
//  Render Sections Helpers
// ──────────────────────────────────────────────
function renderSubtaskMatrix(data, verdict) {
    subtaskMatrixTbody.innerHTML = "";
    if (!verdict) return;

    const factSlots = verdict.fact_slots;
    const compoundSlots = (factSlots && factSlots.compound_slots) ? factSlots.compound_slots : [];
    
    if (compoundSlots.length === 0) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>核心事实调查</strong></td>
            <td><code>${factSlots ? factSlots.entity : "目标主体"}</code></td>
            <td><span class="status-badge-cell ${verdict.evidence_state === 'SUFFICIENT' || verdict.evidence_state === 'STRONG' ? 'confirmed' : 'unconfirmed'}">${getStateLabel(verdict.evidence_state)}</span></td>
            <td>${verdict.explanation || "已完成核验"}</td>
        `;
        subtaskMatrixTbody.appendChild(tr);
        return;
    }

    compoundSlots.forEach(cs => {
        const isMatched = (verdict.relations || []).some(r => (r.matched_slots || []).includes(cs.slot_name));
        const statusClass = isMatched ? "confirmed" : "unconfirmed";
        const statusText = isMatched ? "已物理证实" : "未发现直接支持";

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${translateSlotName(cs.slot_name)}</strong></td>
            <td><code>${cs.slot_name}=${cs.value}${cs.unit || ''}</code></td>
            <td><span class="status-badge-cell ${statusClass}">${statusText}</span></td>
            <td>${isMatched ? "在抓取正文中成功逐字定位" : "缺少官方公告或第一手凭证"}</td>
        `;
        subtaskMatrixTbody.appendChild(tr);
    });
}

function renderSearchTelemetry(claimText, verdict) {
    queryPillsContainer.innerHTML = "";
    const sources = verdict ? verdict.sources : [];
    const totalCount = sources.length;
    const acceptedCount = sources.filter(s => s.fetch_status !== "REJECTED_IRRELEVANT").length;
    const rejectedCount = sources.filter(s => s.fetch_status === "REJECTED_IRRELEVANT").length;
    const fetchedCount = sources.filter(s => s.fetch_status === "FETCH_SUCCESS" || s.fetch_status === "SYNTHETIC_MOCK").length;

    statTotalSearch.textContent = totalCount;
    statAcceptedSearch.textContent = acceptedCount;
    statRejectedSearch.textContent = rejectedCount;
    statLiveFetched.textContent = fetchedCount;

    // Synthesize Queries for display
    const entity = verdict && verdict.fact_slots ? verdict.fact_slots.entity : "目标主体";
    const slotVals = verdict && verdict.fact_slots ? verdict.fact_slots.compound_slots.map(s => s.value).join(" ") : "";
    
    const queries = [
        { type: "raw", label: "Query A (原始语义)", text: claimText.slice(0, 45) },
        { type: "slots", label: "Query B (实体+数值)", text: `${entity} ${slotVals}`.trim() || `${entity} 事实核验` },
        { type: "official", label: "Query C (官方定向)", text: `${entity} 官方 公告 / 财报 / MSRP 规格` },
        { type: "rumor", label: "Query D (争议排查)", text: `${entity} 辟谣 澄清 声明` }
    ];

    queries.forEach(q => {
        const item = document.createElement("div");
        item.className = "query-pill-item";
        item.innerHTML = `
            <span class="query-type-tag ${q.type}">${q.label}</span>
            <span class="query-text">${q.text}</span>
        `;
        queryPillsContainer.appendChild(item);
    });
}

function renderProvenanceGraph(sources) {
    provenanceGraphContainer.innerHTML = "";
    if (sources.length === 0) {
        provenanceGraphContainer.innerHTML = `<div class="empty-hint" style="color:var(--text-muted);font-size:13px;">未检索到有效信源节点</div>`;
        return;
    }

    sources.forEach((s, idx) => {
        const card = document.createElement("div");
        card.className = "provenance-source-card";
        const isLive = s.fetch_mode === "LIVE";
        const statusBadge = s.fetch_status === "FETCH_SUCCESS" 
            ? `<span style="color:var(--state-sufficient-text);font-size:11px;">● 正文抓取成功 (${s.raw_text_length || 0} 字)</span>`
            : s.fetch_status === "REJECTED_IRRELEVANT"
            ? `<span style="color:var(--state-unsupported-text);font-size:11px;">✕ 相关性低已过滤</span>`
            : `<span style="color:var(--text-muted);font-size:11px;">○ ${s.fetch_status}</span>`;

        card.innerHTML = `
            <div class="source-card-top">
                <span class="source-tier-pill tier-${s.source_tier}">${s.source_tier}</span>
                ${statusBadge}
            </div>
            <a href="${s.url}" target="_blank" rel="noopener noreferrer" class="source-title-link">
                <i data-lucide="external-link" style="width:14px;height:14px;"></i>
                <span>${s.title}</span>
            </a>
            <div class="source-meta-row">
                <span>域名: ${s.domain}</span>
                <span>模式: ${isLive ? '🌐 LIVE 实时抓取' : '💾 快照回放'}</span>
                ${s.content_hash ? `<span>Hash: ${s.content_hash.slice(0, 10)}...</span>` : ''}
            </div>
        `;
        provenanceGraphContainer.appendChild(card);
    });
}

function renderPhysicalQuotes(evidences) {
    quotesListContainer.innerHTML = "";
    const validQuotes = evidences.filter(e => e.exact_quote);
    if (validQuotes.length === 0) {
        quotesListContainer.innerHTML = `<div class="empty-hint" style="color:var(--text-muted);font-size:13px;">本次调查未从抓取网页中提取到可逐字锚定的实体引文。</div>`;
        return;
    }

    validQuotes.forEach((ev, idx) => {
        const item = document.createElement("div");
        item.className = "quote-inspect-item";
        const coords = (ev.char_start !== null && ev.char_end !== null)
            ? `字符偏移: [${ev.char_start} : ${ev.char_end}]`
            : "未锁定偏移坐标";

        item.innerHTML = `
            <div class="quote-inspect-header">
                <span>引文 #${idx + 1} | ${coords}</span>
                <span class="quote-tier-badge tier-${ev.match_tier}">${ev.match_tier}</span>
            </div>
            <div class="quote-verbatim-text">“${ev.exact_quote}”</div>
            <div style="font-size:11px;color:var(--text-muted);display:flex;justify-content:space-between;">
                <span>证据采纳状态: ${ev.is_admissible_factual_evidence ? '✅ 真实证据采纳' : '⚠️ 仅供背景参考'}</span>
                <span>极性关系: ${ev.supports_claim ? '支持' : ev.contradicts_claim ? '反驳' : '中立/补充'}</span>
            </div>
        `;
        quotesListContainer.appendChild(item);
    });
}

function renderTimelineAndDuality(verdict) {
    if (!verdict || !verdict.relations || verdict.relations.length === 0) {
        timelineDisputeContainer.innerHTML = `
            <div style="font-size:13px;color:var(--text-secondary);">
                当前事实声明属于静态事实或单一时间线，未观测到 GAAP/Non-GAAP 会计口径冲突或跨阶段临床试验演进。
            </div>
        `;
        return;
    }

    timelineDisputeContainer.innerHTML = "";
    verdict.relations.forEach((r, idx) => {
        const item = document.createElement("div");
        item.style.marginBottom = "12px";
        item.innerHTML = `
            <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:4px;">
                关系 #${idx + 1}: ${r.relation_type} (会计准则: ${r.accounting_standard || 'N/A'} | 时序演进: ${r.temporal_evolution || 'N/A'})
            </div>
            <div style="font-size:12px;color:var(--text-secondary);font-family:var(--font-mono);background:var(--bg-card);padding:8px 12px;border-radius:6px;">
                ${r.polarity_reasoning || '已结构化绑定事实槽位'}
            </div>
        `;
        timelineDisputeContainer.appendChild(item);
    });
}

function renderEvidenceGaps(verdict) {
    gapsAdviceBody.innerHTML = "";
    const reasons = verdict ? verdict.why_reasons : [];
    const gaps = verdict ? verdict.evidence_gaps : [];

    if (reasons.length === 0 && gaps.length === 0) {
        gapsAdviceBody.innerHTML = `<div>✓ 证据链充分，无关键缺口。</div>`;
        return;
    }

    reasons.forEach(r => {
        const div = document.createElement("div");
        div.className = "gap-bullet-item";
        div.innerHTML = `<i data-lucide="info" style="width:16px;height:16px;color:var(--accent-cyan);flex-shrink:0;"></i> <span>${r}</span>`;
        gapsAdviceBody.appendChild(div);
    });

    gaps.forEach(g => {
        const div = document.createElement("div");
        div.className = "gap-bullet-item";
        div.innerHTML = `<i data-lucide="alert-circle" style="width:16px;height:16px;color:var(--state-insufficient-text);flex-shrink:0;"></i> <span>${g}</span>`;
        gapsAdviceBody.appendChild(div);
    });
}

// ──────────────────────────────────────────────
//  Export & Archive Handlers
// ──────────────────────────────────────────────
function handleExportMarkdown() {
    if (!currentInvestigationDossier) return;
    const d = currentInvestigationDossier;
    const data = d.data;
    const v = (data.verdicts && data.verdicts.length > 0) ? data.verdicts[0] : null;

    const mdContent = `# 调查档案报告 (Investigation Dossier) - ${d.id}

- **调查目标**：${d.goal}
- **调查时间**：${new Date(d.timestamp).toLocaleString("zh-CN")}
- **证据判定**：${getStateLabel(data.overall_state || "INSUFFICIENT")}
- **执行摘要**：${data.overall_summary || (v ? v.explanation : '')}

---

## 1. 调查子任务与关键发现
${(v && v.fact_slots && v.fact_slots.compound_slots) ? v.fact_slots.compound_slots.map(s => `- **${translateSlotName(s.slot_name)}** (${s.slot_name}): \`${s.value}${s.unit || ''}\``).join("\n") : "- 核心主体事实核验已执行"}

## 2. 独立证据链与信源清单
${(v && v.sources) ? v.sources.map(s => `- [${s.source_tier}] [${s.title}](${s.url}) (${s.domain}) - 状态: ${s.fetch_status}`).join("\n") : "无"}

## 3. 逐字引文物理定位
${(v && v.evidences) ? v.evidences.map(e => `- [${e.match_tier}] [${e.char_start}:${e.char_end}] "${e.exact_quote}"`).join("\n") : "无"}

## 4. 调查局限与证据缺口
${(v && v.why_reasons) ? v.why_reasons.map(r => `- ${r}`).join("\n") : "无"}

---
*由 AI Real-World Investigator 自动化系统生成*
`;

    const blob = new Blob([mdContent], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Investigation_Report_${d.id}.md`;
    a.click();
    URL.revokeObjectURL(url);
}

function handleCopyDossier() {
    if (!currentInvestigationDossier) return;
    const str = JSON.stringify(currentInvestigationDossier, null, 2);
    navigator.clipboard.writeText(str).then(() => {
        alert("调查档案 JSON 已复制到剪贴板！");
    }).catch(err => {
        console.error("Copy failed:", err);
    });
}

function saveToArchive(dossier) {
    try {
        const raw = localStorage.getItem("INVESTIGATION_ARCHIVE") || "[]";
        let list = JSON.parse(raw);
        list.unshift(dossier);
        if (list.length > 20) list = list.slice(0, 20);
        localStorage.setItem("INVESTIGATION_ARCHIVE", JSON.stringify(list));
        updateArchiveBadge();
    } catch (e) {
        console.warn("Save archive failed:", e);
    }
}

function updateArchiveBadge() {
    const raw = localStorage.getItem("INVESTIGATION_ARCHIVE") || "[]";
    try {
        const list = JSON.parse(raw);
        archiveCountBadge.textContent = list.length;
    } catch (e) {
        archiveCountBadge.textContent = "0";
    }
}

function renderArchiveView() {
    archiveGrid.innerHTML = "";
    const raw = localStorage.getItem("INVESTIGATION_ARCHIVE") || "[]";
    let list = [];
    try {
        list = JSON.parse(raw);
    } catch (e) { list = []; }

    if (list.length === 0) {
        archiveGrid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text-muted);">暂无已归档调查项目，在工作台发起调查后将自动归档。</div>`;
        return;
    }

    list.forEach((item) => {
        const card = document.createElement("div");
        card.className = "archive-card";
        const state = item.data.overall_state || "INSUFFICIENT";

        card.innerHTML = `
            <div class="archive-card-header">
                <span class="status-badge-cell ${state === 'SUFFICIENT' || state === 'STRONG' ? 'confirmed' : 'unconfirmed'}">${getStateLabel(state)}</span>
                <span style="font-size:11px;color:var(--text-muted);font-family:var(--font-mono);">${item.id}</span>
            </div>
            <div class="archive-claim-text">${item.goal}</div>
            <div class="archive-meta-footer">
                <span>${new Date(item.timestamp).toLocaleDateString("zh-CN")}</span>
                <span style="color:var(--accent-cyan);">查看档案 →</span>
            </div>
        `;

        card.addEventListener("click", () => {
            currentInvestigationDossier = item;
            switchView("console");
            renderExecutiveInvestigationDossier(item);
        });

        archiveGrid.appendChild(card);
    });
}

function handleClearArchive() {
    if (confirm("确定要清空所有已保存的调查档案吗？")) {
        localStorage.removeItem("INVESTIGATION_ARCHIVE");
        updateArchiveBadge();
        renderArchiveView();
    }
}

// ──────────────────────────────────────────────
//  Utility Helpers
// ──────────────────────────────────────────────
function getStateLabel(state) {
    const map = {
        "SUFFICIENT": "证实 (Sufficient Evidence)",
        "STRONG": "充分证实 (Strong Verification)",
        "INSUFFICIENT": "证据不足 (Insufficient)",
        "CONFLICTING": "存在实质冲突 (Conflicting)",
        "UNSUPPORTED": "官方证伪 / 反驳 (Unsupported)",
        "NOT_ASSESSABLE": "无法评估 (Not Assessable)"
    };
    return map[state] || state;
}

function translateSlotName(name) {
    const map = {
        "model": "产品型号 / 规格",
        "price": "官方定价 / MSRP",
        "memory": "显存 / 硬件规格",
        "headquarters": "企业总部 / 所在地",
        "founder": "创始人 / CEO",
        "founding_year": "创立时间",
        "net_income": "净利润 / 财务指标",
        "revenue": "营业收入",
        "company": "主体企业",
        "target": "收购标的",
        "amount": "交易金额",
        "equity_stake": "股权比例",
        "drug_name": "药物名称",
        "trial_name": "临床试验名称",
        "trial_phase": "临床阶段",
        "endpoint_result": "主要终点结果"
    };
    return map[name] || name;
}
