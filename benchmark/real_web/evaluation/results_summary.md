# Real-Web E2E Benchmark Evaluation Report

**Evaluation Date**: 2026-08-30  
**Mode**: `CACHED` | **LLM Tier**: `MOCK` | **Total Cases**: `20`

---

## Executive Summary Metrics

| Metric | Score | Target Standard | Status |
| :--- | :---: | :---: | :---: |
| **State Classification Accuracy** | **100.0%** | >= 90.0% | PASS |
| **Overclaim Rate (Safety Invariant)** | **0.0%** | **0.0%** | PERFECT |
| **Conservative Miss Rate** | **0.0%** | <= 10.0% | ACCEPTABLE |
| **True Raw-Text Quote Grounding** | **100.0%** | >= 95.0% | GROUNDED |

---

## 6x6 Confusion Matrix

| Gold \\ Predicted | SUFF | STRG | INSU | CONF | UNSP | N_AS |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`SUFFICIENT`** | 3 | 0 | 0 | 0 | 0 | 0 |
| **`STRONG`** | 0 | 3 | 0 | 0 | 0 | 0 |
| **`INSUFFICIENT`** | 0 | 0 | 4 | 0 | 0 | 0 |
| **`CONFLICTING`** | 0 | 0 | 0 | 4 | 0 | 0 |
| **`UNSUPPORTED`** | 0 | 0 | 0 | 0 | 3 | 0 |
| **`NOT_ASSESSABLE`** | 0 | 0 | 0 | 0 | 0 | 3 |

---

## 🔍 Quote Anchoring Tier Breakdown

- **`EXACT`** (Verbatim character codepoint equality): `28`
- **`NORMALIZED_EXACT`** (Whitespace / Newline / Unicode NFC normalization): `0`
- **`FUZZY`** (Case-insensitive / sliding anchor contextual match): `0`
- **`UNVERIFIED`** (Hallucination rejection, null coordinates): `0`

---

## 📋 Case-by-Case Breakdown

| ID | Domain | Claim | Gold State | Pred State | Match | Quotes |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `rw-01` | Tech/AI | OpenAI launched ChatGPT Plus at a subscription price of $20 per month in February 2023. | `SUFFICIENT` | `SUFFICIENT` | ✅ | `EXACT, EXACT` |
| `rw-02` | Tech/Hardware | Apple Vision Pro is priced starting at $3,499 with 256GB of storage. | `SUFFICIENT` | `SUFFICIENT` | ✅ | `EXACT, EXACT` |
| `rw-03` | Corporate/Finance | Microsoft completed its $68.7 billion acquisition of Activision Blizzard in October 2023. | `SUFFICIENT` | `SUFFICIENT` | ✅ | `EXACT, EXACT` |
| `rw-04` | Tech/Robotics | Unitree Robotics raised nearly 1 billion RMB in Series B2 funding led by Meituan in 2024. | `STRONG` | `STRONG` | ✅ | `EXACT, EXACT` |
| `rw-05` | Tech/AI | DeepSeek-V3 is an open-weights Mixture-of-Experts AI model with 671 billion total parameters. | `STRONG` | `STRONG` | ✅ | `EXACT, EXACT` |
| `rw-06` | Tech/Semiconductor | TSMC began engineering trial production of 4nm chips at its Arizona Fab 21 in 2024. | `STRONG` | `STRONG` | ✅ | `EXACT, EXACT` |
| `rw-07` | Executive Rumor | Apple has completely cancelled all internal development of the M5 chip architecture. | `INSUFFICIENT` | `INSUFFICIENT` | ✅ | `EXACT` |
| `rw-08` | Republishing Chain | AI startup BrainWave was acquired by Amazon for $500 million in cash. | `INSUFFICIENT` | `INSUFFICIENT` | ✅ | `EXACT, EXACT` |
| `rw-09` | Press Release Claim | QuantumNexus achieved room-temperature quantum supremacy with a 10,000-qubit processor. | `INSUFFICIENT` | `INSUFFICIENT` | ✅ | `EXACT` |
| `rw-10` | Gaming Rumor | Nintendo Switch 2 will officially launch at a global retail price of $199. | `INSUFFICIENT` | `INSUFFICIENT` | ✅ | `EXACT` |
| `rw-11` | Corporate/Finance | TechCorp Q3 2024 net income reached $500 million. | `CONFLICTING` | `CONFLICTING` | ✅ | `EXACT, EXACT` |
| `rw-12` | Venture Capital | CleanEnergy Inc raised Series C funding at a post-money valuation of $2.0 billion. | `CONFLICTING` | `CONFLICTING` | ✅ | `EXACT, EXACT` |
| `rw-13` | Biomedical | BioPharma's new oncology drug candidate demonstrated an 85% overall response rate in clinical trials. | `CONFLICTING` | `CONFLICTING` | ✅ | `EXACT, EXACT` |
| `rw-14` | Corporate News | Global Retail Corp CEO confirmed immediate plans to lay off 20% of corporate staff. | `CONFLICTING` | `CONFLICTING` | ✅ | `EXACT, EXACT` |
| `rw-15` | Medical/Regulatory | The FDA officially approved MiracleHerb extract for curing type 2 diabetes. | `UNSUPPORTED` | `UNSUPPORTED` | ✅ | `EXACT` |
| `rw-16` | Executive Rumor | Tesla CEO Elon Musk stepped down from his position as Chief Executive Officer in July 2024. | `UNSUPPORTED` | `UNSUPPORTED` | ✅ | `EXACT` |
| `rw-17` | Corporate Acquisition | Google acquired 100% of AI company Anthropic and integrated it as an internal Alphabet subsidiary. | `UNSUPPORTED` | `UNSUPPORTED` | ✅ | `EXACT` |
| `rw-18` | Private Matters | The Board of Directors of InnovateCo secretly agreed in an executive session to replace the CFO next quarter. | `NOT_ASSESSABLE` | `NOT_ASSESSABLE` | ✅ | `None` |
| `rw-19` | Private Matters | Executive John Doe privately decided to sell his personal real estate portfolio by the end of this year. | `NOT_ASSESSABLE` | `NOT_ASSESSABLE` | ✅ | `None` |
| `rw-20` | Speculative Prediction | Commercial fusion power will account for more than 50% of global electricity generation in the year 2060. | `NOT_ASSESSABLE` | `NOT_ASSESSABLE` | ✅ | `None` |

---

## 🛠️ Failure Taxonomy Analysis

No failure taxonomy issues detected. All cases satisfied expected invariants.
