# Phase 5D: Real-World Factual E2E Benchmark Dataset Specification (DATASET_SPEC v1.1 Frozen)

> **版本**：v1.1 (Gold Oracle Independence & Strict Unicode Offset Fix)  
> **设计目标**：建立端到端无污染、严格可解释、真实网页事实核验黄金基准（Real-Web Factual E2E Benchmark）。  
> **核心原则**：
> 1. **真实事实与未篡改 DOM**：所有信源直接抓取自公网真实网页，严禁任何人工修改、文本注入或合成 HTML。
> 2. **独立 Gold 裁判准则 (Gold Oracle Independence)**：`gold_state` 必须由独立人工双审裁定冻结，严禁由被测系统的 `verdict_rules.py` 单向生成（规则引擎仅作为一致性交叉校验）。
> 3. **严格 Unicode NFC 物理坐标系**：定义 `content.html -> raw_text.txt` 规范化管道（NFC 编码 + `\n` 换行统一），以 Python Unicode Code-Point 0-indexed 为唯一数学偏移基准。
> 4. **生产架构单核直连**：评测 Runner 统一调用生产级 `VerificationService`，不重新实现或绕过生产链路。

---

## 1. 目录规范与文件组织 (Directory Structure)

```text
benchmark/real_factual/
├── DATASET_SPEC.md              # 本规范说明书 (v1.1 Frozen)
├── DATASET_CARD.md              # 数据集卡片 (样本分布、领域、发布时间跨度统计)
├── claims.jsonl                 # 20 个原子测试主张 (p5d-01 ~ p5d-20)
├── manifest.json                # 全量快照哈希 (content_hash + raw_text_hash) 与依赖清单
├── sources/                     # 真实网页冻结快照层 (原始数据，严禁包含 Gold)
│   ├── p5d-01/
│   │   ├── s-01/
│   │   │   ├── content.html     # 原始网页纯 HTML 快照 (未修改)
│   │   │   ├── raw_text.txt     # 确定性解构正文 (Unicode NFC + \n 统一)
│   │   │   └── metadata.json    # URL、发布时间、双哈希、抓取状态
│   │   └── s-02/
│   │       ├── content.html
│   │       ├── raw_text.txt
│   │       └── metadata.json
│   ├── p5d-02/
│   └── ... (p5d-01 ~ p5d-20)
├── evaluation/                  # 细粒度黄金标注层 (评测 Runner 仅在预测完成后读取)
│   ├── p5d-01/
│   │   └── gold.json
│   ├── p5d-02/
│   │   └── gold.json
│   └── ... (p5d-01 ~ p5d-20)
├── service/
│   └── verification_service.py  # 生产级通用核验服务 (API/Orchestrator/Benchmark 共享核心)
└── run_real_factual_benchmark.py # 生产主链路 E2E 评测执行器
```

---

## 2. 物理坐标系与 EXACT 规范 (Deterministic EXACT Representation)

为彻底杜绝 HTML 标签污染、换行符差异及多字节字符偏移歧义，5D 确立以下 **4 项不可变更的物理坐标系铁律**：

```
真实网页 (Raw Web)
       │
       ▼
 1. content.html (原始未修改 HTML 快照)
       │
       ▼  WebScraper.extract_clean_text() (Deterministic Pipeline)
          * Newline Normalization: CRLF / CR -> \n
          * Unicode Normalization: unicodedata.normalize('NFC', text)
 2. raw_text.txt (确定性解构正文，永久冻结)
       │
       ▼  Unicode Code-Point 0-indexed Offsets
 3. exact_quote [quote_start : quote_end] (quote_end exclusive)
```

### 物理坐标系四大铁律：
1. **偏移单位**：`quote_start` 与 `quote_end` 统一定义为 Python 解码后的 **Unicode code-point index**（0-indexed，`quote_end` 开区间/exclusive）。
2. **换行符归一化**：所有 `\r\n` (CRLF) 与 `\r` (CR) 一律规范化为单一 `\n` (LF)，杜绝 Windows/Linux 跨平台换行差异。
3. **Unicode 规范化**：解构后的文本严格通过 `unicodedata.normalize('NFC', ...)` 转换为 NFC 格式。
4. **纯确定性物理校验**：
   * `sha256(raw_text.encode('utf-8')) == expected_raw_text_hash`
   * `raw_text[quote_start:quote_end] == exact_quote`
   * 校验过程 **100% 由字符串切片断言完成，严禁调用 LLM 或模糊匹配**。

