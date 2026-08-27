# 🔍 AI Claim Verifier (事实核验透视镜)

> **基于 Evidence-First 的多源事实核验与证据状态判定系统**  
> 不下主观断言，只回答一个核心问题：**「现有公开证据是否足以支持这个说法？」**

---

## 🎯 系统核心哲学 (Core Philosophy)

> **AI 不是上帝，不能直接宣称现实世界某件事情是绝对的“真”或“假”。**  
> 本系统的使命是：**寻找公开证据 → 判断证据质量与直接性 → 识别同源与转载链条 → 寻找支持与反证 → 用保守的确定性规则引擎，告诉用户目前公开证据支持到什么程度。**

```
用户输入一个说法 (文字 / 链接 / 截图)
         │
         ▼
 1. 主张拆解 (Claim Decomposition)
    将长句/复合陈述拆解为 1~N 个独立可验证事实点
         │
         ▼
 2. 定向证据检索与抽取 (Evidence Retrieval & Extraction)
    检索公开网络信源，提取精确引文并标记支持/反驳/直接性/范围匹配
         │
         ▼
 3. 信息溯源去重 (Source Provenance)
    穿透通稿转载链条，还原真实原始信息源 (Origin Source)
         │
         ▼
 4. 确定性规则引擎 (Rule-Engine Verdict)
    由严密的逻辑边界计算判定，杜绝 LLM 概率瞎猜与数量崇拜
         │
         ▼
 5. 结构化呈现 (Verdict Card & Coverage)
    输出 6 级证据状态、判定依据清单、关键证据缺口与核实指引
```

---

## 🌟 6 级证据状态体系 (Evidence States)

用户端展示严格对应以下 6 种证据状态：

| 证据状态 | 英文枚举 | 核心判定逻辑 |
|---|---|---|
| 🟢 **证据充分** | `SUFFICIENT` | 拥有 ≥2 个独立信息源直接支持，且包含官方/一手渠道直接证实，无可信反驳 |
| 🟢 **证据较强** | `STRONG` | 拥有 ≥2 个独立可靠信息源直接证实，无可信反驳 |
| 🟡 **证据不足** | `INSUFFICIENT` | 证据链不完整、仅有单一信息源、均为二次转载，或尚未检索到有效证据（**“没搜到 ≠ 证明是假的”**） |
| 🟠 **存在冲突** | `CONFLICTING` | 可靠信源之间存在直接对立或口径差异（如融资金额或统计数据不一） |
| 🔴 **有可靠证据反驳** | `UNSUPPORTED` | 存在权威/第一手渠道的明确否定反证，且缺乏对等的可靠支持 |
| ⚪ **公开资料无法核验** | `NOT_ASSESSABLE` | 涉及私人行为或非公开未披露事项，无法通过公开互联网资料进行有效判定 |

---

## 🛡️ 核心设计原则 (Design Principles)

1. **规则引擎驱动判定**：最终 Verdict 状态由纯逻辑规则引擎（`verdict_rules.py`）严格计算，LLM 仅负责文本片段提取与人话解释翻译。
2. **信息溯源去重 (Provenance)**：穿透二次转载与引用关系（`CITES` / `REPUBLISHES`），避免将“10 个互相抄袭的通稿”误判为“10 个独立来源”。
3. **复合主张完整覆盖 (Claim Coverage)**：复合输入分别核验，多维度生成完整性覆盖结论（`FULLY_SUPPORTED` / `PARTIALLY_SUPPORTED` / `MIXED` / `FULLY_UNSUPPORTED` / `NOT_ASSESSABLE`），杜绝粗暴“取最弱”。
4. **可追溯证据绑定**：核验结果尽可能绑定可追溯的原始来源域名、发布时间与具体引文片段。
5. **不使用伪精确概率**：不展示无数学依据的“78% 可信度”或模糊标签，仅呈现事实依据清单与关键缺口。

---

## 🚀 快速启动 (Quick Start)

### 1. 激活虚拟环境与启动服务

在项目根目录下运行：

```powershell
# PowerShell 环境
.\.venv\Scripts\Activate.ps1

# 或 Windows CMD 环境
.\.venv\Scripts\activate.bat

# 启动一体化服务 (FastAPI 后端 + 前端静态托管)
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

或者直接双击根目录下的 `start_app.bat` 脚本一键启动。

### 2. 打开网页控制台
浏览器访问：[http://127.0.0.1:8000](http://127.0.0.1:8000)

### 3. 运行自动化测试套件
```powershell
.\.venv\Scripts\pytest backend\tests -v
```

---

## ⚙️ 运行模式与 API 密钥配置

系统默认内置**离线拟真引擎与事实库**（无需任何 API Key 即可全流程离线体验与测试）。如需接入实时公网大模型与搜索：

1. **网页端配置**：点击页面右上角 **「API 配置」**，在弹出窗口中填写您的 `Google Gemini`、`OpenAI / DeepSeek` 或 `Tavily` 密钥（仅保存在本地浏览器）。
2. **环境变量配置**：复制 `.env.example` 到 `.env`：

```env
# 推理模型 (支持 Gemini, OpenAI, DeepSeek, Mock)
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here

# 搜索引擎 (支持 DuckDuckGo 免费搜索, Tavily, Mock)
DEFAULT_SEARCH_PROVIDER=duckduckgo
TAVILY_API_KEY=your_tavily_api_key_here

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./investigator.db
```
