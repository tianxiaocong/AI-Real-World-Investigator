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

### 1. 安装依赖与启动后端
```bash
# 1. 激活虚拟环境
.\.venv\Scripts\activate

# 2. 安装依赖
pip install -r backend/requirements.txt

# 3. 启动一体化服务 (FastAPI + 前端静态托管)
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 打开网页控制台
浏览器访问：[http://localhost:8000](http://localhost:8000)

---

## ⚙️ 环境变量配置 (.env)

复制 `.env.example` 到 `.env` 并按需填写：

```env
# 推理模型 (默认支持 Gemini, OpenAI, DeepSeek, Mock)
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
FAST_LLM_MODEL=gemini-1.5-flash
REASONING_LLM_MODEL=gemini-1.5-pro

# 搜索引擎 (支持 DuckDuckGo 免费搜索, Tavily, Mock)
DEFAULT_SEARCH_PROVIDER=duckduckgo
TAVILY_API_KEY=your_tavily_api_key_here

# 数据库 (默认免配置 SQLite，支持 PostgreSQL + pgvector)
DATABASE_URL=sqlite+aiosqlite:///./investigator.db
```

---

## 🏗️ 系统架构与设计文档

详见白皮书：
- [TECHNICAL_SPEC_AND_ARCHITECTURE.md](./TECHNICAL_SPEC_AND_ARCHITECTURE.md)
- [implementation_plan.md](./implementation_plan.md)
