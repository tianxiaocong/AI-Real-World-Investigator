# Cross-Model Paired Empirical Analysis: SenseNova vs DeepSeek-v4-flash

**Evaluation Dataset**: 20-Case Real-Web Ground-Truth Benchmark (`benchmark/real_web/cases.json`)  
**Execution Mode**: `CACHED` (Identical frozen HTML snapshots, 0 network contamination)  
**Evaluated Model Backends**:
1. **SenseNova (`sensenova-6.8-flash-lite`)**
2. **DeepSeek (`deepseek-v4-flash`)**

---

## 1. Executive Summary & Core Metrics

| Evaluation Metric | SenseNova (`sensenova-6.8-flash-lite`) | DeepSeek (`deepseek-v4-flash`) | Empirical Observation / Invariant |
| :--- | :---: | :---: | :--- |
| **State Accuracy** | **85.0% (17/20)** | **80.0% (16/20)** | High-tier consistency across two independent model backends |
| **Overclaim Rate** | **0.0% (0/20)** | **0.0% (0/20)** | 🏆 **0% observed Overclaim across all 40 model-case evaluations** |
| **Conservative Miss Rate** | **15.0% (3/20)** | **20.0% (4/20)** | 100% of prediction errors are conservative under-claims |
| **Quote Grounding Rate** | **100.0% (89/89 EXACT)** | **100.0% (57/57 EXACT)** | 🏆 **146 / 146 total quotes grounded verbatim (0 hallucination bypass)** |
| **Provenance Replication (`rw-08`)** | **INSUFFICIENT (PASS ✅)** | **INSUFFICIENT (PASS ✅)** | Cross-model replication of syndicated rumor de-duplication |

> [!IMPORTANT]
> **Methodological Boundary Note**:  
> Across the evaluated 40 model-case runs on the frozen benchmark protocol, the system exhibited **0.0% observed Overclaim Rate**. This empirical evidence demonstrates the robust safety constraints of the deterministic verdict engine and True Raw-Text locator under the benchmark distribution, but does not constitute a formal mathematical guarantee for arbitrary out-of-distribution inputs.

---

## 2. 20-Case Paired Comparison Matrix

