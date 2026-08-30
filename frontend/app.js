// AI Claim Verifier — Frontend Application Logic (v4 Final)

const API_BASE = window.location.origin.includes(":8000") || window.location.origin.includes(":3000")
    ? `${window.location.origin}/api/v1`
    : "http://127.0.0.1:8000/api/v1";

// Global State
let currentInputMode = "TEXT";
let currentUploadedImageBase64 = null;
let currentVerificationResult = null;

// DOM Elements
const verifyForm = document.getElementById("verify-form");
const claimInput = document.getElementById("claim-input");
const btnStartVerify = document.getElementById("btn-start-verify");
const imageUploadInput = document.getElementById("image-upload-input");
const imagePreviewBox = document.getElementById("image-preview-box");
const imagePreviewImg = document.getElementById("image-preview-img");
const previewFileName = document.getElementById("preview-file-name");
const btnRemoveImage = document.getElementById("btn-remove-image");

const loadingStateCard = document.getElementById("loading-state-card");
const loadingTitle = document.getElementById("loading-title");
const loadingDesc = document.getElementById("loading-desc");

const verdictResultSection = document.getElementById("verdict-result-section");
const overallSummaryCard = document.getElementById("overall-summary-card");
const overallStatePill = document.getElementById("overall-state-pill");
const overallStateText = document.getElementById("overall-state-text");
const overallSummaryText = document.getElementById("overall-summary-text");
const coverageTableBody = document.getElementById("coverage-table-body");
const verdictCardsContainer = document.getElementById("verdict-cards-container");

const btnNewVerify = document.getElementById("btn-new-verify");
const btnCopyVerdict = document.getElementById("btn-copy-verdict");
const recentHistoryGrid = document.getElementById("recent-history-grid");
const currentEngineLabel = document.getElementById("current-engine-label");

// Settings Elements
const btnOpenSettings = document.getElementById("btn-open-settings");
const settingsModal = document.getElementById("settings-modal");
const btnCloseSettings = document.getElementById("btn-close-settings");
const btnCancelSettings = document.getElementById("btn-cancel-settings");
const btnSaveSettings = document.getElementById("btn-save-settings");

const setLlmSelect = document.getElementById("set-llm-select");
const setSearchSelect = document.getElementById("set-search-select");
const setGeminiKey = document.getElementById("set-gemini-key");
const setOpenaiKey = document.getElementById("set-openai-key");
const setTavilyKey = document.getElementById("set-tavily-key");

// Initialization
document.addEventListener("DOMContentLoaded", () => {
    lucide.createIcons();
    loadSavedSettings();
    setupEventListeners();
    renderRecentHistory();
});

function loadSavedSettings() {
    if (localStorage.getItem("VERIFIER_LLM_PROVIDER")) {
        setLlmSelect.value = localStorage.getItem("VERIFIER_LLM_PROVIDER");
    }
    if (localStorage.getItem("VERIFIER_SEARCH_PROVIDER")) {
        setSearchSelect.value = localStorage.getItem("VERIFIER_SEARCH_PROVIDER");
    }
    if (localStorage.getItem("INVESTIGATOR_GEMINI_KEY")) {
        setGeminiKey.value = localStorage.getItem("INVESTIGATOR_GEMINI_KEY");
    }
    if (localStorage.getItem("INVESTIGATOR_OPENAI_KEY")) {
        setOpenaiKey.value = localStorage.getItem("INVESTIGATOR_OPENAI_KEY");
    }
    if (localStorage.getItem("INVESTIGATOR_TAVILY_KEY")) {
        setTavilyKey.value = localStorage.getItem("INVESTIGATOR_TAVILY_KEY");
    }
    updateEngineLabel();
}

function updateEngineLabel() {
    const llm = setLlmSelect.value;
    const search = setSearchSelect.value;
    if (llm === "mock" && search === "mock") {
        currentEngineLabel.textContent = "运行模式: 离线拟真引擎 (内置事实库)";
    } else {
        currentEngineLabel.textContent = `运行模式: ${llm.toUpperCase()} + ${search.toUpperCase()}`;
    }
}

