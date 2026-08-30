# 🕵️‍♂️ AI Real-World Investigator (AI 现实世界侦察兵)

> **面向真实世界事实调查与深度核验的 Evidence-First 工程系统**  
> 旗舰核心引擎：**🔍 AI Claim Verifier (事实核验透视镜)**  
> 不下主观断言，只回答一个核心问题：**「现有公开证据是否足以支持这个说法？」**  
> *A Reliable, Auditable, and Deterministic Web Evidence Adjudication System.*

---

## 🎯 系统核心主线与设计哲学 (Core Product Narrative & Triad)

在开放世界事实核查中，端到端大模型（LLM-only）天然存在引文幻觉、同源转载回音壁、口径与时效失真以及过度断言（Overclaim）等系统性脆弱性。

本系统的核心使命是：**构建一个高可靠、可审计、抗欺骗的现实世界调查系统，并通过真实实验与持续迭代不断发现和修复失败。**

```text
                 AI Real-World Investigator
                           │
                           ▼
              现实世界事实调查 / 证据核验
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
     正确性 (Correctness)  可审计性 (Auditability) 安全性 (Security)
        │                  │                  │
        ▼                  ▼                  ▼
   Claim Extraction     Exact Quote Grounding  Hop-by-Hop SSRF
   Search & Retrieval   Auditable Evidence     Anti-Spoof Classifier
   Scope & Polarity     Provenance Graph       IPv4/IPv6 getaddrinfo
   Consistency Gating   Strict Source Identity Resource Limits
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
               Deterministic Safety Guard (规则安全闸门)
                           │
                           ▼
                Final EvidenceState (6 级证据状态)
                           │
                           ▼
              Human-readable Verdict Report (可溯源报告)
```

### 核心设计原则：**职责分离 (Separation of Concerns)**
$$\text{LLM is the Semantic Reader, not the Final Judge.}$$

* **原网页 (Raw Documents)**：负责提供事实原材料与 DOM 快照；
* **大模型 (LLM Extractor)**：负责理解复杂自然语言、提取候选引文、识别陈述极性与范围冲突（Scope Issues）；
* **精确物理定位器 (Exact Locator)**：在规范化文本（Canonical Text）中建立 Unicode 码点级字符落点，实时拒认幻觉引用；
* **来源血缘解析器 (Provenance Graph)**：以严格 Source Identity 优先，遍历 `REPUBLISHES` 与 `CITES` 图谱，去重同源转载与引文回音壁；
* **确定性规则闸门 (Deterministic Guard)**：作为最后一道安全防线，依据严格定义的证据状态机实施时空/数量一致性门禁，阻断危险的假证实。

---

## 🔄 核心工程开发与验证闭环 (The Engineering Reliability Loop)

整个系统的演进始终围绕以下可靠性链路展开：

$$\text{搜得到} \longrightarrow \text{抓得准} \longrightarrow \text{读得对} \longrightarrow \text{引得准} \longrightarrow \text{来源不重} \longrightarrow \text{时空不乱} \longrightarrow \text{危险阻断} \longrightarrow \text{可溯源}$$

```text
真实调查场景 ──▶ 发现失败案例 ──▶ 定位失败层 (抽取/定位/血缘/规则/网络)
                                            │
                                            ▼
冻结版本 ◀── 确认真实改善 ◀── 真实大模型重测 ◀── 修复代码/Prompt/数据结构
```

---

## 📸 交互界面与核验效果预览 (UI & Verdict Showcase)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  AI Real-World Investigator  ·  AI Claim Verifier               [⚙️ API 配置]│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                            这个说法是真的吗？                                │
│          输入一段话、粘贴新闻链接或上传截图，基于公开证据链快速核验。         │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ [📝 文本陈述]   [🔗 网页链接]   [📷 截图提取]                          │  │
│  │                                                                       │  │
│  │ “宇树科技于2024年完成近10亿元人民币B2轮融资，美团领投”                  │  │
│  │                                                                       │  │
│  │ 试试这些例子： [宇树科技完成近10亿融资]  [OpenAI已实现盈利]  [某产品成本20元]  │  │
│  │                                                                       │  │
│  │ 运行模式: 离线拟真引擎 (内置事实库)                     [ 🔍 开始核验 ] │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ─── 核验结论 (Verdict Card) ────────────────────────────────────────────── │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ 🟢 证据充分 (SUFFICIENT)   [公开可验证事实]           核验时间: 动态实时   │  │
│  │                                                                       │  │
│  │ “宇树科技于2024年完成近10亿元人民币B2轮融资，美团领投”                  │  │
│  │                                                                       │  │
│  │ ▍ 为什么这样判断？(核验依据)                                          │  │
│  │  ✓ 找到 2 个相互独立的权威信息源证实该融资事件                          │  │
│  │  ✓ 获得企业官方公告与主流财经创投直接确认                               │  │
│  │  ℹ️ 未发现主要投资方或监管层面的相悖反驳                              │  │
│  │                                                                       │  │
│  │ ▍ 关键证据缺口                                                        │  │
│  │  ⚠ 尚未查验对应工商登记实缴资本变更记录                               │  │
│  │                                                                       │  │
│  │ ▍ 下一步核实建议                                                      │  │
│  │  如需进一步核实细节，可查阅全国企业信用信息公示系统或国家企业信用报告。  │  │
│  │                                                                       │  │
│  │                                       [ 🔄 核验新说法 ] [ 📋 复制结论 ]│  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 💡 为什么不是普通的 AI 搜索总结？(Core Technical Moat)

