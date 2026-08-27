# 🕵️‍♂️ AI 现实世界侦察兵 (AI Real-World Investigator)

> **基于 Evidence-First 原则的深度自主调查与事实可回溯研究平台**  
> 不做简易搜索总结器，只做严谨的 AI 调查记者与情报分析员。

---

## 🌟 核心特色 (Core Highlights)

1. **Evidence First (证据第一)**：所有关键结论均绑定原始网页中的**字符级精确证据片段 (`Exact Quote`)** 与上下文视窗，拒绝无源幻觉。
2. **原子化主张建模 (Claim Modeling)**：自动区分：
   - `FACT`（客观事实）
   - `INFERENCE`（推论）
   - `OPINION`（主观观点）
   - `UNVERIFIED`（未证实传言）
   - `CONFLICTING`（相互矛盾信息）
3. **多源交叉核验与矛盾仲裁 (Cross-Verification Engine)**：利用向量嵌入聚类相同议题，自动识别多源一致支持（`MULTI_SOURCE_SUPPORTED`）与相互对立的冲突事实（`CONFLICTING`）。
4. **实时情报雷达视窗 (Live SSE Radar)**：通过 Server-Sent Events 实时推送子课题规划、信源捕获与主张提取瀑布流。
5. **交互式证据透视镜 (Evidence Inspector Drawer)**：点击研报中的任何角标 `[1]` 或陈述，右侧抽屉直接展示原始网页上下文、发布时间、权威度评分与冲突来源。

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