function getActiveApiKeys() {
    return {
        gemini_api_key: localStorage.getItem("INVESTIGATOR_GEMINI_KEY") || "",
        openai_api_key: localStorage.getItem("INVESTIGATOR_OPENAI_KEY") || "",
        tavily_api_key: localStorage.getItem("INVESTIGATOR_TAVILY_KEY") || ""
    };
}

function setupEventListeners() {
    // Input Mode Tabs
    document.querySelectorAll(".input-mode-tabs .mode-tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".input-mode-tabs .mode-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            currentInputMode = tab.dataset.mode;
            handleInputModeChange(currentInputMode);
        });
    });

    // Image Upload & Removal
    btnRemoveImage.addEventListener("click", () => {
        currentUploadedImageBase64 = null;
        imageUploadInput.value = "";
        imagePreviewBox.style.display = "none";
        claimInput.style.display = "block";
    });

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

    // Sample Chips Click
    document.querySelectorAll(".sample-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            claimInput.value = chip.dataset.sample;
            claimInput.focus();
        });
    });

    // Main Verification Form Submit
    verifyForm.addEventListener("submit", handleStartVerification);

    // Reset & Action Buttons
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

    btnCopyVerdict.addEventListener("click", handleCopyVerdict);

    // Settings Modal
    btnOpenSettings.addEventListener("click", () => settingsModal.style.display = "flex");
    btnCloseSettings.addEventListener("click", () => settingsModal.style.display = "none");
    btnCancelSettings.addEventListener("click", () => settingsModal.style.display = "none");
    btnSaveSettings.addEventListener("click", () => {
        localStorage.setItem("VERIFIER_LLM_PROVIDER", setLlmSelect.value);
        localStorage.setItem("VERIFIER_SEARCH_PROVIDER", setSearchSelect.value);
        localStorage.setItem("INVESTIGATOR_GEMINI_KEY", setGeminiKey.value.trim());
        localStorage.setItem("INVESTIGATOR_OPENAI_KEY", setOpenaiKey.value.trim());
        localStorage.setItem("INVESTIGATOR_TAVILY_KEY", setTavilyKey.value.trim());
        settingsModal.style.display = "none";
        updateEngineLabel();
        alert("配置已保存！将在下次核验时立即生效。");
    });
}

function handleInputModeChange(mode) {
    if (mode === "IMAGE") {
        imageUploadInput.click();
    } else if (mode === "URL") {
        imagePreviewBox.style.display = "none";
        claimInput.style.display = "block";
        claimInput.placeholder = "粘贴需要核验的新闻或文章网页链接 (https://...)\n系统将自动抓取正文并提取可验证事实";
    } else {
        imagePreviewBox.style.display = "none";
        claimInput.style.display = "block";
        claimInput.placeholder = "把你看到的说法、新闻快讯或争议声明贴进来...\n例如：宇树科技于2024年完成近10亿元人民币B2轮融资，美团领投";
    }
}

