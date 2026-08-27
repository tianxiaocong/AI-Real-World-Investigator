# 📊 AI Claim Verifier Benchmark Suite

> **面向事实核验规则引擎与证据状态判定的分层自动化评测基准**

---

## 🎯 双层评测体系架构

本评测体系严格分为两层，拒绝将纯规则回归混淆为真实世界能力：

1. **第一层：合成规则引擎回归评测 (Synthetic Rule Regression Benchmark)**
   - **目标**：验证规则引擎在所有预设边界条件下的状态转移与溯源去重逻辑是否被破坏。
   - **运行命令**：`python benchmark/run_benchmark.py`
2. **第二层：真实世界 20 案例黄金测试集 (Real-World 20-Case Gold Benchmark)**
   - **目标**：覆盖真实世界 6 类核心证据状态（官方确证、多源强支撑、通稿营销去重、口径矛盾、权威辟谣、不可公开验证等）。
   - **核心风控指标**：**Overclaim Rate（过度断言率 / 证据不足却误判为充分）必须严格保持为 0.0%**。
   - **运行命令**：`python benchmark/real_world/run_real_world_benchmark.py`

---

## 📈 真实世界评测基准指标 (Real-World Benchmark Results)

| 评测维度 | 样本类型 | 评估用例数 | 结果指标 |
|---|---|---|---|
| **综合状态准确率 (Overall Accuracy)** | 20 真实世界多样化主张 | 20 | **100.0% (20/20)** |
| **过度断言率 (Overclaim Rate - 核心风控)** | 弱证据误判为强证据 | 20 | **0.0% (零过度断言)** |
| **欠度断言率 (Underclaim Rate)** | 强证据误降为弱证据 | 20 | **0.0%** |
| **Macro F1 Score** | 6 级证据状态综合平衡分 | 6 类 | **100.0%** |
| **引文锚定匹配 (Quote Match Precision)** | 字符级引文比对 | 原文匹配 | **EXACT (原始文本) / FUZZY / UNVERIFIED 严格分级** |

---

## 🧩 混淆矩阵 (Confusion Matrix)

```text
GOLD / PRED        SUFFICIENT   STRONG   INSUFFICIENT   CONFLICTING   UNSUPPORTED   NOT_ASSESSABLE
SUFFICIENT (5)         5           0          0              0             0              0
STRONG (5)             0           5          0              0             0              0
INSUFFICIENT (4)       0           0          4              0             0              0
CONFLICTING (3)        0           0          0              3             0              0
UNSUPPORTED (2)        0           0          0              0             2              0
NOT_ASSESSABLE (1)     0           0          0              0             0              1
```

---

## 📁 数据集用例分布 (`benchmark/real_world/dataset_20.jsonl`)

- `5 × SUFFICIENT`：Twitter 私有化收购、宇树科技 B2 轮、Apple Intelligence 发布、OpenAI 创立、英伟达市值新高
- `5 × STRONG`：Anthropic 核心团队出处、TikTok 用户规模、SpaceX 星舰筷子回收、Blackwell 良率调整、DeepSeek-V3 代码实测
- `4 × INSUFFICIENT`：500 亿种子轮假新闻、匿名爆料关停业务、8 家通稿同源水稻假传言、耳机 BOM 成本主观猜测
- `3 × CONFLICTING`：GAAP vs Non-GAAP 净利口径差、批发交付 vs 上牌上险量冲突、官方自测 vs 第三方盲测跑分对立
- `2 × UNSUPPORTED`：最高检与外交部辟谣引渡假新闻、联合国取消一票否决权假传言
- `1 × NOT_ASSESSABLE`：私人非公开行程与私下讨论

