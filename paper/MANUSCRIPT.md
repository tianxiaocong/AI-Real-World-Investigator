# Grounding Real-World Fact Verification: Deterministic Verdict Rules, True Raw-Text Quote Anchoring, and Cross-Model Empirical Evaluation

**Authors**: AI Real-World Investigator Research Team  
**Date**: August 2026  
**Artifact Repository**: [GitHub: AI-Real-World-Investigator](https://github.com/tianxiaocong/AI-Real-World-Investigator)

---

## Abstract

Automated fact-checking in real-world web environments is fraught with citation hallucinations, source syndication cascades (where republished rumors mimic independent corroboration), and conflicting financial/biomedical reporting. Standard LLM-only verification systems frequently suffer from *overclaiming*—falsely asserting that an unverified, rumor-based, or conflicting claim is definitively verified. 

In this paper, we present **AI Real-World Investigator**, an open-source, deterministic fact-checking architecture that decouples semantic claim extraction from evidentiary verdict determination. Our system introduces three core mechanisms:
1. **True Raw-Text Quote Anchoring**: A character-level, Unicode code-point-accurate physical locator that binds extracted claims to immutable raw HTML document codepoints across four tiered matching strategies (`EXACT`, `NORMALIZED_EXACT`, `FUZZY`, `UNVERIFIED`), immediately rejecting phantom or hallucinated citations.
2. **Structural Provenance Resolution**: An automated graph-attribution engine that detects syndication, republication, and external leak chains (e.g., social media leaks cited across secondary news blogs), preventing echo-chamber overcounting of non-independent sources.
3. **Deterministic Verdict Rules Engine**: A mathematically rigorous, multi-tier state machine defining six mutually exclusive evidentiary states (`SUFFICIENT`, `STRONG`, `INSUFFICIENT`, `CONFLICTING`, `UNSUPPORTED`, `NOT_ASSESSABLE`).

We evaluate the system on a 20-case real-world web benchmark spanning technology, corporate finance, biomedical trials, executive rumors, regulatory denials, and unassessable private matters. Across **40 paired model-case evaluations** using two distinct real-world LLM backends (**SenseNova `sensenova-6.8-flash-lite`** and **DeepSeek `deepseek-v4-flash`**) under identical frozen evidence, the system achieved **85.0%** and **80.0%** classification accuracy, respectively, with **0.0% observed Overclaim Rate (0/40)** and **100.0% physical quote grounding (146/146 verbatim EXACT quotes)**. Under live web execution with anti-scraping WAF obstacles, the architecture demonstrated safe graceful degradation (65.0% resilience accuracy, 0.0% overclaims, with 7 drifted quotes safely rejected as `UNVERIFIED`).

---

## 1. Introduction & Problem Motivation

Large Language Models (LLMs) possess remarkable linguistic comprehension but exhibit critical failure modes when tasked with high-stakes fact verification:
* **Citation Hallucination**: Models frequently generate plausible-sounding quotes or paraphrased statements that do not exist verbatim in the source documents.
* **Syndication Cascades & Echo Chambers**: When a single unverified leak (e.g., an anonymous post) is republished across multiple secondary aggregators (e.g., *"According to [Source X]..."*), naive verification pipelines treat each URL as an independent corroborating witness, artificially inflating evidentiary confidence into false certainty.
* **Overclaim Fragility**: Standard end-to-end generative fact-checkers tend to classify ambiguous, single-source, or subtly conflicting claims as "True", creating unacceptable safety risks in financial, legal, and biomedical intelligence.
* **Dynamic Web Fragility**: Real-world web retrieval suffers from DOM drift, Cloudflare/WAF bot-blocking (HTTP 403/401), and ephemeral content changes.

To resolve these vulnerabilities, we propose an architecture built on the principle of **Evidentiary Grounding and Deterministic Separation**: *LLMs perform semantic extraction and candidate citation identification, while physical text anchoring, provenance attribution, and verdict computation are enforced by deterministic, character-level rule engines.*

```text
[ Raw Web HTML / Snapshot ]
           │
           ▼
[ UTF-8 NFC Normalization & Preservation (raw_text) ]
           │
           ├───────────────────────────────┐
           ▼                               ▼
[ LLM Claim Extractor Agent ]      [ Clean Text Pipeline ]
   • Semantic Fact Extraction
   • Immutable exact_quote
   • Extracted Provenance Meta
           │
           ▼
[ True Raw-Text Quote Locator ] ◄── (Character-level Verification)
   • Tier 1: Verbatim Exact (Codepoint Equality)
   • Tier 2: Normalized Exact (Unicode NFC / Whitespace Token Match)
   • Tier 3: Contextual Sliding Anchor (OCR / Typo Drift)
   • Tier 4: UNVERIFIED (Nullify Coordinates & Reject)
           │
           ▼
[ Provenance & Polarity Graph Engine ]
   • Token/Stem Domain Mapping
   • External Rumor Clustering (ext:<handle>)
   • Origin-based Source De-duplication
           │
           ▼
[ Deterministic 6-State Verdict Rules Engine ]
   • SUFFICIENT | STRONG | INSUFFICIENT | CONFLICTING | UNSUPPORTED | NOT_ASSESSABLE
```

---

## 2. System Architecture & Methods

### 2.1 Canonical Raw-Text Preservation
To prevent destructive loss during HTML sanitization, the ingestion pipeline normalizes HTTP responses to Unicode NFC and bifurcates storage into:
* `raw_text`: The canonical, unmodified raw HTML/text payload used strictly for quote coordinate indexing $[char\_start, char\_end]$.
* `clean_text`: Stripped, readable text provided in the LLM context window.

### 2.2 True Raw-Text Quote Locator (Four-Tier Hierarchy)
Given a source document $S_{raw}$ and an extracted candidate quote $Q$, the locator computes exact character spans and assigns a grounding tier:
1. **Tier 1 (`EXACT`)**: Verbatim substring search where $S_{raw}[start:end] == Q$.
2. **Tier 2 (`NORMALIZED_EXACT`)**: Matches $Q$ to $S_{raw}$ under NFC normalization and whitespace/newline folding, mapping back to precise character boundaries in $S_{raw}$.
3. **Tier 3 (`FUZZY`)**: Employs an $N$-gram sliding anchor search with a similarity threshold $\tau \ge 0.85$ to account for OCR or encoding drift.
4. **Tier 4 (`UNVERIFIED`)**: If no valid alignment is found, the quote coordinates are set to `None`, and the evidence is stripped of admissible status, preventing fabricated quotes from influencing the verdict.

### 2.3 Structural Provenance Resolution
To combat republishing chains, `resolve_textual_provenance` parses extracted attribution metadata (`REPUBLISHES`, `CITES`) through a two-stage algorithm:
* **Intra-Manifest Resolution**: Natural language citations (e.g., *"TechDailyNews and @AILeaker"*) are tokenized into domain stems (`techdailynews`) and mapped to manifest source instances (`s-01` on `techdailynews.org`).
* **External Rumor Clustering**: When sources cite unretrieved third-party entities (e.g., social media handles `@AILeaker`), the resolver generates canonical cluster keys (`ext:aileaker`). Multiple secondary sources citing the same external leak resolve to a single origin node, ensuring the independent source count remains $N=1$.

### 2.4 Deterministic 6-State Verdict Rules Engine
The engine computes an `EvidenceAssessment` and transitions into exactly one evidentiary state:
* **`SUFFICIENT`**: Direct support by at least 1 official source or $\ge 2$ independent mainstream sources.
* **`STRONG`**: Direct support by $\ge 2$ independent high-tier sources without contradictions.
* **`INSUFFICIENT`**: Single-source rumors, syndicated republications (origin count = 1), or unverified press releases.
* **`CONFLICTING`**: Substantive, direct contradictory assertions from credible independent sources (e.g., GAAP vs Non-GAAP net income).
* **`UNSUPPORTED`**: Authoritative, direct denial or refutation (e.g., SEC disclosure or regulatory warning letter).
* **`NOT_ASSESSABLE`**: Non-verifiable private internal deliberations or distant speculative predictions, filtered prior to retrieval.

---

## 3. Experimental Setup & Benchmark Protocol

### 3.1 Benchmark Dataset
We construct a 20-case real-world fact-verification benchmark (`benchmark/real_web/cases.json`) covering 6 domains:
1. **Technology & AI Models** (e.g., ChatGPT Plus pricing, DeepSeek-V3 architecture)
2. **Hardware & Semiconductors** (e.g., Apple Vision Pro specifications, TSMC Fab 21 trial production)
3. **Corporate Finance & M&A** (e.g., Microsoft Activision buyout, TechCorp GAAP earnings)
4. **Biomedical & Clinical Trials** (e.g., Oncology trial response rates)
5. **Rumor Cascades & Denials** (e.g., Amazon BrainWave rumor, Tesla executive resignation rumor)
6. **Pre-Retrieval Boundaries** (e.g., Secret board deliberations, 2060 fusion projections)

### 3.2 Evaluation Matrix & Protocols
The benchmark is evaluated under a controlled $2 \times 2 (+1)$ matrix:
* **Execution Modes**:
  * `CACHED`: Frozen, character-exact HTML snapshots with 0 network variance.
  * `LIVE`: Real-time HTTP fetching with automated fallback isolation upon encountering bot-blocking (HTTP 403/401).
* **Model Backends**:
  1. `Mock`: Deterministic rule-based extractor (upper-bound baseline).
  2. `SenseNova` (`sensenova-6.8-flash-lite`): Commercial large language model.
  3. `DeepSeek` (`deepseek-v4-flash`): Independent reasoning model family.

### 3.3 Metric Definitions
* **State Accuracy**: Proportion of cases where predicted state matches the gold annotation:
  $$\text{Accuracy} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(\hat{y}_i = y_i)$$
* **Overclaim Rate (Safety Metric)**: Proportion of unverified, false, or conflicting claims mistakenly classified as verified (`SUFFICIENT` or `STRONG`):
  $$\text{Overclaim Rate} = \frac{\sum_{i=1}^N \mathbb{I}(y_i \in \{\text{INSU}, \text{CONF}, \text{UNSP}, \text{N\_AS}\} \land \hat{y}_i \in \{\text{SUFF}, \text{STRO}\})}{N}$$
* **Conservative Miss Rate**: Proportion of true claims under-claimed into conservative states.
* **Quote Grounding Rate**: Percentage of model-extracted quotes verified verbatim:
  $$\text{Quote Grounding Rate} = \frac{N_{\text{EXACT}} + N_{\text{NORMALIZED\_EXACT}}}{N_{\text{Total Quotes}}}$$

---

## 4. Empirical Results

### 4.1 Cross-Model Matrix Summary

| Evaluation Setup | Mode | Accuracy | Overclaim Rate | Conservative Miss Rate | Quote Grounding Rate |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Mock Baseline** | `CACHED` | **100.0% (20/20)** | **0.0% (0/20)** | 0.0% | 100.0% (Exact) |
| **Mock Baseline** | `LIVE` | **80.0% (16/20)** | **0.0% (0/20)** | 20.0% | 100.0% (Exact) |
| **SenseNova (`sensenova-6.8-flash-lite`)** | `CACHED` | **85.0% (17/20)** | **0.0% (0/20)** | 15.0% (3/20) | **100.0% (89/89 EXACT)** |
| **SenseNova (`sensenova-6.8-flash-lite`)** | `LIVE` | **65.0% (13/20)** | **0.0% (0/20)** | 35.0% (7/20) | **90.8% (69/76 Grounded)** |
| **DeepSeek (`deepseek-v4-flash`)** | `CACHED` | **80.0% (16/20)** | **0.0% (0/20)** | 20.0% (4/20) | **100.0% (57/57 EXACT)** |

### 4.2 20-Case Paired Comparison (SenseNova vs DeepSeek)

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

| Case ID | Domain / Scenario | Gold State | SenseNova Pred | DeepSeek Pred | Concordance Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `rw-01` | Tech/AI (ChatGPT Plus) | `SUFFICIENT` | `SUFFICIENT` | `SUFFICIENT` | ✅ Shared Pass |
| `rw-02` | Tech/Hardware (Vision Pro Specs) | `SUFFICIENT` | `INSUFFICIENT` | `SUFFICIENT` | 🔀 DeepSeek Only |
| `rw-03` | Finance (Activision Acquisition) | `SUFFICIENT` | `SUFFICIENT` | `SUFFICIENT` | ✅ Shared Pass |
| `rw-04` | Robotics (Unitree B2 Funding) | `STRONG` | `STRONG` | `INSUFFICIENT` | 🔀 SenseNova Only |
| `rw-05` | AI Models (DeepSeek-V3 MoE) | `STRONG` | `STRONG` | `STRONG` | ✅ Shared Pass |
| `rw-06` | Semiconductor (TSMC Fab 21) | `STRONG` | `STRONG` | `STRONG` | ✅ Shared Pass |
| `rw-07` | Rumor (Apple M5 Cancelled) | `INSUFFICIENT` | `INSUFFICIENT` | `INSUFFICIENT` | ✅ Shared Pass |
| `rw-08` | Syndication (BrainWave Buyout) | `INSUFFICIENT` | `INSUFFICIENT` | `INSUFFICIENT` | ✅ Shared Pass |
| `rw-09` | PR Claim (Quantum Supremacy) | `INSUFFICIENT` | `INSUFFICIENT` | `INSUFFICIENT` | ✅ Shared Pass |
| `rw-10` | Gaming Rumor (Switch 2 $199) | `INSUFFICIENT` | `INSUFFICIENT` | `INSUFFICIENT` | ✅ Shared Pass |
| `rw-11` | Finance (TechCorp GAAP Conflict) | `CONFLICTING` | `UNSUPPORTED` | `INSUFFICIENT` | ⚠️ Shared Miss |
| `rw-12` | VC Valuation (CleanEnergy Series C) | `CONFLICTING` | `CONFLICTING` | `CONFLICTING` | ✅ Shared Pass |
| `rw-13` | Biomedical (Drug ORR Conflict) | `CONFLICTING` | `CONFLICTING` | `UNSUPPORTED` | 🔀 SenseNova Only |
| `rw-14` | Corporate (Layoff Rumor Denial) | `CONFLICTING` | `UNSUPPORTED` | `UNSUPPORTED` | ⚠️ Shared Miss |
| `rw-15` | Regulatory (FDA Unapproved Drug) | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | ✅ Shared Pass |
| `rw-16` | Rumor (Tesla CEO Resignation) | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | ✅ Shared Pass |
| `rw-17` | Tech M&A (Google Anthropic Buyout) | `UNSUPPORTED` | `UNSUPPORTED` | `UNSUPPORTED` | ✅ Shared Pass |
| `rw-18` | Private Matters (CFO Replacement) | `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| ✅ Shared Pass |
| `rw-19` | Private Matters (Real Estate Sale) | `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| ✅ Shared Pass |
| `rw-20` | Speculation (Fusion Power 2060) | `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| `NOT_ASSESSABLE`| ✅ Shared Pass |

---

## 5. Failure Analysis & Diagnostic Autopsy

An essential finding of our paired benchmark is that model errors are exclusively **conservative under-claims**, never unsafe overclaims. We analyze the specific failure mechanisms below:

### 5.1 Multi-Attribute Semantic Linking (`rw-02`)
* **Claim**: *"Apple Vision Pro is priced starting at $3,499 with 256GB of storage."*
* **Failure**: SenseNova extracted the pricing ($3,499) and base storage (256GB) as separate clauses across sources without successfully asserting their conjunction in a single supporting evidence structure, leading to a conservative `INSUFFICIENT` verdict.
* **Resolution**: DeepSeek successfully extracted the compound assertion in one unit, passing with `SUFFICIENT`.

### 5.2 Evidence Strength Thresholding (`rw-04`)
* **Claim**: *"Unitree Robotics raised nearly 1 billion RMB in Series B2 funding led by Meituan in 2024."*
* **Failure**: SenseNova extracted direct evidence from both 36Kr and Pandaily (`STRONG`), whereas DeepSeek categorized the Pandaily article as background context rather than direct corroboration, resulting in `INSUFFICIENT`.

### 5.3 Accounting Standard Duality (`rw-11`)
* **Claim**: *"TechCorp Q3 2024 net income reached $500 million."*
* **Gold**: `CONFLICTING` (News reported $500M Non-GAAP net income; official SEC 10-Q filing reported $320M GAAP net income).
* **Failure**: Both LLMs struggled to represent accounting duality as a legitimate evidentiary conflict. SenseNova treated the SEC filing as a direct refutation (`UNSUPPORTED`), while DeepSeek failed to extract sufficient polarity from the financial tables (`INSUFFICIENT`).

### 5.4 Rumor Denial vs Conflict Polarity (`rw-14`)
* **Claim**: *"Global Retail Corp CEO confirmed immediate plans to lay off 20% of corporate staff."*
* **Gold**: `CONFLICTING` (News blog asserted rumors vs corporate press release issued an explicit denial).
* **Failure**: Both models prioritized the authoritative corporate denial and classified the claim as `UNSUPPORTED`. While technically a conservative classification error, in practical intelligence contexts treating an authoritative official denial as an overriding refutation is safe behavior.

---

## 6. Ablation Studies

In Phase 5E, we conducted single-component ablation studies on 20 frozen real-factual web documents to isolate the causal contribution of each architectural layer:

| Experimental Condition | Intervention | Accuracy | Overclaim Rate | Miss Rate | Causal Mechanism |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Control (Full System)** | All components active | **95.0%** | **0.0%** | **0.0%** | Baseline production pipeline |
| **Ablation A** | Disable Provenance Resolution | **90.0%** | **5.0%** 🚨 | **0.0%** | **Syndication cascade**: 3 republished articles treated as independent, triggering Overclaim |
| **Ablation B** | Disable Semantic Polarity Arbitration | **10.0%** 📉 | **0.0%** | **15.0%** | **Paraphrase blindness**: Rigid string matching fails to comprehend paraphrased support |
| **Ablation C** | Disable Dynamic Context Window | **95.0%** | **0.0%** | **5.0%** ⚠️ | **Document truncation**: Salient evidence in long articles truncated by static 16k context window |

---

## 7. Limitations & Threats to Validity

1. **Benchmark Scale**: The benchmark contains 20 curated real-world cases. While rich in structural adversarial traps (provenance syndication, GAAP conflicts, private matters), larger sample sizes are required for fine-grained statistical significance testing.
2. **Web Scraping Fragility**: Fresh live retrieval achieved a 14.3% availability rate due to anti-bot WAF protections on Tier-1 publishers (Bloomberg, Reuters, SEC EDGAR). Production deployment requires residential proxy integration.
3. **Accounting & Specialized Domain Lexicons**: Differentiating legitimate accounting duality (GAAP vs Non-GAAP) from factual contradictions requires domain-specific extraction rules.
4. **Empirical vs Formal Safety**: While zero overclaims were observed across 40 model-case evaluations, this empirical observation does not guarantee zero overclaims under adversarial prompt injection or extreme distribution shifts.

---

## 8. Conclusion

We presented **AI Real-World Investigator**, an open-source verification framework that enforces physical quote anchoring, provenance de-duplication, and deterministic rule evaluation. 

Across 40 paired evaluations on two commercial real LLM backends (SenseNova and DeepSeek-v4-flash), the architecture achieved **0.0% observed Overclaim Rate** and **100.0% physical quote grounding (146/146 verbatim EXACT quotes)**. Model performance differences were confined strictly to higher-order evidence integration and conflict aggregation, validating that the underlying physical grounding and provenance safety mechanisms operate stably across distinct LLM architectures.
