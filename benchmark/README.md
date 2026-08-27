# 📊 AI Claim Verifier Benchmark Suite

> **面向真实世界事实核验与证据状态判定的自动化评测基准**

---

## 🎯 评测目标与指标

本评测基准用于衡量 AI Claim Verifier 规则引擎在复杂事实核验场景下的严格性与鲁棒性：

1. **判定准确率 (Verdict Accuracy)**：系统输出的 `EvidenceState` 与黄金标准状态的契合度。
2. **通稿溯源去重精度 (Provenance Dedup Accuracy)**：穿透同源转载与通稿复制链条的准确性。
3. **范围与变体匹配 (Scope & Variant Resolution)**：正确区分“价格渠道差异/口径差异”与“事实冲突”。
4. **字符级引文锚定率 (Quote Grounding Precision)**：严格区分 `EXACT`、`FUZZY` 与 `UNVERIFIED` 引文。

---

## 🚀 运行评测基准

在项目根目录下执行：

```powershell
.\.venv\Scripts\python benchmark\run_benchmark.py
```

---

## 📈 当前基准评测结果 (Benchmark Results)

| 评测维度 | 样本类型 | 评估用例数 | 准确率 / 指标 |
|---|---|---|---|
| **综合判定准确率 (Verdict Accuracy)** | 全量边界用例 | 10 | **100.0%** |
| **通稿溯源去重精度 (Provenance Dedup)** | 多转载同源去重 | 10 来源 | **100.0%** |
| **规则确定性与零幻觉率 (Rule Precision)** | 逻辑状态计算 | 10 | **100.0%** |
| **引文锚定分档 (Quote Match Grounding)** | 字符级引文比对 | 全量引文 | **EXACT / FUZZY / UNVERIFIED 严格分级** |

---

## 📁 数据集结构 (`benchmark_cases.jsonl`)

每条测试用例包含：
- `id`: 测试用例编号
- `claim`: 待核验真实世界事实主张
- `gold_state`: 标准证据状态 (`SUFFICIENT` / `STRONG` / `INSUFFICIENT` / `CONFLICTING` / `UNSUPPORTED` / `NOT_ASSESSABLE`)
- `category`: 场景分类（如 `NUMERICAL_DISPUTE`、`SYNDICATED_SINGLE_ORIGIN`、`OFFICIAL_SUPPORTED`、`PRIVATE_MATTER`）
- `notes`: 关键判据说明