| 维度 | 普通 AI 搜索总结 (Search + LLM) | AI Claim Verifier 证据核验引擎 |
|---|---|---|
| **核心机制** | 搜索抓取若干网页 → LLM 直接生成结论 | **主张解构 → 逐字物理锚定 → 来源血缘穿透 → 确定性规则裁决** |
| **同源转载识别** | 10 家媒体转载同一通稿被误认为“10 个独立证实” | **遍历 `REPUBLISHES` / `CITES` 图谱，识别实际仅有 1 个原始源** |
| **引文可信度** | 依赖 LLM 自行生成的带引号句子（容易幻觉） | **Unicode 码点级逐字切片，未物理落地的引文直接标记 `UNVERIFIED`** |
| **时效与口径** | 容易忽略生效时间（旧价格）与口径差异（GAAP vs Non-GAAP） | **提取 `ScopeIssue`（TEMPORAL / QUANTIFIER），实质阻断假证实** |
| **判定确定性** | 每次询问受 Temperature 扰动输出不同结果 | **由 `verdict_rules.py` 规则引擎执行确定性状态转移** |
| **安全防护** | 爬虫直接请求目标 URL，易受 SSRF 与域名仿冒攻击 | **IPv4/IPv6 `getaddrinfo` + 逐跳重定向验证 + 后缀严格防伪** |

---

## 🌟 6 级证据状态体系 (Canonical EvidenceState Ontology)

系统统一以 `EvidenceState` 作为第一类 Canonical Ontology（旧 `VerificationStatus` 仅作为向下兼容层）：

| 证据状态 | 英文枚举 | 核心判定逻辑与门禁要求 |
|---|---|---|
| 🟢 **证据充分** | `SUFFICIENT` | $\ge 2$ 个独立信息源直接支持 + 包含官方/一手渠道证实 + 无可信反驳 + 时空与数量口径一致 (`time/value_consistent is not False`) |
| 🟢 **证据较强** | `STRONG` | $\ge 2$ 个独立可靠信息源直接证实 + 无可信反驳 + 时空与数量口径一致 |
| 🟡 **证据不足** | `INSUFFICIENT` | 证据链不完整、仅有单一信息源、均为二次转载、时空/数值冲突降级，或尚未检索到有效证据（**“没搜到 ≠ 证明是假的”**） |
| 🟠 **存在冲突** | `CONFLICTING` | 可靠信源之间存在直接对立或口径冲突（如融资金额或统计数据不一） |
| 🔴 **有可靠证据反驳** | `UNSUPPORTED` | 存在权威/第一手渠道的明确否定反证，且缺乏对等的可靠支持 |
| ⚪ **公开资料无法核验** | `NOT_ASSESSABLE` | 涉及私人行为或非公开未披露事项，无法通过公开互联网资料进行有效判定 |

---

## 🎯 10 类对抗性陷阱分类法 (The 10-Trap Taxonomy)

系统的 Benchmark 与规则引擎专门针对真实世界最容易误导大模型的 10 种对抗场景设计：