// ──────────────────────────────────────────────
//  Start Verification Pipeline
// ──────────────────────────────────────────────
async function handleStartVerification(e) {
    e.preventDefault();
    let text = claimInput.value.trim();
    if (currentInputMode === "IMAGE") {
        if (!currentUploadedImageBase64) {
            alert("请先上传要核验的截图文件。");
            return;
        }
        text = `[截图核验 - ${previewFileName.textContent}] (自动解析)`;
    }

    if (!text) return;

    // UI State -> Loading
    btnStartVerify.disabled = true;
    btnStartVerify.innerHTML = `<span class="spinner-inline"></span> 正在核验...`;
    loadingStateCard.style.display = "flex";
    verdictResultSection.style.display = "none";

    try {
        const payload = {
            claim: text,
            input_type: currentInputMode,
            llm_provider: setLlmSelect.value || "mock",
            search_provider: setSearchSelect.value || "mock",
            api_keys: getActiveApiKeys()
        };

        const res = await fetch(`${API_BASE}/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            throw new Error(`服务响应异常 (${res.status})`);
        }

        const coverage = await res.json();
        currentVerificationResult = coverage;

        // Render Results
        renderVerificationResult(coverage);

        // Save to History
        saveToRecentHistory(coverage);

        // Scroll to Result
        setTimeout(() => {
            verdictResultSection.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 100);

    } catch (err) {
        console.error("Verification failed:", err);
        alert(`核验未能完成: ${err.message}`);
    } finally {
        btnStartVerify.disabled = false;
        btnStartVerify.innerHTML = `<i data-lucide="search-check"></i> 开始核验`;
        loadingStateCard.style.display = "none";
        lucide.createIcons();
    }
}

// ──────────────────────────────────────────────
//  Render Verdict & Coverage
// ──────────────────────────────────────────────
function renderVerificationResult(coverage) {
    const claims = coverage.claims || [];
    const verdicts = coverage.verdicts || [];
    const verdictMap = {};
    verdicts.forEach(v => {
        verdictMap[v.claim_id] = v;
    });

    verdictCardsContainer.innerHTML = "";

    // 1. Overall Multi-Claim Coverage Table
    if (claims.length > 1) {
        overallSummaryCard.style.display = "block";
        const overallStateInfo = formatOverallState(coverage.overall_state);
        overallStatePill.className = `overall-state-pill ${overallStateInfo.className}`;
        overallStateText.textContent = overallStateInfo.label;
        overallSummaryText.textContent = coverage.coverage_summary || "多主张核验覆盖完成。";

        coverageTableBody.innerHTML = claims.map((c, i) => {
            const v = verdictMap[c.id] || {};
            const stateInfo = formatEvidenceState(v.evidence_state);
            const verifInfo = formatVerifiability(c.verifiability);
            return `
                <tr>
                    <td style="font-family:var(--font-mono);font-weight:700;color:var(--text-muted);">${i+1}</td>
                    <td style="font-weight:600;color:var(--text-primary);">${escapeHtml(c.statement)}</td>
                    <td><span class="verif-tag">${verifInfo}</span></td>
                    <td><span class="verdict-state-pill ${stateInfo.className}">${stateInfo.label}</span></td>
                </tr>
            `;
        }).join("");
    } else {
        overallSummaryCard.style.display = "none";
    }

    // 2. Render Detailed Verdict Cards
    claims.forEach((claim, idx) => {
        const verdict = verdictMap[claim.id] || { evidence_state: "INSUFFICIENT", why_reasons: [], evidence_gaps: [] };
        const stateInfo = formatEvidenceState(verdict.evidence_state);
        const verifInfo = formatVerifiability(claim.verifiability);
        const assessment = verdict.assessment || {};
        const sources = verdict.sources || [];
        const evidences = verdict.evidences || [];
        const provenances = verdict.provenances || [];

        const card = document.createElement("div");
        card.className = "verdict-card";

        // Tab 1: Why reasons list
        const reasons = verdict.why_reasons || [];
        const reasonsHtml = reasons.map(r => {
            let iconClass = "reason-bullet-check";
            if (r.startsWith("!")) iconClass = "reason-bullet-warn";
            if (r.startsWith("ℹ")) iconClass = "reason-bullet-info";
            return `
                <div class="why-reason-item">
                    <span class="why-icon-badge ${iconClass}">${escapeHtml(r.slice(0, 1))}</span>
                    <span class="why-text">${escapeHtml(r.slice(1).trim())}</span>
                </div>
            `;
        }).join("");

        const gaps = verdict.evidence_gaps || [];
        const gapsHtml = gaps.length > 0 ? `
            <div class="evidence-gaps-block">
                <div class="block-label"><i data-lucide="alert-circle"></i> 关键证据缺口</div>
                <div class="gaps-list">
                    ${gaps.map(g => `<div class="gap-item">⚠ ${escapeHtml(g)}</div>`).join("")}
                </div>
            </div>
        ` : "";

        const adviceHtml = verdict.next_step_advice ? `
            <div class="advice-block">
                <div class="block-label"><i data-lucide="compass"></i> 下一步核实建议</div>
                <div class="advice-text">${escapeHtml(verdict.next_step_advice)}</div>
            </div>
        ` : "";

        // Tab 2: Provenance DAG Nodes
        const provMap = {};
        provenances.forEach(p => {
            provMap[p.source_id] = p;
        });

        const sourcesDagHtml = sources.length > 0 ? sources.map(s => {
            const tierClass = `tier-${(s.source_tier || "unknown").toLowerCase()}`;
            const prov = provMap[s.id];
            const republishHtml = prov ? `
                <div class="dag-republish-tag" title="${escapeHtml(prov.explanation || '')}">
                    <i data-lucide="git-branch" style="width:12px;height:12px;"></i> ${escapeHtml(prov.explanation || '同源转载')}
                </div>
            ` : "";
            return `
                <div class="dag-node-card">
                    <div class="dag-node-header">
                        <span class="dag-tier-badge ${tierClass}">${escapeHtml(s.source_tier || 'UNKNOWN')}</span>
                        ${s.is_synthetic ? '<span class="verif-tag" style="font-size:0.65rem;">测试快照</span>' : ''}
                    </div>
                    <div class="dag-node-domain">${escapeHtml(s.domain || s.title)}</div>
                    ${republishHtml}
                </div>
            `;
        }).join("") : '<div class="why-text">暂无检索信源</div>';

        const quotesDagHtml = evidences.length > 0 ? evidences.map(e => {
            let polarityClass = "polarity-context";
            let polarityLabel = "⚪ 背景";
            if (e.supports_claim) {
                polarityClass = "polarity-support";
                polarityLabel = "🟢 支持 (DIRECT)";
            } else if (e.contradicts_claim) {
                polarityClass = "polarity-contradict";
                polarityLabel = "🔴 反驳 (DIRECT)";
            }
            return `
                <div class="dag-node-card">
                    <div class="dag-quote-polarity ${polarityClass}">${polarityLabel}</div>
                    <div style="font-size:0.8rem;color:var(--text-primary);margin-top:6px;line-height:1.4;">
                        "${escapeHtml(e.exact_quote ? e.exact_quote.slice(0, 70) + (e.exact_quote.length > 70 ? '...' : '') : '')}"
                    </div>
                </div>
            `;
        }).join("") : '<div class="why-text">暂无提取证据</div>';

        // Tab 3: Raw-Text Quote Inspector Cards
        const quotesInspectorHtml = evidences.length > 0 ? evidences.map((e, qIdx) => {
            let tierPillClass = "tier-exact";
            let tierLabel = "EXACT";
            if (e.locator_tier === "NORMALIZED_EXACT") {
                tierPillClass = "tier-normalized";
                tierLabel = "NORMALIZED_EXACT";
            } else if (e.locator_tier === "UNVERIFIED") {
                tierPillClass = "tier-unverified";
                tierLabel = "UNVERIFIED (HALLUCINATION REJECTED)";
            }

            const charRange = (e.char_start !== undefined && e.char_end !== undefined && e.char_start !== null) 
                ? `[char ${e.char_start}:${e.char_end}]` 
                : `[char-level verified]`;

            return `
                <div class="quote-inspector-card">
                    <div class="quote-card-meta">
                        <span class="quote-tier-pill ${tierPillClass}">
                            <i data-lucide="shield-check" style="width:13px;height:13px;"></i> ${tierLabel} ${charRange}
                        </span>
                        <span style="font-family:var(--font-mono);font-size:0.75rem;color:var(--text-muted);">
                            信源 ID: ${escapeHtml(e.source_id)}
                        </span>
                    </div>
                    <div class="quote-text-block">
                        ${escapeHtml(e.exact_quote)}
                    </div>
                    ${e.context ? `<div class="quote-context-preview">上下文: ${escapeHtml(e.context)}</div>` : ''}
                    ${e.evidence_note ? `<div style="font-size:0.75rem;color:var(--text-secondary);margin-top:4px;">备注: ${escapeHtml(e.evidence_note)}</div>` : ''}
                </div>
            `;
        }).join("") : '<div class="why-text">暂无提取引文</div>';

        // Tab 4: Telemetry Metrics
        const indepCount = assessment.independent_source_count !== undefined ? assessment.independent_source_count : sources.length;
        const officialCount = assessment.official_source_count !== undefined ? assessment.official_source_count : 0;
        const directSupportCount = assessment.direct_support_count !== undefined ? assessment.direct_support_count : (evidences.filter(e => e.supports_claim).length);
        const contradictCount = assessment.direct_contradiction_count !== undefined ? assessment.direct_contradiction_count : (evidences.filter(e => e.contradicts_claim).length);
        const republishCount = assessment.republish_count !== undefined ? assessment.republish_count : provenances.length;

        card.innerHTML = `
            <div class="verdict-card-header">
                <div class="verdict-main-badge-wrap">
                    <span class="verdict-state-pill lg ${stateInfo.className}">${stateInfo.label}</span>
                    <span class="verif-tag">${verifInfo}</span>
                </div>
                <span class="as-of-label">核验时间: ${verdict.verified_as_of || "最新"}</span>
            </div>

            <div class="verdict-claim-box">
                <h3 class="verdict-statement-heading">${escapeHtml(claim.statement)}</h3>
            </div>

            <!-- Tab Navigation Header -->
            <div class="verdict-tab-nav" data-card-idx="${idx}">
                <button type="button" class="verdict-tab-btn active" data-tab="summary-${idx}">
                    <i data-lucide="check-square" style="width:14px;height:14px;"></i> 结论与依据
                </button>
                <button type="button" class="verdict-tab-btn" data-tab="graph-${idx}">
                    <i data-lucide="git-merge" style="width:14px;height:14px;"></i> 证据链图谱 (${sources.length}信源)
                </button>
                <button type="button" class="verdict-tab-btn" data-tab="quotes-${idx}">
                    <i data-lucide="quote" style="width:14px;height:14px;"></i> 逐字引文透视 (${evidences.length}条)
                </button>
                <button type="button" class="verdict-tab-btn" data-tab="metrics-${idx}">
                    <i data-lucide="activity" style="width:14px;height:14px;"></i> 规则判定度量
                </button>
            </div>

            <!-- Tab 1: Summary Pane -->
            <div class="verdict-tab-pane active" id="tab-summary-${idx}">
                <div class="verdict-reasons-block">
                    <div class="block-label"><i data-lucide="list-checks"></i> 为什么这样判断？(判定依据)</div>
                    <div class="why-reasons-list">
                        ${reasonsHtml || '<div class="why-text">暂无详细判定理由</div>'}
                    </div>
                </div>
                ${gapsHtml}
                ${adviceHtml}
            </div>

            <!-- Tab 2: Provenance DAG Pane -->
            <div class="verdict-tab-pane" id="tab-graph-${idx}">
                <div class="provenance-dag-wrap">
                    <div class="dag-flow-grid">
                        <div class="dag-stage-col">
                            <div class="dag-col-title"><i data-lucide="globe" style="width:13px;height:13px;"></i> 1. 检索公开信源</div>
                            ${sourcesDagHtml}
                        </div>
                        <div class="dag-stage-col">
                            <div class="dag-col-title"><i data-lucide="file-text" style="width:13px;height:13px;"></i> 2. 证据极性判定</div>
                            ${quotesDagHtml}
                        </div>
                        <div class="dag-stage-col">
                            <div class="dag-col-title"><i data-lucide="cpu" style="width:13px;height:13px;"></i> 3. 确定性规则门</div>
                            <div class="dag-node-card" style="border-left: 3px solid var(--accent-cyan);">
                                <div style="font-size:0.75rem;color:var(--text-muted);font-weight:700;">RULE GATE</div>
                                <div style="font-size:0.85rem;color:var(--text-primary);margin:4px 0;">
                                    独立信源: <strong>${indepCount}</strong> 个<br>
                                    官方直证: <strong>${officialCount}</strong> 个<br>
                                    直接反驳: <strong>${contradictCount}</strong> 个
                                </div>
                                <span class="verdict-state-pill sm ${stateInfo.className}">${stateInfo.label}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tab 3: Quotes Inspector Pane -->
            <div class="verdict-tab-pane" id="tab-quotes-${idx}">
                <div class="quotes-inspector-grid">
                    ${quotesInspectorHtml}
                </div>
            </div>

            <!-- Tab 4: Telemetry Metrics Pane -->
            <div class="verdict-tab-pane" id="tab-metrics-${idx}">
                <div class="telemetry-grid">
                    <div class="telemetry-card">
                        <div class="telemetry-val">${indepCount}</div>
                        <div class="telemetry-label">独立有效信源数 ($N_{indep}$)</div>
                    </div>
                    <div class="telemetry-card">
                        <div class="telemetry-val">${officialCount}</div>
                        <div class="telemetry-label">官方一手信源数 ($N_{official}$)</div>
                    </div>
                    <div class="telemetry-card">
                        <div class="telemetry-val">${directSupportCount}</div>
                        <div class="telemetry-label">直接强证实证据 ($N_{support}$)</div>
                    </div>
                    <div class="telemetry-card">
                        <div class="telemetry-val">${contradictCount}</div>
                        <div class="telemetry-label">直接权威反驳 ($N_{contra}$)</div>
                    </div>
                    <div class="telemetry-card">
                        <div class="telemetry-val">${republishCount}</div>
                        <div class="telemetry-label">同源转载去重数 ($N_{republish}$)</div>
                    </div>
                </div>
            </div>
        `;

        // Attach Tab Click Handlers
        card.querySelectorAll(".verdict-tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const targetTab = btn.dataset.tab;
                card.querySelectorAll(".verdict-tab-btn").forEach(b => b.classList.remove("active"));
                card.querySelectorAll(".verdict-tab-pane").forEach(p => p.classList.remove("active"));
                btn.classList.add("active");
                const targetPane = card.querySelector(`#tab-${targetTab}`);
                if (targetPane) targetPane.classList.add("active");
                lucide.createIcons();
            });
        });

        verdictCardsContainer.appendChild(card);
    });

    verdictResultSection.style.display = "block";
    lucide.createIcons();
}