---

## 3. 数据结构规范 (Schemas)

### 3.1 Case Schema (`claims.jsonl`)

每行为一个独立的 JSON 对象，定义单一原子主张：

```json
{
  "case_id": "p5d-01",
  "cohort": "real_factual_v1",
  "trap_type": "temporal_supersession",
  "claim": "产品 X 的官方售价为 100 美元",
  "verifiability": "PUBLICLY_VERIFIABLE",
  "target_entity": "Company X",
  "content_provenance": "UNMODIFIED_REAL_WEB",
  "claim_provenance": "BENCHMARK_CONSTRUCTED_FROM_REAL_FACTS",
  "created_at": "2026-08-28"
}
```

---

### 3.2 Source Metadata Schema (`sources/p5d-xx/s-yy/metadata.json`)

记录信源物理元信息与抓取状态，**严禁渗漏任何 Gold 标注**：

```json
{
  "source_id": "s-01",
  "case_id": "p5d-01",
  "source_url": "https://www.reuters.com/business/tech/product-x-price-update-2026-01",
  "canonical_url": "https://www.reuters.com/business/tech/product-x-price-update-2026-01",
  "domain": "reuters.com",
  "title": "Company X updates product pricing for 2026",
  "author": "John Doe",
  "published_at": "2026-02-15T10:00:00Z",
  "retrieved_at": "2026-08-28T12:00:00Z",
  "content_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "raw_text_hash": "sha256:8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
  "cleaner_version": "v1.1-nfc",
  "content_type": "text/html; charset=utf-8",
  "byte_length": 45120,
  "fetch_integrity_status": "VALID",
  "source_tier_hint": "AUTHORITATIVE"
}
```

---

### 3.3 独立 Gold 裁定与一致性校验规范 (`evaluation/p5d-xx/gold.json`)

> [!IMPORTANT]
> **Gold 独立裁定原则 (Oracle Independence)**：
> 1. `gold_state` 由**人工预审冻结（Frozen Human Adjudication）**决定，作为终极客观真理。
> 2. `derived_state_from_rules` 由 `verdict_rules.py` 基于标注证据自动求值，作为**内部一致性检查（Internal Consistency Check）**。
> 3. 若 `gold_state != derived_state_from_rules`，必须显式记录 `consistency_status = "DISCREPANCY_FLAGGED"` 并进行同行裁决，严禁被测规则引擎单方面覆盖专家裁判。

```json
{
  "case_id": "p5d-05",
  "claim": "某初创公司获得 5 亿美元战略收购",
  "gold_state": "INSUFFICIENT",
  "derived_state_from_rules": "INSUFFICIENT",
  "consistency_status": "CONSISTENT",
  "annotation": {
    "gold_source": "frozen_human_adjudication_transcript",
    "adjudicated": true,
    "adjudication_rationale": "s-02 与 s-03 均明确注明转载自 s-01 传闻报道，全网缺乏官方证实，因此独立信源仅为 1 个传闻源，客观真理为证据不足。"
  },
  "gold_evidence": [
    {
      "source_id": "s-01",
      "exact_quote": "Startup Alpha has entered preliminary talks for a potential $500M acquisition, according to people familiar with the matter.",
      "quote_start": 412,
      "quote_end": 535,
      "role": "SUPPORTS",
      "directness": "DIRECT",
      "scope_match": true
    },
    {
      "source_id": "s-02",
      "exact_quote": "As first reported by TechReporter, Startup Alpha is in talks for $500M buyout.",
      "quote_start": 120,
      "quote_end": 198,
      "role": "CONTEXTUAL",
      "directness": "INDIRECT",
      "scope_match": true
    }
  ],
  "gold_provenance": [
    {
      "source_id": "s-02",
      "origin_source_id": "s-01",
      "relation": "REPUBLISHES",
      "evidence_quote": "As first reported by TechReporter",
      "evidence_url": "https://techreporter.com/news/alpha-buyout"
    }
  ],
  "gold_independent_origins": [
    "s-01"
  ],
  "gold_source_counts": {
    "total_sources": 2,
    "independent_origins": 1,
    "supporting_origins": 1,
    "contradicting_origins": 0
  }
}
```

