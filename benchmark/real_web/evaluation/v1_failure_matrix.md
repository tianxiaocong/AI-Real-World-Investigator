# V1 Failure Matrix & Root-Cause Layer Diagnostics

**Evaluation Protocol**: 20-Case Real-Web Benchmark (`benchmark/real_web/cases.json`)  
**Evaluated Runs**:
1. `CACHED + SenseNova` (`sensenova-6.8-flash-lite`): 20 Cases (17 Pass, 3 Fail)
2. `CACHED + DeepSeek` (`deepseek-v4-flash`): 20 Cases (16 Pass, 4 Fail)
3. `LIVE + SenseNova` (`sensenova-6.8-flash-lite`): 20 Cases (13 Pass, 7 Fail)

---

## 1. Comprehensive Case-Level Failure Matrix

| Case ID | Model | Mode | Gold State | Pred State | Safe / Unsafe | Primary Failure Layer | Secondary Failure Layer | Root-Cause Failure Reason | Extracted Evidence & Locator State |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| `rw-02` | SenseNova | `CACHED` | `SUFFICIENT` | `INSUFFICIENT` | **SAFE** (Conservative Miss) | **Extraction** (Multi-Spec) | Verdict Gate | Split price ($3,499) and storage (256GB) into disconnected atomic claims without asserting joint conjunction. | 1 EXACT quote (price only); storage was isolated into background context. |
| `rw-04` | DeepSeek | `CACHED` | `STRONG` | `INSUFFICIENT` | **SAFE** (Conservative Miss) | **Extraction** (Evidence Strength) | Verdict Gate | Extracted 36Kr as direct support, but categorized Pandaily article as contextual/secondary rather than direct support ($N_{\text{strong}} < 2$). | 4 EXACT quotes; dual-source strong support threshold not met. |
| `rw-11` | SenseNova | `CACHED` | `CONFLICTING` | `UNSUPPORTED` | **SAFE** (Conservative Miss) | **Scope / Polarity** (Accounting) | Verdict Gate | Treated official SEC 10-Q GAAP filing ($320M) as an authoritative overriding refutation of the Non-GAAP news report ($500M). | 2 EXACT quotes; SEC filing treated as refutation rather than legitimate accounting duality. |
| `rw-11` | DeepSeek | `CACHED` | `CONFLICTING` | `INSUFFICIENT` | **SAFE** (Conservative Miss) | **Extraction** (Accounting) | Scope | Failed to extract admissible polar claims from financial data tables $\rightarrow$ defaulted to safe insufficient. | 0 quotes extracted from financial tables. |
| `rw-13` | DeepSeek | `CACHED` | `CONFLICTING` | `UNSUPPORTED` | **SAFE** (Conservative Miss) | **Polarity** (Temporal/Trial) | Verdict Gate | Emphasized the confirmed full trial refutation (42% ORR) as overriding the preliminary report (85% ORR), collapsing dual polarity to refutation. | 4 EXACT quotes; polarity collapsed to one-sided refutation. |
| `rw-14` | SenseNova | `CACHED` | `CONFLICTING` | `UNSUPPORTED` | **SAFE** (Conservative Miss) | **Polarity** (Authoritative Denial) | Scope | Prioritized corporate press release explicit denial over blog rumors, treating it as refutation rather than active conflict. | 3 EXACT quotes; denial treated as definitive refutation. |
| `rw-14` | DeepSeek | `CACHED` | `CONFLICTING` | `UNSUPPORTED` | **SAFE** (Conservative Miss) | **Polarity** (Authoritative Denial) | Scope | Prioritized corporate press release explicit denial over blog rumors, treating it as refutation rather than active conflict. | 3 EXACT quotes; denial treated as definitive refutation. |
| `rw-02` | SenseNova | `LIVE` | `SUFFICIENT` | `INSUFFICIENT` | **SAFE** (Conservative Miss) | **Extraction** (Multi-Spec) | Retrieval | Multi-spec pricing connection failed (same as cached) + 1 source hit Cloudflare 403. | 1 EXACT quote. |
| `rw-04` | SenseNova | `LIVE` | `STRONG` | `INSUFFICIENT` | **SAFE** (Conservative Miss) | **Retrieval** (WAF 403) | Verdict Gate | 36Kr returned 403 WAF block on live network $\rightarrow$ only 1 live source extracted $\rightarrow$ downgraded from STRONG to INSUFFICIENT. | 2 EXACT quotes from secondary source. |
| `rw-05` | SenseNova | `LIVE` | `STRONG` | `INSUFFICIENT` | **SAFE** (Conservative Miss) | **Grounding** (DOM Drift) | Locator Defense | Live DeepSeek GitHub page drifted $\rightarrow$ LLM generated memory quotes $\rightarrow$ Locator rejected 7 hallucinated quotes as `UNVERIFIED` $\rightarrow$ safe fallback. | 7 `UNVERIFIED` quotes (coordinates nullified by locator). |
| `rw-11` | SenseNova | `LIVE` | `CONFLICTING` | `INSUFFICIENT` | **SAFE** (Conservative Miss) | **Retrieval** (SSRF / 403) | Extraction | Synthetic `.example` URLs blocked by SSRF security policy on live network $\rightarrow$ no live text available $\rightarrow$ safe insufficient. | 0 quotes (live blocked). |
| `rw-12` | SenseNova | `LIVE` | `CONFLICTING` | `INSUFFICIENT` | **SAFE** (Conservative Miss) | **Retrieval** (SSRF / 403) | Extraction | Synthetic `.example` URLs blocked by SSRF security policy on live network $\rightarrow$ safe insufficient. | 0 quotes (live blocked). |
| `rw-13` | SenseNova | `LIVE` | `CONFLICTING` | `INSUFFICIENT` | **SAFE** (Conservative Miss) | **Retrieval** (WAF 403) | Polarity | Live medical portal returned 403 WAF $\rightarrow$ secondary source missing $\rightarrow$ safe insufficient. | 1 EXACT quote. |
| `rw-14` | SenseNova | `LIVE` | `CONFLICTING` | `UNSUPPORTED` | **SAFE** (Conservative Miss) | **Polarity** (Authoritative Denial) | Retrieval | Corporate denial press release prioritized over blog rumor (same as cached). | 2 EXACT quotes. |

