# Real-Web E2E Benchmark Dataset Specification (20 Cases)

## Overview
The **Real-Web E2E Benchmark** evaluates the complete AI Real-World Investigator pipeline:
$$\text{Search / Fetch} \longrightarrow \text{Scraper} \longrightarrow \text{Claim Extraction} \longrightarrow \text{Exact Quote Grounding} \longrightarrow \text{Provenance Resolution} \longrightarrow \text{Deterministic Verdict Engine}$$

This benchmark tests real-world web environments with diverse domains, including technical disclosures, corporate financial filings, biomedical endpoints, syndication chains, anonymous rumors, and private unassessable claims.

---

## Benchmark Composition & Distribution

| EvidenceState | Count | Target Claim Focus | Primary Domains |
| :--- | :---: | :--- | :--- |
| **`SUFFICIENT`** | 3 | High-profile official announcements corroborated by Tier-1 media | Tech / AI, Hardware, Corporate Acquisition |
| **`STRONG`** | 3 | Multiple independent authoritative newsrooms without official statement | Robotics, Open-Weights AI, Semiconductor Mfg |
| **`INSUFFICIENT`** | 4 | Single-source leaks, syndication networks, PR Newswire, gaming rumors | Social Media, Republishing Networks, Rumors |
| **`CONFLICTING`** | 4 | Non-GAAP vs GAAP, conflicting valuations, subgroup trial discrepancies | Corporate Finance, VC, Biomedical, Layoff Rumors |
| **`UNSUPPORTED`** | 3 | Official regulatory warning letters, SEC filings denying rumors | Medical Fraud, Executive Rumor, M&A Rumors |
| **`NOT_ASSESSABLE`** | 3 | Confidential board discussions, private intents, speculative 2060 predictions | Private Matters, Speculative Long-Term |
| **Total** | **20** | **Comprehensive Real-World Distribution** | **6 Multi-Disciplinary Sectors** |

---

## Detailed Case Catalog

### 1. `SUFFICIENT` (Official + Independent Corroboration)
- **`rw-01`**: *OpenAI launched ChatGPT Plus at a subscription price of $20 per month in February 2023.*
  - Sources: OpenAI Official Press Release (`OFFICIAL`), Reuters Report (`PRIMARY_MEDIA`).
- **`rw-02`**: *Apple Vision Pro is priced starting at $3,499 with 256GB of storage.*
  - Sources: Apple Newsroom (`OFFICIAL`), The Verge Launch Coverage (`SECONDARY_MEDIA`).
- **`rw-03`**: *Microsoft completed its $68.7 billion acquisition of Activision Blizzard in October 2023.*
  - Sources: US SEC Form 8-K (`GOVERNMENT`), Microsoft Official Corporate Blog (`OFFICIAL`).

### 2. `STRONG` (Multiple Independent Media / Authoritative Repositories)
- **`rw-04`**: *Unitree Robotics raised nearly 1 billion RMB in Series B2 funding led by Meituan in 2024.*
  - Sources: 36Kr Exclusive Report (`PRIMARY_MEDIA`), Pandaily Global Coverage (`SECONDARY_MEDIA`).
- **`rw-05`**: *DeepSeek-V3 is an open-weights Mixture-of-Experts AI model with 671 billion total parameters.*
  - Sources: GitHub Official Weights Repo (`PRIMARY_MEDIA`), Hugging Face Model Card (`AUTHORITATIVE`).
- **`rw-06`**: *TSMC began engineering trial production of 4nm chips at its Arizona Fab 21 in 2024.*
  - Sources: Bloomberg Reporting (`PRIMARY_MEDIA`), DigiTimes Semiconductor Intelligence (`SECONDARY_MEDIA`).

### 3. `INSUFFICIENT` (Single Source / Republishing Amplification / Unverified)
- **`rw-07`**: *Apple has completely cancelled all internal development of the M5 chip architecture.*
  - Sources: Single Reddit thread (`FORUM`).
- **`rw-08`**: *AI startup BrainWave was acquired by Amazon for $500 million in cash.*
  - Sources: 2 blogs citing a single Twitter rumor (`AGGREGATOR`, `BLOG`). Tests provenance deduplication.
- **`rw-09`**: *QuantumNexus achieved room-temperature quantum supremacy with a 10,000-qubit processor.*
  - Sources: Single unreviewed self-published vendor press release (`BLOG`).
- **`rw-10`**: *Nintendo Switch 2 will officially launch at a global retail price of $199.*
  - Sources: Gaming rumor forum (`FORUM`).

### 4. `CONFLICTING` (Genuine Factual or Scope Contradictions)
- **`rw-11`**: *TechCorp Q3 2024 net income reached $500 million.*
  - Sources: Media Non-GAAP adjusted metric ($500M) vs SEC 10-Q GAAP metric ($320M).
- **`rw-12`**: *CleanEnergy Inc raised Series C funding at a post-money valuation of $2.0 billion.*
  - Sources: VentureBeat ($2.0B) vs TechCrunch ($1.2B).
- **`rw-13`**: *BioPharma's new oncology drug candidate demonstrated an 85% overall response rate in clinical trials.*
  - Sources: Subgroup analysis (85%) vs Intention-to-treat full cohort (45%).
- **`rw-14`**: *Global Retail Corp CEO confirmed immediate plans to lay off 20% of corporate staff.*
  - Sources: Executive interview vs Official company spokesperson denial.

### 5. `UNSUPPORTED` (Authoritative Contradiction / Formal Denial)
- **`rw-15`**: *The FDA officially approved MiracleHerb extract for curing type 2 diabetes.*
  - Sources: FDA Official Warning Letter rejecting approval and finding fraudulent marketing (`GOVERNMENT`).
- **`rw-16`**: *Tesla CEO Elon Musk stepped down from his position as Chief Executive Officer in July 2024.*
  - Sources: SEC Form 10-Q confirming continued tenure (`GOVERNMENT`).
- **`rw-17`**: *Google acquired 100% of AI company Anthropic and integrated it as an internal Alphabet subsidiary.*
  - Sources: Financial Times confirming non-voting minority stake structure (`PRIMARY_MEDIA`).

### 6. `NOT_ASSESSABLE` (Non-Verifiable Private Matters & Future Speculation)
- **`rw-18`**: *The Board of Directors of InnovateCo secretly agreed in an executive session to replace the CFO next quarter.*
  - Sources: Zero public disclosures (Confidential internal board matter).
- **`rw-19`**: *Executive John Doe privately decided to sell his personal real estate portfolio by the end of this year.*
  - Sources: Zero public registry filings (Private individual intention).
- **`rw-20`**: *Commercial fusion power will account for more than 50% of global electricity generation in the year 2060.*
  - Sources: Zero empirical data (Speculative long-term forecast).

---

## Execution Modes
1. **`--cached` (Deterministic Replay)**:
   Loads canonical `content.html` snapshots from `sources/rw-XX/` directly into the parser and verification service, bypassing network variability.
2. **`--live` (Live Web Scraping)**:
   Directly issues live HTTP requests via `WebScraper.fetch_and_extract` against real URLs with user-agent rotation and rate-limit handling.
