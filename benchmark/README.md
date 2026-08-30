# 📊 AI Claim Verifier Benchmark Suite

> **面向事实核验规则引擎、证据锚定与端到端状态判定的分层自动化评测基准**

---

## 🎯 三层评测体系架构 (Three-Tier Benchmark Taxonomy)

本评测体系严格分为三层，拒绝将纯规则回归混淆为真实世界能力，保障评测科学性与可复现性：

1. **第一层：合成规则引擎边界回归评测 (Synthetic Rule Regression Benchmark)**
   - **目标**：验证 6 级证据状态转移（SUFFICIENT / STRONG / INSUFFICIENT / CONFLICTING / UNSUPPORTED / NOT_ASSESSABLE）、独立信源去重与时空/数量冲突门禁在极端边界条件下的确定性逻辑。
   - **测试套件**：`backend/tests/test_verdict_boundaries.py` (18 passed)
   - **运行命令**：`pytest backend/tests/test_verdict_boundaries.py -v`

2. **第二层：冻结真实网页快照端到端评测与消融研究 (Frozen Real-Factual Snapshot E2E Benchmark & Ablation Study)**
   - **目标**：在 20 个对抗性真实长篇网页快照上，验证「抽取 → 逐字引文锚定 → 极性仲裁 → 血缘去重 → 确定性裁决」完整链路。
   - **测试目录**：`benchmark/real_factual/`
   - **运行命令**：`python benchmark/real_factual/run_phase_5e_ablations.py --mode openai --run all`

3. **第三层：实时网络端到端评测基准 (Live Real-Web E2E Benchmark)**
   - **目标**：评估结合实时搜索引擎（Search/Retrieval）与动态爬虫抓取时的全自动端到端核验能力，支持 `--live` 在线抓取与 `--cached` 确定性快照回放双重模式。
   - **测试目录**：`benchmark/real_web/`
   - **运行命令**：`python benchmark/real_web/run_real_web_benchmark.py --mode cached`

---

## 📈 官方真实基准指标 (Phase 5D / Phase 5E Control Results)

在 20 个冻结真实长篇网页快照（包含时间线更替、同源转载回音壁、口径差异、侧边栏噪声等对抗陷阱）上，全组件生产级系统的实测数据如下：

| 评测维度 | 定义与说明 | 样本数 | 实测结果 |
| :--- | :--- | :---: | :---: |
| **EvidenceState 准确率 (Accuracy)** | 预测证据状态与人工黄金标签（Gold）完全一致 | 20 | **95.0% (19/20)** |
| **过度断言率 (Overclaim Rate - 核心风控)** | 弱证据或不实主张误判为强证实状态（严禁发生） | 20 | **0.0% (0/20)** |
| **保守漏判率 (Conservative Miss Rate)** | 充分证实的真实主张被错误降级为不足或反驳 | 20 | **0.0% (0/20)** |
| **逐字引文精确锚定率 (Quote Grounding)** | 提取引文在原始源文档中实现 100% 字符级精准锚定 | 20 | **100.0% (20/20)** |
| **主张抽取成功率 (Extraction Rate)** | 成功提取原子主张且未发生格式/解析崩溃 | 20 | **100.0% (20/20)** |
| **基础设施故障数 (Infra Failures)** | 评测过程因超时/连接中断崩溃的用例数 | 20 | **0 / 20** |

> [!NOTE]
> **偏差案例说明 (`p5d-11`)**：在苹果公司库克离职谣言案中，系统预测为 `CONFLICTING`，人工真值为 `UNSUPPORTED`。此偏差属于模型状态分类偏差（`MODEL FAILURE / SAFE`），未造成虚假证实（Overclaim）。

---

## 🧩 官方混淆矩阵 (Official Phase 5D/5E Confusion Matrix)

```text
PRED \ GOLD    SUFFICIENT    UNSUPPORTED    CONFLICTING    INSUFFICIENT
SUFFICIENT          4              0              0              0
UNSUPPORTED         0             14              0              0
CONFLICTING         0              1              0              0   <-- p5d-11 (Safe Rejection)
INSUFFICIENT        0              0              0              1
```

---

## 🌐 第三层 Real-Web E2E 实测指标与跨模型横向矩阵 (Cross-Model Evaluation)

在覆盖科技、财经、生物医疗、谣言网络与私密事实的 20 个 Real-Web 真实用例集上，评测结果全景如下：

### 1. 跨模型全景实证矩阵 (Cross-Model Empirical Matrix)

