# P7-P11 创新阶段工程 SOP

撰写日期：2026-06-14

文档定位：本文件承接 `SOP_engineering_workflow.md` 与 `P7_innovation_research_roadmap.md`，把 P7 之后的研究创新工作拆成可执行 stage。它回答“从现在开始每个阶段做什么、参考哪些既有文档、产出什么、达到什么效果才进入下一阶段”。

<!-- TOC START -->
## 目录

- [0. 总览](#0-总览)
- [1. 新阶段基本原则](#1-新阶段基本原则)
- [2. 文档引用地图](#2-文档引用地图)
- [3. P7-A Multi-template 与 Registration Confidence](#3-p7-a-multi-template-与-registration-confidence)
  - [P7-A Entry](#p7-a-entry)
  - [P7-A 核心任务](#p7-a-核心任务)
  - [P7-A 推荐开发文档](#p7-a-推荐开发文档)
  - [P7-A 预期效果](#p7-a-预期效果)
  - [P7-A DoD](#p7-a-dod)
- [4. P7-B Positive-aware Calibration](#4-p7-b-positive-aware-calibration)
  - [P7-B Entry](#p7-b-entry)
  - [P7-B 核心任务](#p7-b-核心任务)
  - [P7-B 推荐开发文档](#p7-b-推荐开发文档)
  - [P7-B 预期效果](#p7-b-预期效果)
  - [P7-B DoD](#p7-b-dod)
- [5. P7-C Pseudo Anomaly 与 Discriminative SDF Smoke](#5-p7-c-pseudo-anomaly-与-discriminative-sdf-smoke)
  - [P7-C Entry](#p7-c-entry)
  - [P7-C 核心任务](#p7-c-核心任务)
  - [P7-C 推荐开发文档](#p7-c-推荐开发文档)
  - [P7-C 预期效果](#p7-c-预期效果)
  - [P7-C DoD](#p7-c-dod)
- [6. P8 RA-MT-DSDF 四类集成实验](#6-p8-ra-mt-dsdf-四类集成实验)
  - [P8 Entry](#p8-entry)
  - [P8 核心任务](#p8-核心任务)
  - [P8 推荐开发文档](#p8-推荐开发文档)
  - [P8 预期效果](#p8-预期效果)
  - [P8 DoD](#p8-dod)
- [7. P9 强对照与扩展预研](#7-p9-强对照与扩展预研)
  - [P9 Entry](#p9-entry)
  - [P9 核心任务](#p9-核心任务)
  - [P9 推荐开发文档](#p9-推荐开发文档)
  - [P9 预期效果](#p9-预期效果)
  - [P9 DoD](#p9-dod)
- [8. P10 40 类与跨数据集扩展](#8-p10-40-类与跨数据集扩展)
  - [P10 Entry](#p10-entry)
  - [P10 核心任务](#p10-核心任务)
  - [P10 推荐开发文档](#p10-推荐开发文档)
  - [P10 预期效果](#p10-预期效果)
  - [P10 DoD](#p10-dod)
- [9. P11 创新交付包与论文式报告冻结](#9-p11-创新交付包与论文式报告冻结)
  - [P11 Entry](#p11-entry)
  - [P11 核心任务](#p11-核心任务)
  - [P11 推荐开发文档](#p11-推荐开发文档)
  - [P11 预期效果](#p11-预期效果)
  - [P11 DoD](#p11-dod)
- [10. 每个 stage 的统一产物规范](#10-每个-stage-的统一产物规范)
- [11. 实验命名与 Git 规范](#11-实验命名与-git-规范)
- [12. 算力使用规范](#12-算力使用规范)
- [13. 阶段推进门与止损规则](#13-阶段推进门与止损规则)
- [14. References](#14-references)
<!-- TOC END -->

## 0. 总览

P0-P6 已经完成强基线复现、失败分析和交付证据包。P7 之后的核心目标不是继续补图，而是把 failure evidence 转成可训练、可消融、可复查的新方法。

推荐阶段拆分如下：

| 阶段 | 名称 | 核心产出 | 进入下一阶段的关键判断 |
|---|---|---|---|
| P7-A | Multi-template 与 Registration Confidence | 多模板 assignment、配准置信度、`cap3` false positive 诊断表 | 能解释或压低 `cap3_positive9/7/10` 的 template mismatch |
| P7-B | Positive-aware Calibration | calibration head、boundary margin 表、positive-aware 排序约束 | 不抬高 positive control，至少一类 boundary 改善 |
| P7-C | Pseudo Anomaly 与 Discriminative SDF Smoke | 伪异常生成、margin loss、单类训练 smoke | `helmet1` 或 `tap1` 点级信号增强，且不破坏 control |
| P8 | RA-MT-DSDF 四类集成实验 | `cap3/tap1/helmet1/ashtray0` 四类完整消融 | 至少一个 failure class 有清楚正收益 |
| P9 | 强对照与扩展预研 | PO3AD smoke、PTv3/Reg2Inv/high-res feasibility | 形成外部强对照和扩展路线选择 |
| P10 | 40 类与跨数据集扩展 | 40 类主表、Real3D-AD subset、high-res local rescore | 判断方法是否能作为主贡献写入最终报告 |
| P11 | 创新交付包冻结 | 技术报告、图表、证据索引、可复现实验包 | 可向他人完整交付和审阅 |

## 1. 新阶段基本原则

1. **P7 之后所有工作都要围绕 P7 roadmap**：主线是 RA-MT-DSDF，即 `multi-template prototype bank + registration confidence + discriminative SDF + positive-aware calibration`。
2. **先四类 smoke，再 40 类**：四类固定为 `cap3/tap1/helmet1/ashtray0`。`cap3` 是 template false positive 主类，`tap1` 是 soft boundary 主类，`helmet1` 是点级定位弱主类，`ashtray0` 是强 baseline control。
3. **不恢复 naive geometry fusion**：P4/P6 已经证明手工加权 geometry 会抬高 positive control。geometry 只作为诊断特征、伪异常生成依据或局部 refinement，不直接作为无约束 object score。
4. **训练和评估在 Docker/conda 容器内执行**，git pull/commit/push 在宿主机执行。
5. **每个 stage 开始前先写 `tech_arche` 设计文档**，结束后写 `stage_record` 结果记录。文档中文，指标与实验数据必须对得上。
6. **每个实验必须保留 config、git hash、metrics CSV、README 和可视化路径**，否则不能进入报告 claim。

## 2. 文档引用地图

后续写任何开发文档时，优先参考下表。

| 用途 | 必读文档 | 使用方式 |
|---|---|---|
| 会话启动与约束 | `docs/document/SERVER_AGENT_KICKOFF.md` | 新 agent 接手前必须读 |
| 总体工程规范 | `docs/document/SOP_engineering_workflow.md` | Docker/Git/测试/文档规范以此为准 |
| 学术立项背景 | `docs/document/3d_point_cloud_defect_detection_research_plan.md` | 写背景、相关工作、数据集定位时引用 |
| P7 创新路线 | `docs/document/tech_arche/P7_innovation_research_roadmap.md` | P7-P11 的主依据 |
| 代码框架与依赖 | `docs/document/tech_arche/P7_code_framework_and_dependency_preresearch.md` | 新模块、包版本、环境风险依据 |
| P3 baseline | `docs/document/stage_record/2026-06-08_p0_p3_stage_check.md` | 固定 PASDF baseline 指标 |
| P4 负结果 | `docs/document/stage_record/2026-06-09_p4_geometry_closure.md` | 避免重复 naive geometry |
| P5 case study | `docs/document/report/2026-06-13_p5_targeted_case_study_report.md` | 复用 cap3/tap1 图与解释 |
| P6 closure | `docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md` | failure mode 与下一步依据 |
| 交付证据 | `docs/document/stage_record/2026-06-14_p6_delivery_evidence_pack.md` | 复用证据索引格式 |

## 3. P7-A Multi-template 与 Registration Confidence

### P7-A Entry

- P7 roadmap 已审批。
- PASDF baseline 产物存在：`experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv`。
- P5 per-point score 存在：`experiments/P5_pasdf_scores/representative`。
- P6 failure closure 已确认：`cap3` 按 registration/template false positive 收口。

### P7-A 核心任务

1. 构建每类 normal template bank，不再默认单一 `template0`。
2. 对 `cap3/tap1/helmet1/ashtray0` 的测试样本计算多模板 residual。
3. 输出 template assignment、top-1/top-2 margin、assignment entropy、residual overlap、registration confidence。
4. 对 `cap3_positive9/7/10` 与 `cap3_hole0/hole1/broken2/broken3` 做对照。
5. 判断 false positive 是单模板错位、类别形态多峰，还是 PASDF SDF score 本身过敏。

### P7-A 推荐开发文档

阶段开始前创建：

```text
docs/document/tech_arche/P7_A_template_bank_and_registration_confidence_plan.md
```

阶段完成后创建：

```text
docs/document/stage_record/YYYY-MM-DD_p7_a_multitemplate_registration_summary.md
docs/document/stage_record/YYYY-MM-DD_p7_a_multitemplate_registration_summary.csv
```

### P7-A 预期效果

- 最低预期：能用数值解释 `cap3_positive9/7/10` 的高分是否来自 template mismatch。
- 理想预期：multi-template top-1 selection 后，`cap3_positive9/7/10` object score 或 residual confidence 明显下降，同时真实 anomaly 样本不被同步压低。
- 若没有改善，也要形成有效结论：说明 `cap3` 需要训练型 discriminative SDF，而不是只换模板。

### P7-A DoD

- 新增 `src/pcdad/prototypes/` 模块和对应单测。
- `cap3/tap1/helmet1/ashtray0` 四类都有 per-sample CSV。
- `cap3_positive9/7/10` 有单独表格和图。
- `git diff --check`、相关 pytest 通过。
- stage record 写清楚是否进入 P7-B。

## 4. P7-B Positive-aware Calibration

### P7-B Entry

- P7-A 已输出 multi-template features。
- P6 calibration 结论可引用：`cap3` 与 `helmet1` strict boundary failed，`tap1` only soft pass。
- P4/P6 已拒绝 additive geometry fusion。

### P7-B 核心任务

1. 汇总 PASDF score、template residual、registration confidence、assignment entropy、bbox ratio、pair ratio 等特征。
2. 训练轻量 calibration head。优先使用 scikit-learn 的 `LogisticRegression`、`IsotonicRegression` 或简单线性/温度缩放，先不引入复杂深度网络。
3. calibration 的选择标准必须 positive-aware：不能只看 anomaly 均值提升，必须看 `max positive - min anomaly` margin。
4. 对 `cap3/tap1/helmet1/ashtray0` 输出 calibrated score 与 baseline score 对照。

### P7-B 推荐开发文档

阶段开始前创建：

```text
docs/document/tech_arche/P7_B_positive_aware_calibration_plan.md
```

阶段完成后创建：

```text
docs/document/stage_record/YYYY-MM-DD_p7_b_positive_calibration_summary.md
docs/document/stage_record/YYYY-MM-DD_p7_b_positive_calibration_summary.csv
```

### P7-B 预期效果

- 最低预期：不会抬高 positive control，能给出 failure class 的 boundary margin 变化。
- 理想预期：`cap3` 或 `tap1` 至少一个类别由 failed/soft pass 变成 strict pass。
- 若 calibration 无改善，也应产出“仅靠 object-level 后处理不足”的证据，为 P7-C 训练型模块提供依据。

### P7-B DoD

- 新增 `src/pcdad/calibration/positive_aware.py` 和单测。
- 输出 per-class AUROC、boundary margin、false positive top list。
- 对比至少三组：PASDF baseline、multi-template score、calibrated score。
- 文档明确记录 calibration 是否使用了测试标签，避免不严谨调参。

## 5. P7-C Pseudo Anomaly 与 Discriminative SDF Smoke

### P7-C Entry

- P7-A/P7-B 已完成，知道 non-training 方法的上限。
- 已确认不直接重做 DLF-3AD 全文，而是把 pseudo anomaly + margin loss 思路并入 PASDF/SDF 路线。
- 至少 1 张 GPU 可用，建议 4 类并行时使用 4 张 GPU。

### P7-C 核心任务

1. 设计 `PseudoAnomalySpec`，支持 normal-direction perturbation、patch cut/hole/broken、curvature-aware perturbation、registration jitter positive control。
2. 先生成可视化和统计，不直接训练：检查伪异常是否像真实缺陷，而不是无意义噪声。
3. 实现最小 discriminative SDF loss：normal surface SDF 接近 0，pseudo anomaly SDF residual 高于 margin。
4. 先做单类 smoke：建议从 `helmet1` 或 `tap1` 开始，另用 `ashtray0` 做 control。
5. 输出训练曲线、object/pixel AUROC、weak localization count。

### P7-C 推荐开发文档

阶段开始前创建：

```text
docs/document/tech_arche/P7_C_pseudo_anomaly_discriminative_sdf_plan.md
```

阶段完成后创建：

```text
docs/document/stage_record/YYYY-MM-DD_p7_c_discriminative_sdf_smoke_summary.md
docs/document/stage_record/YYYY-MM-DD_p7_c_discriminative_sdf_smoke_summary.csv
```

### P7-C 预期效果

- 最低预期：伪异常生成可复现、训练可跑通、指标不崩。
- 理想预期：`helmet1` weak localization count 下降，或 `tap1` GT/background gap 增大。
- 若 SDF 训练不稳定，回退到 P7-B calibration 作为主线，并把 P7-C 作为负结果记录。

### P7-C DoD

- 新增 `src/pcdad/training/pseudo_anomaly.py`、`src/pcdad/training/discriminative_sdf.py` 和单测。
- 单类 smoke 有完整 config、git hash、metrics、README。
- 训练命令和环境写入 stage record。
- 不使用未记录的手工调参结果作为报告 claim。

## 6. P8 RA-MT-DSDF 四类集成实验

### P8 Entry

- P7-A/P7-B/P7-C 中至少两个阶段产出有效结果。
- 已确认四类 smoke 的 config 和输入产物稳定。
- 代码单测覆盖 template bank、calibration、pseudo anomaly、metrics。

### P8 核心任务

1. 集成 RA-MT-DSDF pipeline。
2. 固定四类实验矩阵：PASDF baseline、multi-template、calibration、discriminative SDF、full。
3. 输出 object AUROC、pixel AUROC、AUPR、boundary margin、weak localization count、false positive top list。
4. 生成与 P5/P6 可对比的 heatmap 和 overlay。

### P8 推荐开发文档

阶段开始前创建：

```text
docs/document/tech_arche/P8_ra_mt_dsdf_four_class_integration_plan.md
```

阶段完成后创建：

```text
docs/document/stage_record/YYYY-MM-DD_p8_ra_mt_dsdf_four_class_summary.md
docs/document/stage_record/YYYY-MM-DD_p8_ra_mt_dsdf_four_class_summary.csv
docs/document/report/YYYY-MM-DD_p8_ra_mt_dsdf_four_class_report.md
```

### P8 预期效果

- 最低预期：四类全量 smoke 跑通，能判断每个模块对每类 failure mode 的作用。
- 理想预期：至少一个 failure class 明确超过 PASDF baseline，且 `ashtray0` control 不退化。
- 若 full 方法均值提升但 positive false positive 增加，不算成功。

### P8 DoD

- 四类每个方法都有同口径 CSV。
- 每个核心 claim 都能追溯到 CSV 或 SVG。
- report 中必须包含失败案例，不只展示成功样本。
- 明确是否进入 P10 40 类扩展。

## 7. P9 强对照与扩展预研

### P9 Entry

- P8 四类集成已有初步结论。
- 当前工作需要回答“我们的改进是否只是 PASDF 特有，还是能与判别式强基线对照”。

### P9 核心任务

1. **PO3AD smoke**：单独环境跑 `cap3/tap1/helmet1/ashtray0`，不污染 PASDF 环境。
2. **PTv3/Pointcept feasibility**：只做环境和 forward smoke，不急着整合。
3. **Reg2Inv/registration-aware feature 对照**：只抽取思想，不直接引入整套训练框架。
4. **High-res local rescore 预研**：从 16k top-k candidate 映射回原始高密度点云局部 patch。

### P9 推荐开发文档

阶段开始前创建：

```text
docs/document/tech_arche/P9_po3ad_ptv3_highres_feasibility_plan.md
```

阶段完成后创建：

```text
docs/document/stage_record/YYYY-MM-DD_p9_external_baseline_feasibility_summary.md
```

### P9 预期效果

- 最低预期：PO3AD 官方环境风险和可跑性有明确记录。
- 理想预期：PO3AD 在四类上给出有效对照；high-res local rescore 产出至少 3 个样本图。
- 如果 PO3AD/MinkowskiEngine 环境阻塞半天以上，不让它阻塞主线。

### P9 DoD

- PO3AD 是否可运行有日志和结论。
- 任何新增重依赖都必须在单独 conda env 内验证。
- 对每个扩展给出 go/no-go 结论。

## 8. P10 40 类与跨数据集扩展

### P10 Entry

- P8 四类结果至少有一个强正收益，或 P7-P8 形成了值得报告的有界负结果。
- 代码可通过单测和固定命令复跑。

### P10 核心任务

1. 将 RA-MT-DSDF 中有效模块扩到 Anomaly-ShapeNet 40 类。
2. 选 Real3D-AD 2-4 类做真实高分辨率泛化验证。
3. 若 P9 high-res rescore 成立，补充课程高密度原始点云上的局部 refinement。
4. 统一主表、消融表和失败分析表。

### P10 推荐开发文档

阶段开始前创建：

```text
docs/document/tech_arche/P10_40class_real3d_highres_extension_plan.md
```

阶段完成后创建：

```text
docs/document/stage_record/YYYY-MM-DD_p10_40class_extension_summary.md
docs/document/stage_record/YYYY-MM-DD_p10_real3d_subset_summary.md
docs/document/report/YYYY-MM-DD_p10_extension_report.md
```

### P10 预期效果

- 最低预期：四类有效结论在 40 类上不出现系统性崩坏。
- 理想预期：40 类 mean object/pixel AUROC 至少一个指标超过 PASDF baseline，或 failure class 明确修复。
- 若 40 类均值不升，但特定 failure mode 修复明显，也可以作为 targeted robustness contribution。

### P10 DoD

- 40 类结果表有完整类列表。
- Real3D-AD subset 的预处理、类别、点数和评估口径写清楚。
- 任何“提升”都必须给出 baseline、ours、delta 和随机/重复实验说明。

## 9. P11 创新交付包与论文式报告冻结

### P11 Entry

- P8/P10 至少一个阶段形成可报告结论。
- 所有关键实验有 stage record、CSV、图和复现命令。

### P11 核心任务

1. 整理创新技术报告：问题定义、方法、实验、消融、失败分析、局限。
2. 整理图文并茂的 delivery pack，所有图片使用相对路径。
3. 生成 evidence index，列出每个 claim 的来源。
4. 冻结最终 commit/tag。

### P11 推荐开发文档

阶段开始前创建：

```text
docs/document/tech_arche/P11_innovation_delivery_pack_plan.md
```

阶段完成后创建：

```text
docs/document/delivery_pack/YYYY-MM-DD_p11_innovation_delivery_pack/
docs/document/delivery_pack/YYYY-MM-DD_p11_innovation_delivery_pack.zip
docs/document/stage_record/YYYY-MM-DD_p11_innovation_delivery_evidence_pack.md
```

### P11 预期效果

- 交付对象可以不读全仓库，只看 delivery pack 就理解贡献、结果和局限。
- 报告明确区分：已验证正结果、负结果、工程可行性、未来工作。

### P11 DoD

- delivery pack 中图片相对路径可打开。
- README、MANIFEST、evidence index 完整。
- 最终 commit/tag 已推送远端。

## 10. 每个 stage 的统一产物规范

每个 stage 的实验目录必须包含：

```text
experiments/<stage>_<method>/<scope>/<run_id>/
  README.md
  config.yaml
  git_hash.txt
  metrics.csv
  per_sample_scores.csv
  failure_toplist.csv
  svg/
```

每个 stage 的文档至少包含：

- 目标与入口条件。
- 参考文档。
- 命令与环境。
- 输入产物。
- 输出产物。
- 指标表。
- 失败样本。
- go/no-go 结论。

## 11. 实验命名与 Git 规范

实验命名：

```text
P7_A_multitemplate_<class_or_scope>
P7_B_calibration_<class_or_scope>
P7_C_dsdf_<class_or_scope>
P8_ra_mt_dsdf_four_class
P10_ra_mt_dsdf_40class
```

提交规范：

```text
docs(sop): add p7 innovation workflow
feat(prototypes): add multi-template assignment
feat(calibration): add positive-aware calibration
feat(training): add pseudo anomaly generation
docs(results): add p7 multitemplate summary
```

git 边界：

- 宿主机执行 `git pull/commit/push`。
- Docker 内执行训练、评估、测试。
- 大型实验产物不进 git，只提交 summary、CSV、小图和交付包。

## 12. 算力使用规范

8 张 RTX 4090 48G 的建议分配：

| GPU | 优先任务 |
|---:|---|
| 0 | `cap3` multi-template/calibration |
| 1 | `tap1` calibration/pseudo anomaly |
| 2 | `helmet1` discriminative SDF |
| 3 | `ashtray0` control |
| 4 | hyperparameter sweep |
| 5 | PO3AD smoke |
| 6 | Real3D-AD/high-res local rescore |
| 7 | visualization/evaluation/retry |

规则：

- smoke 前不跑大规模 sweep。
- 每轮最多改变 2-3 个变量。
- GPU 训练命令必须写入 README。
- 失败实验也要保留摘要，避免重复踩坑。

## 13. 阶段推进门与止损规则

推进门：

| 条件 | 说明 |
|---|---|
| 指标同口径 | baseline 和 ours 使用同一数据、同一 sample list、同一 metric |
| positive-aware | 不能只看 anomaly 均值，必须看 positive boundary |
| control 不崩 | `ashtray0` 不能明显退化 |
| 可复现 | 同一命令、同一 config、同一 git hash 可复跑 |
| 文档闭环 | stage record 与 CSV/SVG 对得上 |

止损规则：

| 风险 | 止损条件 | 动作 |
|---|---|---|
| multi-template 无收益 | 四类均不能解释或改善 boundary | 转向 calibration/DSDF |
| calibration 过拟合 | positive 被压低但 anomaly 同步被压低 | 降低特征复杂度 |
| DSDF 训练不稳 | 单类 3 次运行 ranking 不稳定 | 暂停训练，回到 non-training 模块 |
| PO3AD 环境阻塞 | 半天无法 import/train smoke | 记录失败，不阻塞主线 |
| 40 类扩展退化 | 均值下降且 failure 未修复 | 定位为 targeted robustness module |

## 14. References

1. P7 roadmap: `docs/document/tech_arche/P7_innovation_research_roadmap.md`
2. P6 failure closure: `docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md`
3. P6 delivery evidence pack: `docs/document/stage_record/2026-06-14_p6_delivery_evidence_pack.md`
4. P3 baseline record: `docs/document/stage_record/2026-06-08_p0_p3_stage_check.md`
5. P4 geometry closure: `docs/document/stage_record/2026-06-09_p4_geometry_closure.md`
6. P5 targeted report: `docs/document/report/2026-06-13_p5_targeted_case_study_report.md`