// ──────────────────────────────────────────────
//  Presentation Format Helpers
// ──────────────────────────────────────────────
function formatEvidenceState(state) {
    switch (state) {
        case "SUFFICIENT":
            return { label: "🟢 证据充分", className: "state-sufficient" };
        case "STRONG":
            return { label: "🟢 证据较强", className: "state-strong" };
        case "INSUFFICIENT":
            return { label: "🟡 证据不足", className: "state-insufficient" };
        case "CONFLICTING":
            return { label: "🟠 存在冲突", className: "state-conflicting" };
        case "UNSUPPORTED":
            return { label: "🔴 有可靠证据反驳", className: "state-unsupported" };
        case "NOT_ASSESSABLE":
            return { label: "⚪ 公开资料无法核验", className: "state-not-assessable" };
        default:
            return { label: "🟡 证据不足", className: "state-insufficient" };
    }
}

function formatOverallState(state) {
    switch (state) {
        case "FULLY_SUPPORTED":
            return { label: "🟢 全部支持", className: "state-sufficient" };
        case "PARTIALLY_SUPPORTED":
            return { label: "🟢 部分支持", className: "state-strong" };
        case "MIXED":
            return { label: "🟠 结论存在分歧", className: "state-conflicting" };
        case "FULLY_UNSUPPORTED":
            return { label: "🔴 均有反驳", className: "state-unsupported" };
        case "NOT_ASSESSABLE":
            return { label: "⚪ 无法有效核验", className: "state-not-assessable" };
        default:
            return { label: "🟡 证据有限", className: "state-insufficient" };
    }
}