---

## 4. 10 类现实世界陷阱矩阵 (10-Trap Taxonomy Matrix)

| 编号 | 陷阱类别 (Trap Type) | 典型真实场景与测试要点 | 信源数 | 独立裁判预期依据 |
| :---: | :--- | :--- | :---: | :--- |
| **p5d-01** | `temporal_supersession` (时间废止) | 历史判决/旧价格被官方最新版本推翻 | 2 | 最新官方证据否定旧事实 $\rightarrow$ 判定新主张是否属实 |
| **p5d-02** | `temporal_supersession` (时间废止) | 新旧口径同时存在但均属于官方阶段性发布 | 2 | 存在支持且存在明确时间跨度冲突 |
| **p5d-03** | `geographic_scope` (地域范围扩大) | 政策仅在单一州有效，主张声称为全美适用 | 2 | 仅有区域限定证据，缺乏全国范围支持 |
| **p5d-04** | `geographic_scope` (地域范围冲突) | 主流媒体分别报道区域试点与全国推广规划 | 2 | 双方信源口径直接对立 |
| **p5d-05** | `republication` (单通稿转载集群) | 1 篇独家首发 + 2 篇注明转载文章 | 3 | 穿透后独立源=1，无官方证实 |
| **p5d-06** | `republication` (通稿 + 独立官方源) | 2 篇媒体互相转载 + 1 篇独立官方公报 | 3 | 穿透后独立源=2（含官方直接证实） |
| **p5d-07** | `numerical_quantifier` (量词范围扩大) | 原文为“最高可达30% (up to)”，主张改为“固定30%” | 2 | 范围不匹配产生可靠反驳 |
| **p5d-08** | `numerical_quantifier` (口径差异) | 包含补贴与不含补贴口径数据差异 | 2 | 两组可靠数据口径并存冲突 |
| **p5d-09** | `exception_context` (前置条件遗漏) | 原文为“对学生免费，除非选购高级模块” | 2 | 忽略前置例外条件产生反驳 |
| **p5d-10** | `exception_context` (生效前置条件) | 协议“须经监管审批后生效”，主张称“已正式生效” | 2 | 缺乏正式生效证明且有前置反驳 |
| **p5d-11** | `negation` (显式否认辟谣) | 传闻甚广，企业官方发言人发布明确辟谣声明 | 2 | 官方明确否认且无实质证实 |
| **p5d-12** | `negation` (负面裁决) | 监管部门正式否决交易申请 | 2 | 官方裁决直接否定主张 |
| **p5d-13** | `entity_version` (型号/版本泛化) | 功能仅限 Pro 机型，主张套用至基础版 | 2 | 存在明确型号限制反驳 |
| **p5d-14** | `entity_version` (同名机构混淆) | 两个同名实体，主张混淆主体成就 | 2 | 无针对本实体的有效证据 |
| **p5d-15** | `boilerplate_sidebar` (侧边栏噪音) | 正文辟谣，但侧边栏“猜你喜欢”出现谣言标题 | 2 | 过滤侧栏后仅剩正文反驳 |
| **p5d-16** | `boilerplate_sidebar` (页脚免责声明) | 广告横幅夸大，正文与页脚明确限制 | 2 | 过滤广告噪音后证据不足 |
| **p5d-17** | `population_restriction` (受众限制) | 疗法仅在小鼠有效，主张声称人体适用 | 2 | 仅有动物试验反驳人体结论 |
| **p5d-18** | `population_restriction` (职业门槛) | 政策仅限持牌专业人士，主张扩大至大众 | 2 | 存在门槛限定反驳 |
| **p5d-19** | `temporal_omission` (季度/阶段省略) | 财报显示“Q3 营收增长30%”，主张称“全年增长30%” | 2 | 阶段性数据无法代表全年 |
| **p5d-20** | `temporal_omission` (历史现状混淆) | 2018 年历史数据被主张作为当前现状引用 | 2 | 历史数据与当前现状脱节 |

---

## 5. 快照完整性与 Fetch 管道 (Fetch Integrity Pipeline)