1. **`TEMPORAL_SUPERSEDING`**（时间更替）：早期历史价格/旧版本被后续更新更替（如 $20/月涨至 $30/月）。
2. **`GEOGRAPHIC_SCOPE`**（地域限定）：局部国家/地区政策或促销被错误泛化为全球通用。
3. **`REPUBLICATION_CASCADE`**（同源转载回音壁）：1 篇原始泄漏被 10 家科技自媒体转载，伪装成 10 个独立来源。
4. **`NUMERICAL_QUANTIFIER`**（数量级混淆）：金额或数字量级混淆（如 1000 万美元 A 轮 vs 10 亿美元融资）。
5. **`CONDITION_EXCEPTION`**（条件与例外）：忽略前置适用条件或明确排除条款（如“除特定企业客户外”）。
6. **`NEGATION_DENIAL`**（否定与辟谣）：官方发言人明确辟谣否认，反被大模型理解为证实离职。
7. **`ENTITY_VERSION`**（实体与版本张冠李戴）：不同产品型号或概念实体的属性产生混淆。
8. **`BOILERPLATE_NOISE`**（侧边栏与模板噪声）：把网页侧边栏热搜推荐、页脚版权声明当正文事实提取。
9. **`POPULATION_RESTRICTION`**（人群/实验对象限定）：动物模型实验数据套用到人体临床获批。
10. **`TEMPORAL_OMISSION`**（时间定语缺失）：缺失时间状语导致陈述与最新现状冲突。

---

## 📊 非线性解耦评测指标体系 (Safety-First Metric Definitions)

为避免将无序的证据状态误当作线性标尺，评测体系严格解耦为四项独立指标：

1. **Exact State Accuracy**：$\frac{1}{N} \sum \mathbb{I}(\hat{y}_i = y_i)$，预测状态与人工黄金标签完全吻合率。
2. **Safety Overclaim Rate (核心安全红线，实测追求 0.0%)**：
   $$\text{Overclaim Rate} = \frac{\sum_{i=1}^N \mathbb{I}(y_i \in \{\text{INSU}, \text{UNSP}, \text{CONF}, \text{N\_AS}\} \land \hat{y}_i \in \{\text{SUFF}, \text{STRO}\})}{N}$$
   *说明：衡量系统是否把证据不足、存疑或存在反驳的事实错误判定为充分证实。规则引擎作为安全闸门提供约束，实际系统的安全表现通过多模型真实评测进行实证检验。*
3. **Conservative Miss Rate**：真实充分的事实被保守降级为证据不足的比率。
4. **Quote Grounding Rate**：模型提取引文在原始源文档中实现逐字精准定位的比率（`EXACT` / `NORMALIZED_EXACT`）。

---

## 🚀 快速启动 (Quick Start)

### 1. 激活虚拟环境与启动服务

```powershell
# PowerShell 环境
.\.venv\Scripts\Activate.ps1

# 启动一体化服务 (FastAPI 后端 + 前端静态托管)
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

或者直接双击根目录下的 `start_app.bat` 脚本一键启动。

### 2. 打开网页控制台
浏览器访问：[http://127.0.0.1:8000](http://127.0.0.1:8000)

### 3. 运行全量自动化测试套件
```powershell
.\.venv\Scripts\pytest backend\tests -v
```

### 4. 运行评测基准套件
```powershell
# 1. 合成规则引擎边界回归评测 (10 案)
.\.venv\Scripts\python benchmark/run_benchmark.py

# 2. 真实世界端到端拟真基准评测 (35 案)
.\.venv\Scripts\python benchmark/real_world/run_real_world_benchmark.py --mock

# 3. 冻结长篇网页消融研究 (Phase 5E Control & Ablations)
.\.venv\Scripts\python benchmark/real_factual/run_phase_5e_ablations.py --mode mock --run control
```

---

## 📁 核心代码工程架构 (Project Structure)

```text
AI-Real-World-Investigator/
├── backend/
│   └── app/
│       ├── agents/          # 智能体层 (ClaimExtractor, Verifier, FastVerifier, Synthesizer)
│       ├── api/             # FastAPI 路由 (/verify, /investigations, /health)
│       ├── core/            # 核心安全与网络防御 (security.py: SSRF, IPv6, Anti-Spoofing)
│       ├── engine/          # 确定性裁决状态机 (verdict_rules.py)
│       ├── models/          # 数据模型 (verification_models.py: Canonical EvidenceState)
│       ├── providers/       # LLM 与搜索提供方抽象 (Gemini, OpenAI, DeepSeek, Tavily)
│       ├── scraper/         # 安全爬虫与逐字物理定位 (extractor.py: WebScraper)
│       └── services/        # 统一核验业务流 (verification_service.py)
├── benchmark/
│   ├── real_factual/        # 冻结长网页 20 案快照与 Phase 5E 单组件消融评测
│   ├── real_web/            # Live Real-Web 端到端跨模型横向评测套件
│   ├── real_world/          # 35 案真实场景端到端流水线评测
│   └── run_benchmark.py     # 合成规则引擎边界回归运行器
├── frontend/                # 前端单页应用 (Vanilla HTML/CSS/JS, 响应式深色玻璃拟态)
└── paper/
    └── MANUSCRIPT.md        # 学术论文手稿 (Evidence-First Web Investigation)
```
