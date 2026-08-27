# 📊 AI Claim Verifier Benchmark Suite

> **面向事实核验规则引擎与证据判定的自动化评测基准**

---

## 🎯 评测体系设计

本评测体系严格分为两层：

1. **第一层：规则引擎回归基准 (Synthetic Rule Regression Benchmark)**：
   - 目标：确保 `verdict_rules.py` 的确定性边界逻辑、`SourceProvenance` 溯源去重算法与状态转移没有被意外改坏。
   - 核心防线：**Overclaim Rate（过度断言率 / 证据不足却误判为充分）必须严格保持为 0.0%**。
2. **第二层：真实世界端到端评测 (Real-World E2E Benchmark)** *(规划中)*：
   - 从实际网页搜索、真实引文抽取、溯源图谱到最终生成的全链路盲测评估。

---

## 🚀 运行规则引擎回归评测

在项目根目录下执行：

```powershell
.\.venv\Scripts\python benchmark\run_benchmark.py
```

---

## 📈 当前规则回归评测指标 (Rule Regression Results)

| 评测维度 | 样本类型 | 评估用例数 | 结果 |
|---|---|---|---|
| **规则回归通过率 (Regression Pass Rate)** | 边界场景用例 | 10 | **100.0% (10/10)** |
| **过度断言率 (Overclaim Rate - 风险指标)** | 弱证据误判为强 | 10 | **0.0% (零过度断言)** |
| **通稿同源去重率 (Provenance Dedup)** | 10 篇转载溯源 | 10 篇同源 | **100.0% (识别出 1 个原始源)** |
| **引文锚定匹配 (Quote Match Precision)** | 字符级引文比对 | 原文匹配 | **EXACT (原始文本) / FUZZY / UNVERIFIED 严格分级** |

---

## 📁 覆盖测试用例分类 (`benchmark_cases.jsonl`)

- `CONFIRMED_FACT`：多独立权威媒体直接证实
- `OFFICIAL_SUPPORTED`：企业官方一手公告与主流媒体交叉印证
- `NUMERICAL_DISPUTE`：不同财报/审计机构重大金额矛盾 (`CONFLICTING`)
- `PRICE_VARIANT_DIFFERENCE`：官方指导价 vs 渠道补贴价差异（口径差异不误判为事实冲突）
- `SYNDICATED_SINGLE_ORIGIN`：10 家媒体通稿同源转载（识别为独立信源=1，判定为 `INSUFFICIENT`）
- `FACTUALLY_REFUTED`：官方监管档案直接否定反驳 (`UNSUPPORTED`)
- `PRIVATE_MATTER`：非公开私人事项 (`NOT_ASSESSABLE`)