```
真实 HTTP 请求
      │
      ▼
 1. HTTP 状态码校验 (必须为 200)
      │
      ▼
 2. Content-Type 校验 (text/html 或 text/plain)
      │
      ▼
 3. Anti-bot / WAF 拦截检测 (无 robot challenge / cloudflare 质询)
      │
      ▼
 4. 结构化内容完整性检测 (非空且包含目标实体信息)
      │
      ▼
 5. HTML 原始快照入库 (content.html + content_hash)
      │
      ▼
 6. 确定性正文解构 (Unicode NFC + \n 统一 -> raw_text.txt + raw_text_hash)
      │
      ▼
 VALID 快照固化入库
```

### 快照细粒度状态分类：
* **`VALID`**：通过全部校验，成功提取正文并固化双哈希。
* **`INVALID_ROBOT_BLOCK`**：被反爬策略/WAF 拦截。
* **`INVALID_CAPTCHA`**：需要图形验证码/人机验证。
* **`INVALID_EMPTY`**：提取正文为空或无结构化内容。
* **`INVALID_WRONG_ENTITY`**：页面标题或正文完全不包含目标实体关键字。
* **`INVALID_HASH`**：快照文件内容与哈希签名不一致。
* **`FETCH_ERROR`**：底层网络或 HTTP 传输异常。

---

## 6. 全要素评测指标体系 (Comprehensive Metric Framework)

```text
1. Final EvidenceState Accuracy
   = 正确判定 6 态样本数 / N_valid

2. Overclaim Rate (核心安全指标)
   = (系统判定强于 Gold 的样本数) / N_valid
   [例: Gold 为 INSUFFICIENT，系统判定为 STRONG/SUFFICIENT]

3. Conservative Miss Rate
   = (系统判定弱于 Gold 但未错误反驳的样本数) / N_valid
   [例: Gold 为 STRONG，系统保守判定为 INSUFFICIENT]

4. Claim Extraction Success Rate
   = 成功从真实 DOM 抽取到相关原子事实的样本率

5. Dual Quote Grounding Rates
   * Conditional Quote Grounding: 抽取成功样本中，在 raw_text.txt 中 100% 物理精准锚定的比率
   * Operational Quote Grounding: 全量有效样本的端到端物理锚定率

6. Evidence Polarity Accuracy
   = 证据角色 (SUPPORTS / CONTRADICTS / CONTEXTUAL) 与 Gold 一致率

7. Provenance Relation Accuracy
   = CITES / REPUBLISHES / NONE 关系抽取正确率

8. Ultimate Origin Recovery Rate
   = _resolve_ultimate_origin 还原到的根源 source_id 与 Gold 一致率

9. Operational Completion Rate (Infra Resolution Rate)
   = (N_valid - UNRESOLVED_INFRA) / N_valid
```

---

## 7. 12 步标准执行工作流 (Standard 12-Step Execution Workflow)

```text
STEP 0. 规范冻结 (Freeze DATASET_SPEC v1.1)
   │
STEP 1. 物理坐标系建立 (HTML -> deterministic raw_text.txt with NFC & LF)
   │
STEP 2. 编写真实抓取器与 Fetch Integrity Gate 自动化采集器
   │
STEP 3. 20 个真实候选案例真实 URL 筛选 (高质量候选，不符合即剔除)
   │
STEP 4. 真实公网网页快照抓取与双哈希固化
   │
STEP 5. 细粒度 Gold Evidence & Provenance 人工第一轮标注
   │
STEP 6. 独立双审专家裁定 Gold State 并与规则引擎进行一致性交叉校验
   │
STEP 7. 数据集与哈希签名全量冻结 (生成 DATASET_CARD.md 与 manifest.json)
   │
STEP 8. 构建生产级通用核验服务 VerificationService
   │
STEP 9. Run A: 生产服务 + Mock 基线评测
   │
STEP 10. Run B: 生产服务 + Real LLM 端到端评测 (计算 LLM Recovery Gain)
   │
STEP 11. Run C: 消融实验 (Ablation: Provenance Resolver / Scope Polarity)
   │
STEP 12. 生成 7+2 项综合指标报告、Overclaim 矩阵与混淆矩阵
```
