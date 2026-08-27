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

        const card = document.createElement("div");
        card.className = "verdict-card";

        // Why reasons list
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

        // Gaps
        const gaps = verdict.evidence_gaps || [];
        const gapsHtml = gaps.length > 0 ? `
            <div class="evidence-gaps-block">
                <div class="block-label"><i data-lucide="alert-circle"></i> 关键证据缺口</div>
                <div class="gaps-list">
                    ${gaps.map(g => `<div class="gap-item">⚠ ${escapeHtml(g)}</div>`).join("")}
                </div>
            </div>
        ` : "";

        // Next steps
        const adviceHtml = verdict.next_step_advice ? `
            <div class="advice-block">
                <div class="block-label"><i data-lucide="compass"></i> 下一步核实建议</div>
                <div class="advice-text">${escapeHtml(verdict.next_step_advice)}</div>
            </div>
        ` : "";

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

            <div class="verdict-reasons-block">
                <div class="block-label"><i data-lucide="check-square"></i> 为什么这样判断？(核验依据)</div>
                <div class="why-reasons-list">
                    ${reasonsHtml || '<div class="why-text">暂无详细判定理由</div>'}
                </div>
            </div>

            ${gapsHtml}
            ${adviceHtml}
        `;

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