function formatVerifiability(v) {
    switch (v) {
        case "PUBLICLY_VERIFIABLE":
            return "公开可验证事实";
        case "LIMITED_PUBLIC":
            return "有限公开信息";
        case "HARD_TO_VERIFY":
            return "极难公开求证";
        case "NOT_PUBLICLY_VERIFIABLE":
            return "无法公开验证";
        default:
            return "公开事实";
    }
}

// ──────────────────────────────────────────────
//  History & Copy Utilities
// ──────────────────────────────────────────────
function saveToRecentHistory(coverage) {
    let history = [];
    try {
        history = JSON.parse(localStorage.getItem("VERIFIER_HISTORY") || "[]");
    } catch (_) {}

    const item = {
        id: Date.now().toString(),
        input: coverage.original_input,
        state: coverage.overall_state,
        claims_count: (coverage.claims || []).length,
        time: new Date().toLocaleDateString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }),
        coverage: coverage
    };

    history.unshift(item);
    if (history.length > 8) history.pop();
    localStorage.setItem("VERIFIER_HISTORY", JSON.stringify(history));
    renderRecentHistory();
}

function renderRecentHistory() {
    let history = [];
    try {
        history = JSON.parse(localStorage.getItem("VERIFIER_HISTORY") || "[]");
    } catch (_) {}

    if (history.length === 0) {
        recentHistoryGrid.innerHTML = `
            <div class="empty-history-tip">
                <i data-lucide="inbox"></i>
                <p>暂无核验记录。在上方输入任意说法即可开始。</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    recentHistoryGrid.innerHTML = history.map(item => {
        const stateInfo = formatOverallState(item.state);
        return `
            <div class="history-card" data-hid="${item.id}">
                <div class="history-card-header">
                    <span class="verdict-state-pill sm ${stateInfo.className}">${stateInfo.label}</span>
                    <span class="history-time">${item.time}</span>
                </div>
                <div class="history-text">${escapeHtml(item.input)}</div>
            </div>
        `;
    }).join("");

    // Click to re-view
    document.querySelectorAll(".history-card").forEach(card => {
        card.addEventListener("click", () => {
            const hid = card.dataset.hid;
            const target = history.find(h => h.id === hid);
            if (target && target.coverage) {
                renderVerificationResult(target.coverage);
                verdictResultSection.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
    });

    lucide.createIcons();
}

function handleCopyVerdict() {
    if (!currentVerificationResult) return;
    const lines = [];
    lines.push(`【AI Claim Verifier 事实核验结论】`);
    lines.push(`待核验说法: "${currentVerificationResult.original_input}"`);
    lines.push(`整体状态: ${formatOverallState(currentVerificationResult.overall_state).label}`);
    lines.push(`---`);
    (currentVerificationResult.claims || []).forEach((c, idx) => {
        const v = (currentVerificationResult.verdicts || [])[idx] || {};
        lines.push(`主张 ${idx+1}: ${c.statement}`);
        lines.push(`判定: ${formatEvidenceState(v.evidence_state).label}`);
        if (v.why_reasons && v.why_reasons.length > 0) {
            lines.push(`依据:\n${v.why_reasons.map(r => `  - ${r}`).join("\n")}`);
        }
        if (v.next_step_advice) {
            lines.push(`核实建议: ${v.next_step_advice}`);
        }
        lines.push(``);
    });

    navigator.clipboard.writeText(lines.join("\n")).then(() => {
        alert("核验结论已成功复制到剪贴板！");
    }).catch(() => {
        alert("复制失败，请手动选择复制。");
    });
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