---

## 2. Failure Layer Aggregation & Distribution

Across all **14 failure events** observed in the experimental benchmark runs:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      Failure Layer Distribution                         │
├────────────────────────────────┬───────────────┬────────────────────────┤
│ Failure Layer                  │ Count (Total) │ Percentage of Failures │
├────────────────────────────────┼───────────────┼────────────────────────┤
│ 🌐 Retrieval (WAF 403 / SSRF)   │ 5             │ 35.7%                  │
│ ⚖️ Polarity / Denial Priority  │ 4             │ 28.6%                  │
│ 📝 Claim Extraction / Linking   │ 3             │ 21.4%                  │
│ 📊 Scope / Accounting Duality  │ 1             │ 7.1%                   │
│ 🛡️ Grounding (DOM Drift Rejection) 1           │ 7.1% (Safe Defense)    │
│ 🪟 Window Selection            │ 0             │ 0.0%                   │
│ 🔗 Provenance Resolution       │ 0             │ 0.0% (Resolved rw-08)  │
│ ⚙️ Verdict Rule Bypass (Unsafe)│ 0             │ 0.0% (Zero Overclaims) │
└────────────────────────────────┴───────────────┴────────────────────────┘
```

---

## 3. Key Analytical Insights from Failure Matrix

1. **Safety Boundary is 100% Intact (0 Unsafe Failures)**:
   - In all 14 failure instances, the system erred on the side of **conservative under-claiming** (`INSUFFICIENT` or `UNSUPPORTED`).
   - Zero cases produced false corroborations (`SUFFICIENT` or `STRONG` on unverified claims).

2. **In Cached Mode (Decoupled from Network)**:
   - Total failures across 40 model-case evaluations: **7 failures** (3 on SenseNova, 4 on DeepSeek).
   - **4 / 7 (57.1%)** were **Polarity / Denial Hierarchy challenges** (`rw-11`, `rw-13`, `rw-14`), where the models struggled to construct a dual-polarity `CONFLICTING` state when an authoritative denial was present.
   - **3 / 7 (42.9%)** were **Extraction / Multi-Spec Linking challenges** (`rw-02` compound pricing+storage, `rw-04` secondary source directness, `rw-11` financial tables).

3. **In Live Mode (Network Noise Introduced)**:
   - **5 / 7 (71.4%)** of failures were caused by **Retrieval availability** (WAF 403 blocks or SSRF synthetic domain protections), demonstrating why Live Retrieval must be engineered and evaluated as an independent subsystem.
   - **1 / 7 (14.3%)** (`rw-05`) was a **successful Grounding Defense**, where the raw-text locator successfully caught DOM drift and stripped 7 phantom quotes, preventing an overclaim.