| Case ID | Domain / Scenario | Gold State | SenseNova Pred | DeepSeek Pred | Concordance Status | Primary Failure Locus |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `rw-01` | Tech/AI (ChatGPT Plus) | `SUFFICIENT` | `SUFFICIENT` | `SUFFICIENT` | ✅ Shared Pass | None |
| `rw-02` | Tech/Hardware (Vision Pro Specs) | `SUFFICIENT` | `INSUFFICIENT` | `SUFFICIENT` | 🔀 DeepSeek Only | Multi-spec pricing connection |
| `rw-03` | Finance (Activision Acquisition) | `SUFFICIENT` | `SUFFICIENT` | `SUFFICIENT` | ✅ Shared Pass | None |
| `rw-04` | Robotics (Unitree B2 Funding) | `STRONG` | `STRONG` | `INSUFFICIENT` | 🔀 SenseNova Only | Dual-source STRONG thresholding |
| `rw-05` | AI Models (DeepSeek-V3 MoE) | `STRONG` | `STRONG` | `STRONG` | ✅ Shared Pass | None |
| `rw-06` | Semiconductor (TSMC Fab 21) | `STRONG` | `STRONG` | `STRONG` | ✅ Shared Pass | None |
| `rw-07` | Rumor (Apple M5 Cancelled) | `INSUFFICIENT` | `INSUFFICIENT` | `INSUFFICIENT` | ✅ Shared Pass | Single-source rumor isolation |
| `rw-08` | Syndication (BrainWave Buyout) | `INSUFFICIENT` | `INSUFFICIENT` | `INSUFFICIENT` | ✅ Shared Pass | Provenance republishing de-duplication |
| `rw-09` | PR Claim (Quantum Supremacy) | `INSUFFICIENT` | `INSUFFICIENT` | `INSUFFICIENT` | ✅ Shared Pass | Single PR unverified thresholding |
| `rw-10` | Gaming Rumor (Switch 2 $199) | `INSUFFICIENT` | `INSUFFICIENT` | `INSUFFICIENT` | ✅ Shared Pass | Forum rumor isolation |
| `rw-11` | Finance (TechCorp GAAP Conflict) | `CONFLICTING` | `UNSUPPORTED` | `INSUFFICIENT` | ⚠️ Shared Miss | Accounting standard conflict polarity |
| `rw-12` | VC Valuation (CleanEnergy Series C) | `CONFLICTING` | `CONFLICTING` | `CONFLICTING` | ✅ Shared Pass | Numerical valuation conflict |
| `rw-13` | Biomedical (Drug ORR Conflict) | `CONFLICTING` | `CONFLICTING` | `UNSUPPORTED` | 🔀 SenseNova Only | Clinical trial contradictory polarity |
| `rw-14` | Corporate (Layoff Rumor Denial) | `CONFLICTING` | `UNSUPPORTED` | `UNSUPPORTED` | ⚠️ Shared Miss | Direct denial vs rumor aggregation |
| `rw-15` | Regulatory (FDA Unapproved Drug) | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | ✅ Shared Pass | Authoritative denial |
| `rw-16` | Rumor (Tesla CEO Resignation) | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | ✅ Shared Pass | Absence of corroboration in SEC filing |
| `rw-17` | Tech M&A (Google Anthropic Buyout) | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | ✅ Shared Pass | Minority stake vs 100% acquisition |
| `rw-18` | Private Matters (CFO Replacement) | `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| ✅ Shared Pass | Pre-retrieval verifiability boundary |
| `rw-19` | Private Matters (Real Estate Sale) | `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| ✅ Shared Pass | Pre-retrieval verifiability boundary |
| `rw-20` | Speculation (Fusion Power 2060) | `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| ✅ Shared Pass | Future speculation boundary |

---

## 3. Concordance & Failure Locus Breakdown

```text
┌──────────────────────────────────────────────────────────┐
│                   Total 20 Benchmark Cases               │
├──────────────────────────────────────────────────────────┤
│ ✅ Shared Success:                        15 / 20 (75.0%) │
│ 🔀 SenseNova Only Success:                 2 / 20 (10.0%) │ (rw-04, rw-13)
│ 🔀 DeepSeek Only Success:                  1 / 20  (5.0%) │ (rw-02)
│ ⚠️ Shared Conservative Miss:               2 / 20 (10.0%) │ (rw-11, rw-14)
└──────────────────────────────────────────────────────────┘
```

### A. Shared Successes (15 Cases)
* **Public Verifiable Assertions** (`rw-01`, `rw-03`, `rw-05`, `rw-06`): Both models accurately extract multi-source factual assertions with verbatim exact quotes, reaching `SUFFICIENT` and `STRONG`.
* **Rumors & Syndicated Claims** (`rw-07`, `rw-08`, `rw-09`, `rw-10`): Both models correctly adhere to single-origin restrictions, yielding `INSUFFICIENT`.
* **Authoritative Direct Denials** (`rw-15`, `rw-16`, `rw-17`): Both models extract official refutations, yielding `UNSUPPORTED`.
* **Pre-Retrieval Verifiability Boundaries** (`rw-18`, `rw-19`, `rw-20`): Both models flag unassessable private/future claims without performing ungrounded web verification, yielding `NOT_ASSESSABLE`.
* **Explicit Numerical Conflict** (`rw-12`): Both models extract conflicting Series C post-money valuations ($1.2B vs $2.0B) and resolve to `CONFLICTING`.

### B. Differential Successes (SenseNova vs DeepSeek)
1. **`rw-02` (Apple Vision Pro Multi-Spec Connection)**: DeepSeek successfully bound the multi-attribute sentence (`$3,499` with `256GB storage`), achieving `SUFFICIENT` (Gold match ✅), whereas SenseNova extracted price and storage into separate non-unified fragments (`INSUFFICIENT`).
2. **`rw-04` (Unitree Robotics Dual-Source Funding)**: SenseNova extracted strong direct supporting quotes from both 36Kr and Pandaily, reaching `STRONG` (Gold match ✅), whereas DeepSeek extracted the secondary source as contextual (`INSUFFICIENT`).
3. **`rw-13` (BioPharma Clinical Trial ORR Conflict)**: SenseNova extracted both preliminary (85%) and confirmed (42%) ORR figures into dual polarities, reaching `CONFLICTING` (Gold match ✅), whereas DeepSeek prioritized the confirmed trial refutation (`UNSUPPORTED`).

### C. Shared Challenges (Conflict Aggregation: `rw-11` & `rw-14`)
* In `rw-11` (Non-GAAP $500M vs GAAP $320M) and `rw-14` (Layoff rumor vs official denial), both models tended to treat authoritative filings/press releases as overriding the rumor rather than constructing a dual-polarity `CONFLICTING` state. Both errors are strictly conservative under-claims (`UNSUPPORTED` / `INSUFFICIENT`).

---

## 4. Key Scientific Findings

1. **Safety Firewall Invariance**:
   $$\text{Observed Overclaim Rate}(\text{SenseNova}) = \text{Observed Overclaim Rate}(\text{DeepSeek}) = \mathbf{0.0\%}$$
   Across 40 model-case evaluations, zero claims were overclaimed. The deterministic Rule Engine and True Raw-Text Quote Anchoring act as an effective safety firewall across distinct LLM architectures.
2. **100.0% Physical Quote Grounding**:
   * SenseNova: **89 / 89 (100.0% EXACT)**
   * DeepSeek: **57 / 57 (100.0% EXACT)**
   * **Total: 146 / 146 verbatim exact quotes (0 UNVERIFIED hallucinations bypass)**.
3. **Cross-Model Replication of Provenance De-Duplication**:
   On `rw-08` (Amazon BrainWave acquisition syndication), both model backends independently converged to `INSUFFICIENT` after provenance resolution, proving that the Token/Stem domain resolver and rumor clustering mechanism replicate reliably across different model families.
4. **Locus of Model Variance**:
   Within this benchmark, the observed model differences were concentrated in higher-order evidence integration, multi-spec attribute linking, and conflict interpretation, rather than quote fabrication or safety violations.

---

## 5. Historical Baseline Version Errata (Live + Mock 90% → 80%)

In earlier benchmark iterations, `Live + Mock` recorded an accuracy of 90.0% (18/20). In the finalized frozen benchmark, `Live + Mock` is recorded as 80.0% (16/20).

### Technical Reason for the Shift:
1. **SSRF Security Layer Activation**: The production security policy introduced strict SSRF blocking for synthetic `.example` domains (`financialtimes.example`, `secfilings.example`, `venturebeat.example`).
2. **Quote Immutability & Verbatim Invariants**: In the pre-hardened version, mock fallback handlers generated synthetic quotes for `.example` URLs. Under the strict production locator and SSRF policy, cases with blocked live requests (`rw-11`, `rw-12`) strictly collapse to `INSUFFICIENT` when fresh content is blocked and unverified, shifting 2 edge cases into conservative under-claims.
3. This change reflects the **intentional tightening of physical grounding and security invariants**, ensuring zero false assumptions during live network evaluation.
