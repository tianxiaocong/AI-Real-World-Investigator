# 🔍 AI Claim Verifier (事实核验透视镜)

> **基于 Evidence-First 的多源事实核验与证据状态判定系统**  
> 不下主观断言，只回答一个核心问题：**「现有公开证据是否足以支持这个说法？」**

---

## 🌟 核心设计原则 (Design Principles)

1. **证据状态判定 (Evidence State vs Truth Claim)**：系统不对现实真伪妄下定论，而是严格评估公开证据链状态：
   - 🟢 `SUFFICIENT`（证据充分）：多独立来源 + 官方一手直接证实 + 无可信反驳
   - 🟢 `STRONG`（证据较强）：多独立来源直接支持 + 无可信反驳
   - 🟡 `INSUFFICIENT`（证据不足）：公开证据不完整、仅有转载或单一来源（"没搜到 ≠ 证明是假的"）
   - 🟠 `CONFLICTING`（存在冲突）：可靠来源之间存在直接对立或口径差异
   - 🔴 `UNSUPPORTED`（有可靠证据反驳）：存在权威/第一手明确反证，且缺乏对等直接支持
   - ⚪ `NOT_ASSESSABLE`（公开资料无法核验）：私人行为或非公开事项
2. **规则引擎驱动 (Rule-Engine Driven Verdict)**：核心结论由确定性规则引擎与逻辑边界计算，LLM 仅负责引文提取与人话解释，杜绝大模型幻觉与概率瞎猜。
3. **来源溯源图谱 (Source Provenance)**：穿透二次转载与通稿复制链条，精准识别原始信息源（Origin Source），杜绝"10个转载当作10个独立信源"的数量崇拜。
4. **多主张拆解与完整覆盖 (Claim Decomposition & Coverage)**：输入复合长句时自动分解为独立可验证子事实，分别出具证据判断并汇总覆盖结论。
5. **字符级精准引文 (Exact Quote Anchoring)**：每条证据均锁定原始网页精确片段与发布时间有效性，支持多维度交叉比对。

---

## 🚀 快速启动 (Quick Start)

### 1. 激活虚拟环境与启动后端

在项目根目录下运行：

```powershell
# PowerShell 环境
.\.venv\Scripts\Activate.ps1

# 或 Windows CMD 环境
.\.venv\Scripts\activate.bat

# 启动一体化服务 (FastAPI + 前端静态托管)
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

或者直接双击根目录下的 `start_app.bat` 脚本一键启动。

### 2. 打开网页控制台
浏览器访问：[http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🎯 五大专属调查场景 (Specialized Investigation Modes)

系统根据不同的调查场景，自动匹配差异化的侦察方法论与子问题拆解：
1. 🏢 **企业全景背调 (`COMPANY`)**：组织架构、创始人履历、融资财务、产品矩阵、诉讼与合规风险。
2. 📱 **产品深度评测 (`PRODUCT`)**：技术参数实测、故障率与真实口碑、竞品横向对比、价格毛利。
3. 💰 **投资商业尽调 (`INVESTMENT`)**：商业模式闭环、造血能力、主要资方资质、非法集资/虚假宣传欺诈排查。
4. 🔍 **事实核验与辟谣 (`CLAIM`)**：原始出处溯源、官方通报与声明、传播链反转与关键反证链。
5. 🔬 **技术成熟度评估 (`TECHNOLOGY`)**：底层科学原理、论文与专利、第三方 Benchmark 实测、宣传夸大与落地短板。

---

## ⚙️ API 密钥配置

您可以通过两种方式配置 API 密钥：
1. **方式一（网页端动态配置）**：点击页面右上角 **「API 配置」**，在弹出窗口中填写您的 `Google Gemini`、`OpenAI / DeepSeek` 或 `Tavily` 密钥（保存在本地浏览器，随任务动态注入后端）。
2. **方式二（服务端环境配置文件）**：复制 `.env.example` 到 `.env`：

```env
# 推理模型 (支持 Gemini, OpenAI, DeepSeek, Mock)
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here

# 搜索引擎 (支持 DuckDuckGo 免费搜索, Tavily, Mock)
DEFAULT_SEARCH_PROVIDER=duckduckgo
TAVILY_API_KEY=your_tavily_api_key_here

# 数据库 (默认免配置本地 SQLite，支持 PostgreSQL + pgvector)
DATABASE_URL=sqlite+aiosqlite:///./investigator.db
```