| 实验组别 | 运行模式 | Accuracy (准确率) | **Overclaim Rate (观测过度断言率)** | Conservative Miss (保守未命中) | Quote Grounding (逐字引文落地率) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Mock LLM** | `CACHED` | **100.0% (20/20)** | **0.0% (0/20)** | 0.0% | 100.0% (Exact) |
| **Mock LLM** | `LIVE` | **80.0% (16/20)** | **0.0% (0/20)** | 20.0% | 100.0% (Exact) |
| **SenseNova (`sensenova-6.8-flash-lite`)** | `CACHED` | **85.0% (17/20)** | **0.0% (0/20)** | 15.0% (3/20) | **100.0% (89/89 EXACT)** |
| **SenseNova (`sensenova-6.8-flash-lite`)** | `LIVE` | **65.0% (13/20)** | **0.0% (0/20)** | 35.0% (7/20) | **90.8% (69/76 Grounded)** |
| **DeepSeek (`deepseek-v4-flash`)** | `CACHED` | **80.0% (16/20)** | **0.0% (0/20)** | 20.0% (4/20) | **100.0% (57/57 EXACT)** |

> [!IMPORTANT]
> **方法学与学术边界声明 (Methodological Boundary)**：
> 在冻结基准测试的 40 次真实大模型-案例评测（SenseNova 20 案 + DeepSeek 20 案）中，系统观测到 **0.0% 的 Overclaim Rate**，共 **146 条引文实现 100% 逐字 EXACT 物理定位（0 条幻觉穿透）**。此实证结果表明确定性规则引擎与 True Raw-Text 定位层在基准分布下具备跨模型的稳健安全防御能力，但不构成对任意输入分布的形式化数学保证。

### 2. 双模型逐样例配对特征 (SenseNova vs DeepSeek)

* **共同正确 (Shared Success)**: **15 / 20 (75.0%)**，覆盖常规事实、单源谣言隔离、官方辟谣与隐私边界。
* **仅 SenseNova 正确**: **2 / 20 (10.0%)**（`rw-04` 达成双源强证实；`rw-13` 提取正反双向临床数据）。
* **仅 DeepSeek 正确**: **1 / 20 (5.0%)**（`rw-02` 成功连接多规格价格）。
* **共同挑战 (Shared Miss)**: **2 / 20 (10.0%)**（`rw-11` GAAP vs Non-GAAP；`rw-14` 辟谣 vs 传闻，均保守判定为 `UNSUPPORTED` / `INSUFFICIENT`）。
* **模型差异的发生位置**：差异主要集中于高阶证据整合、多属性关联与复杂冲突解释，而非引文伪造或安全违规。

---

## 🔬 Phase 5E 单组件控制变量消融结论 (Component Ablation Study)

在固定测试用例、固定模型、Prompt、Schema、温度与评测规则下，单组件消融实验提供了受控的实证证据：

| 实验组别 | 组件干预 | 准确率 | Overclaim 率 | Miss 率 | 核心因果机制 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Control (Full)** | 全生产组件开启 | **95.0%** | **0.0%** | **0.0%** | 官方基准对照组 |
| **Ablation A** | 关闭出处血缘推导 | **90.0%** | **5.0%** 🚨 | **0.0%** | **防止转载放大**：`p5d-05` 3 篇转载误判为 3 独立信源，重现 Overclaim |
| **Ablation B** | 关闭语义极性仲裁 | **10.0%** 📉 | **0.0%** | **15.0%** | **语义方向理解**：死板字符匹配无法理解转述，18 案退化为保守拒认 |
| **Ablation C** | 关闭动态聚焦窗口 | **95.0%** | **0.0%** | **5.0%** ⚠️ | **长文档可见性**：`p5d-06` 尾部证据被 16k 前缀截断，产生截断漏判 |

---

## 📁 评测数据与执行入口

- `benchmark/real_factual/dataset_p5d_20.jsonl`：20 个冻结真实网页事实核验黄金测试集
- `benchmark/real_factual/sources/`：20 组真实长网页 HTML/Text 快照
- `benchmark/real_factual/results/`：已归档固化的 Control 与 Ablation A/B/C JSON 实验记录
- `benchmark/real_factual/run_phase_5e_ablations.py`：消融实验与基准评测统一自动化入口
- `benchmark/real_web/`：20 案 Live Real-Web E2E 评测套件
  - `benchmark/real_web/claims.jsonl`：20 案主张列表
  - `benchmark/real_web/gold_annotations.jsonl`：6 级黄金标签与判定理据
  - `benchmark/real_web/sources/`：`rw-01` 至 `rw-17` 真实网页 HTML/Text 快照与元数据
  - `benchmark/real_web/DATASET_SPEC.md`：详细数据集规范与案例目录
  - `benchmark/real_web/run_real_web_benchmark.py`：Real-Web E2E 执行脚本与混淆矩阵生成器
  - `benchmark/real_web/evaluation/cross_model_analysis.md`：SenseNova vs DeepSeek 配对交叉评测报告
  - `benchmark/real_web/evaluation/results_summary.md`：最新评测结果与失误归因报告

