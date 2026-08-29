# Real-Web E2E Benchmark Evaluation Report

**Evaluation Date**: 2026-08-30  
**Execution Mode**: `LIVE` | **LLM Provider**: `MOCK` | **Total Cases**: `20`

> [!NOTE]
> **Live Execution Telemetry**: Real HTTP requests were attempted for 28 web sources. Scraper fresh fetch success rate: **10.7%** (3/28). Pure uncontaminated live cases evaluated: **1**.

---

## Executive Summary Metrics

| Metric | Score | Target Standard | Status |
| :--- | :---: | :---: | :---: |
| **State Classification Accuracy** | **90.0%** | >= 90.0% | PASS |
| **Overclaim Rate (Safety Invariant)** | **0.0%** | **0.0%** | PERFECT |
| **Conservative Miss Rate** | **10.0%** | <= 10.0% | ACCEPTABLE |
| **True Raw-Text Quote Grounding** | **89.3%** | >= 95.0% | WEAK |
| **Live Scraper Retrieval Rate** | **10.7%** | >= 80.0% | BOT_BLOCKED |
| **Pure Live (Uncontaminated) Accuracy** | **0.0%** | >= 85.0% | WARN |

---

## 6x6 Confusion Matrix

| Gold \\ Predicted | SUFF | STRG | INSU | CONF | UNSP | N_AS |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`SUFFICIENT`** | 2 | 0 | 1 | 0 | 0 | 0 |
| **`STRONG`** | 0 | 2 | 1 | 0 | 0 | 0 |
| **`INSUFFICIENT`** | 0 | 0 | 4 | 0 | 0 | 0 |
| **`CONFLICTING`** | 0 | 0 | 0 | 4 | 0 | 0 |
| **`UNSUPPORTED`** | 0 | 0 | 0 | 0 | 3 | 0 |
| **`NOT_ASSESSABLE`** | 0 | 0 | 0 | 0 | 0 | 3 |

---

## 🔍 Quote Anchoring Tier Breakdown

- **`EXACT`** (Verbatim character codepoint equality): `25`
- **`NORMALIZED_EXACT`** (Whitespace / Newline / Unicode NFC normalization): `0`
- **`FUZZY`** (Case-insensitive / sliding anchor contextual match): `0`
- **`UNVERIFIED`** (Hallucination rejection, null coordinates): `3`

---

## 📋 Case-by-Case Breakdown

| ID | Domain | Claim | Gold State | Pred State | Match | Quotes |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| `rw-01` | Tech/AI | OpenAI launched ChatGPT Plus at a subscription price of $20 per month in February 2023. | `SUFFICIENT` | `SUFFICIENT` | ✅ | `EXACT, EXACT` |
| `rw-02` | Tech/Hardware | Apple Vision Pro is priced starting at $3,499 with 256GB of storage. | `SUFFICIENT` | `INSUFFICIENT` | ❌ | `UNVERIFIED, EXACT` |
| `rw-03` | Corporate/Finance | Microsoft completed its $68.7 billion acquisition of Activision Blizzard in October 2023. | `SUFFICIENT` | `SUFFICIENT` | ✅ | `EXACT, EXACT` |
| `rw-04` | Tech/Robotics | Unitree Robotics raised nearly 1 billion RMB in Series B2 funding led by Meituan in 2024. | `STRONG` | `STRONG` | ✅ | `EXACT, EXACT` |
| `rw-05` | Tech/AI | DeepSeek-V3 is an open-weights Mixture-of-Experts AI model with 671 billion total parameters. | `STRONG` | `INSUFFICIENT` | ❌ | `UNVERIFIED, UNVERIFIED` |
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

### SCRAPER_BLOCKED_FALLBACK (25 cases)
- rw-01/s-01 (https://openai.com/index/chatgpt-plus/)
- rw-01/s-02 (https://www.reuters.com/technology/openai-launches-chatgpt-plus-subscription-20-month-2023-02-01/)
- rw-02/s-02 (https://www.theverge.com/2024/1/8/24029802/apple-vision-pro-release-date-price)
- rw-03/s-01 (https://www.sec.gov/Archives/edgar/data/789019/000119312523255788/d568435d8k.htm)
- rw-03/s-02 (https://blogs.microsoft.com/blog/2023/10/13/welcoming-the-legendary-teams-at-activision-blizzard-king-to-team-xbox/)
- rw-04/s-01 (https://36kr.com/p/2659821734912)
- rw-04/s-02 (https://pandaily.com/unitree-robotics-secures-nearly-1b-yuan-in-series-b2-financing/)
- rw-06/s-01 (https://www.bloomberg.com/news/articles/2024-04-18/tsmc-arizona-chip-trial-production-advanced-packaging)
- rw-06/s-02 (https://www.digitimes.com/news/a20240419PD203.html)
- rw-07/s-01 (https://reddit.com/r/appleleaks/comments/m5_cancelled_rumor)
- rw-08/s-01 (https://techdailynews.org/amazon-brainwave-acquisition)
- rw-08/s-02 (https://siliconvalleyinsider.blog/amazon-buys-brainwave)
- rw-09/s-01 (https://www.pr-newswire-hub.com/quantumnexus-breakthrough-2025)
- rw-10/s-01 (https://gamingrumorsforum.net/switch-2-199-price)
- rw-11/s-01 (https://financialtimes.example/techcorp-q3-non-gaap)
- rw-11/s-02 (https://secfilings.example/techcorp-10q-q3)
- rw-12/s-01 (https://venturebeat.example/cleanenergy-2b-valuation)
- rw-12/s-02 (https://techcrunch.example/cleanenergy-series-c-1-2b)
- rw-13/s-01 (https://mednews.example/biopharma-trial-85-percent)
- rw-13/s-02 (https://clinicaltrials.example/biopharma-full-results)
- rw-14/s-01 (https://businessjournal.example/retail-corp-layoffs)
- rw-14/s-02 (https://globalretailcorp.example/press/statement-on-layoff-rumors)
- rw-15/s-01 (https://www.fda.gov/warning-letters/miracleherb-unapproved-drug)
- rw-16/s-01 (https://www.sec.gov/edgar/data/1318605/tesla-q2-2024-10q)
- rw-17/s-01 (https://www.ft.com/content/google-anthropic-investment-structure)
### CONSERVATIVE_MISS (2 cases)
- rw-02 (Gold: SUFFICIENT -> Pred: INSUFFICIENT)
- rw-05 (Gold: STRONG -> Pred: INSUFFICIENT)
