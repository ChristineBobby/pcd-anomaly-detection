# P7-B Positive-aware Calibration 设计文档

撰写日期：2026-06-22

文档定位：本文件是 P7-B 的执行依据，承接 `SOP_P7_innovation_workflow.md`、`P7_innovation_research_roadmap.md`、P6 failure closure 和 P7-A multi-template 结果。目标是在进入 P7-C 训练型 DSDF 前，先用低风险、可解释、可复查的 calibration layer 判断 non-training 后处理还能修复多少 false positive 与 object boundary 问题。

<!-- TOC START -->
## 目录

- [1. 阶段定位](#1-阶段定位)
- [2. 学术与工程依据](#2-学术与工程依据)
- [3. 当前输入证据](#3-当前输入证据)
- [4. P7-B 目标与非目标](#4-p7-b-目标与非目标)
- [5. 方案总览](#5-方案总览)
- [6. 数据协议与跨数据集预留](#6-数据协议与跨数据集预留)
- [7. 代码框架与接口](#7-代码框架与接口)
- [8. Calibration 方法集合](#8-calibration-方法集合)
- [9. Positive-aware 指标](#9-positive-aware-指标)
- [10. 实验矩阵](#10-实验矩阵)
- [11. Docker 与环境](#11-docker-与环境)
- [12. 测试计划](#12-测试计划)
- [13. 产物规范](#13-产物规范)
- [14. Go/No-Go 规则](#14-gono-go-规则)
- [15. 下一步实现顺序](#15-下一步实现顺序)
- [16. References](#16-references)
<!-- TOC END -->

## 1. 阶段定位

P7-A 已证明：train PCD 多模板可以输出 registration/template mismatch 诊断特征，但不能独立修复 `cap3_positive9/7/10`。因此 P7-B 不应继续堆模板数量，也不应恢复 P4/P6 已否定的 additive geometry fusion。

P7-B 的定位是：

> 基于 PASDF object score 与 registration-aware diagnostic features 的 positive-aware calibration layer，用于降低 template mismatch false positive，并量化 non-training 后处理的上限。

这里的 calibration 不是把分数强行变成严格概率，而是把 PASDF 分数、template residual、assignment uncertainty 和 registration confidence 合并成一个可解释的 calibrated anomaly score。评价标准必须 positive-aware：不能只看 anomaly 均值或 AUROC，还必须看 positive control 是否被误抬高。

## 2. 学术与工程依据

### 2.1 概率校准

Guo et al. 在 ICML 2017 指出，现代神经网络即使分类准确，也可能输出 poorly calibrated confidence，并系统评估了 post-processing calibration 方法。该工作支持我们把 calibration 作为独立阶段处理，而不是默认相信 PASDF object score 已经可直接比较。

对 P7-B 的启发：

- calibration 应作为后处理模块，避免侵入 PASDF 主干。
- sigmoid/temperature/isotonic 可以作为基线，但不能替代 positive-aware failure analysis。

### 2.2 工业异常检测的 nominal reference

PatchCore 在 CVPR 2022 提出使用 nominal patch-feature memory bank 做工业异常检测，强调正常参照库和局部特征匹配。它与 P7-A 的 template/prototype bank 思路一致：异常分数不应只依赖单个模型输出，还应利用正常参照与不确定性。

对 P7-B 的启发：

- template residual 与 assignment entropy 不能直接当 anomaly score，但可以作为 calibration feature。
- calibration 需要保留 false positive toplist，服务工业检测里的误报分析。

### 2.3 Open-set 与 unknown risk

OpenMax/CVPR 2016 通过额外建模 unknown probability 处理 open-set recognition，核心思想是不要强迫模型对不可靠输入给出闭集高置信结论。P7-A 的 `registration_confidence` 与此相似：当配准或模板解释不可靠时，PASDF object score 的可信度应下降，或至少单独标记。

对 P7-B 的启发：

- `registration_confidence` 不一定直接加权为 anomaly score，也可以作为 gating feature。
- 低 confidence、高 PASDF 分数样本应在 report 中独立呈现。

### 2.4 Real3D-AD 扩展

Real3D-AD 是真实高精度 3D 点云异常检测数据集，OpenReview 官方页面说明其包含 1,254 个高分辨率真实 3D 样本。它比 Anomaly-ShapeNet 更接近工业扫描，也更容易暴露点数、采样密度、配准和局部缺陷尺度问题。

P7-B 不直接要求跑 Real3D-AD，但必须预留跨数据集字段和 adapter 口径。Real3D-AD 正式实验放到 P9/P10：

- P9：数据准备、loader dry-run、2 类 smoke。
- P10：2-4 类正式验证，作为 synthetic-to-real 泛化实验。

## 3. 当前输入证据

### 3.1 P6 failure closure

P6 将三个 failure class 收口为：

| 类别 | Failure mode | 当前判断 |
|---|---|---|
| `cap3` | registration/template false positive | 只调 top-k 或 naive geometry 不能修复 |
| `tap1` | PASDF soft object boundary | additive geometry fusion 被拒绝 |
| `helmet1` | point-level localization weakness / positive boundary confusion | 需要后续点级或训练型模块 |

### 3.2 P7-A multi-template 输出

P7-A 产物：

```text
experiments/P7_A_multitemplate/four_class_train_pcd/
  README.md
  config.yaml
  failure_toplist.csv
  git_hash.txt
  per_sample_scores.csv
  template_assignments.csv
```

`per_sample_scores.csv` 当前字段：

```text
class_name,sample_id,label,point_count,gt_point_count,pasdf_object_score,
template_id,rank,nn_mean,nn_p95,nn_topk_mean,residual_overlap,
bbox_ratio,pair_ratio,assignment_entropy,registration_confidence,
risk_reason,top2_nn_topk_mean,top1_top2_margin,top1_top2_relative_margin
```

关键结论：

- 125 个四类样本均有 top-1 per-sample 记录。
- `cap3_positive9/7` 被标记为 `template_mismatch_risk`。
- `cap3_positive10` 仍有高 entropy 和低 margin，但 residual overlap 为 0，不能和 `positive9/7` 完全归为同一机制。
- `cap3` positive 与 anomaly 的 top-1 residual 均值几乎相同，template residual 不能直接作为 anomaly score。

## 4. P7-B 目标与非目标

### 4.1 目标

最低目标：

- 建立 `src/pcdad/calibration/` 模块。
- 对四类 `cap3/tap1/helmet1/ashtray0` 输出 PASDF baseline、multi-template feature baseline、calibrated score 的同口径对照。
- 报告 per-class AUROC、AUPR、boundary margin、false positive toplist。
- 明确 calibration 是否使用测试标签，避免不严谨 claim。

理想目标：

- `cap3` 或 `tap1` 至少一个类别的 object boundary 改善。
- `cap3_positive9/7/10` 的 calibrated score 排名下降，同时真实 anomaly 不被同步压低。
- `ashtray0` control 不退化。

### 4.2 非目标

- 不训练 PASDF/SDF 主干。
- 不引入深度网络 calibration head。
- 不恢复 additive geometry fusion。
- 不把四类测试标签调参结果包装成严格泛化结果。
- 不在 P7-B 阶段强行接入 Real3D-AD 全流程。

## 5. 方案总览

P7-B 使用三层结构：

1. **Score calibration baselines**
   - PASDF object score 原始分数。
   - single-feature sigmoid calibration。
   - single-feature isotonic calibration。

2. **Feature calibration head**
   - 使用 P7-A 多模板特征训练轻量 logistic calibration。
   - 特征必须少而稳定，优先 5-6 个。

3. **Confidence-gated calibration**
   - 使用 `registration_confidence` 对 PASDF score 的可信度做 gating。
   - 输出 calibrated score 与 risk reason，不隐藏低 confidence 样本。

首轮不做复杂模型选择。若简单方法无法改善 boundary，应记录为 non-training upper-bound 负结果，为 P7-C 提供依据。

## 6. 数据协议与跨数据集预留

### 6.1 统一记录字段

新增统一记录结构时，不绑定 Anomaly-ShapeNet：

```python
@dataclass(frozen=True)
class CalibrationRecord:
    dataset_name: str
    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    pasdf_score: float
    template_score: float
    registration_confidence: float
    assignment_entropy: float
    residual_overlap: float
    top1_top2_margin: float
    calibrated_score: float
    method: str
    split_tag: str
    note: str
```

`dataset_name` 首轮固定为 `anomaly_shapenet_16384`。P9/P10 Real3D-AD adapter 可复用同一字段，设为 `real3d_ad_<subset>`。

### 6.2 标签使用声明

P7-B 有两种运行模式：

| 模式 | 标签使用 | 定位 |
|---|---|---|
| `diagnostic_oracle` | 使用四类 test label 训练/选择 calibration | 诊断上限，不作为泛化 claim |
| `leave_one_class_out` | 按类别留一做校准评估 | 更接近跨类泛化，但样本仍少 |

首轮必须同时输出二者，避免只展示 oracle 结果。

### 6.3 Real3D-AD 预留

Real3D-AD 不进入 P7-B DoD，但 P7-B 的数据结构必须兼容：

- 点数可以远高于 16k。
- GT 可能是点级或局部区域标签，`gt_point_count` 可为 0 或缺失。
- 类别名和 split 不能假设与 Anomaly-ShapeNet 一致。
- Real3D adapter 应只负责把数据转成 unified CSV，不把 calibration 逻辑复制一遍。

## 7. 代码框架与接口

新增：

```text
src/pcdad/calibration/
  __init__.py
  positive_aware.py

scripts/
  train_p7_calibration.py

tests/
  test_positive_aware_calibration.py
  test_train_p7_calibration_cli.py
```

职责：

- `positive_aware.py`：读取/校验记录、构建特征矩阵、计算 calibration score、计算 positive-aware metrics。
- `train_p7_calibration.py`：薄 CLI，负责参数解析、CSV 输入输出、config/git hash/README。
- 测试文件覆盖 metrics、split、gating、CLI dry-run。

核心函数接口：

```python
def load_calibration_records(path: Path, *, dataset_name: str) -> tuple[CalibrationRecord, ...]:
    ...
```

```python
def boundary_margin(records: Sequence[CalibrationRecord], score_field: str) -> BoundaryMargin:
    ...
```

```python
def build_feature_matrix(
    records: Sequence[CalibrationRecord],
    feature_names: Sequence[str],
) -> tuple[np.ndarray, np.ndarray]:
    ...
```

```python
def calibrate_scores(
    records: Sequence[CalibrationRecord],
    method: str,
    feature_names: Sequence[str],
    split_mode: str,
) -> tuple[CalibrationRecord, ...]:
    ...
```

```python
def summarize_calibration(
    records: Sequence[CalibrationRecord],
    score_fields: Sequence[str],
) -> tuple[CalibrationSummary, ...]:
    ...
```

接口原则：

- 纯函数优先。
- `scripts/` 不承载核心逻辑。
- 方法数量少，先可解释再扩展。
- 不为未来 Real3D 写复杂抽象，只保留 `dataset_name` 和统一字段。

## 8. Calibration 方法集合

### 8.1 Baseline methods

| 方法 | 输入 | 输出 | 用途 |
|---|---|---|---|
| `pasdf_raw` | `pasdf_object_score` | 原始分数 | 固定 baseline |
| `template_residual` | `nn_topk_mean` | residual 分数 | 验证 P7-A residual 不能独立做 score |
| `confidence_gate` | PASDF score + confidence | gated score | 检查低 confidence 是否能压 false positive |

### 8.2 Learnable lightweight methods

| 方法 | 工具 | 特征 | 风险控制 |
|---|---|---|---|
| `logistic_l2` | `sklearn.linear_model.LogisticRegression` | 5-6 个结构化特征 | L2 正则、class_weight 可选 |
| `isotonic_pasdf` | `sklearn.isotonic.IsotonicRegression` | 仅 PASDF score | 单调校准 baseline |
| `isotonic_gated` | `IsotonicRegression` | confidence-gated PASDF score | 检查单调 score 是否足够 |

首轮特征集合：

```text
pasdf_object_score
nn_topk_mean
top1_top2_margin
assignment_entropy
residual_overlap
registration_confidence
```

可选派生特征：

```text
low_confidence_score = pasdf_object_score * (1 - registration_confidence)
gated_pasdf_score = pasdf_object_score * registration_confidence
```

默认先不加入 `bbox_ratio`、`pair_ratio`，除非基础特征无效。原因是 P7-B 应遵循奥卡姆剃刀，避免用小样本堆特征制造表面改善。

## 9. Positive-aware 指标

每个 class 与 overall 都输出：

| 指标 | 定义 | 作用 |
|---|---|---|
| `object_auroc` | object label 与 score 的 AUROC | 基础排序能力 |
| `object_aupr` | average precision | 类别不均衡时辅助判断 |
| `max_positive_score` | label=0 样本最高分 | false positive 上界 |
| `min_anomaly_score` | label=1 样本最低分 | 最弱 anomaly |
| `boundary_margin` | `min_anomaly_score - max_positive_score` | 大于 0 才 strict pass |
| `false_positive_top1` | positive 中最高分样本 | 直接审查误报 |
| `low_confidence_topk` | 低 confidence 高分样本 | 检查 registration gating 是否起效 |

注意：历史文档中有时使用 `max positive - min anomaly` 表示 failed margin；P7-B 输出 CSV 统一使用 `boundary_margin = min_anomaly - max_positive`，数值越大越好。README 中同时解释，避免口径混淆。

## 10. 实验矩阵

### 10.1 四类主实验

输入：

```text
experiments/P7_A_multitemplate/four_class_train_pcd/per_sample_scores.csv
```

类别：

```text
cap3 tap1 helmet1 ashtray0
```

方法：

| Method | Split | 目的 |
|---|---|---|
| `pasdf_raw` | none | 原始 PASDF baseline |
| `template_residual` | none | 验证 residual 是否有独立价值 |
| `confidence_gate` | none | 非学习 gating baseline |
| `isotonic_pasdf` | diagnostic_oracle + leave_one_class_out | 单特征单调校准 |
| `logistic_l2` | diagnostic_oracle + leave_one_class_out | 多特征轻量校准 |

### 10.2 重点样本表

必须固定输出：

```text
cap3_positive9
cap3_positive7
cap3_positive10
cap3_hole0
cap3_hole1
cap3_broken2
cap3_broken3
tap1_broken2
tap1_broken3
tap1_hole0
helmet1_concavity1
helmet1_concavity2
helmet1_concavity4
```

### 10.3 Real3D-AD 后续入口

P7-B 文档不要求 Real3D 结果，但预留 P9 命令口径：

```bash
PYTHONPATH=src python scripts/prepare_real3d_subset.py \
  --real3d-root data/Real3D-AD \
  --classes airplane car duck shell \
  --output-csv experiments/P9_real3d_subset/metadata.csv
```

该命令后续 P9 再设计，不在 P7-B 实现。

## 11. Docker 与环境

实验容器：

```text
container name: Anomaly
workspace: /workspace/code_folder/area1/Anomaly
conda env: /workspace/.conda/envs/pasdf
visible GPUs: host GPU1-6 only
```

推荐命令前缀：

```bash
docker exec Anomaly bash -lc 'cd /workspace/code_folder/area1/Anomaly && PYTHONPATH=src /workspace/.conda/envs/pasdf/bin/python ...'
```

环境结论：

- 当前 `pasdf` 环境已有 `scikit-learn 1.5.2`、`numpy 1.23.5`。
- P7-B 不需要新增依赖。
- 若后续 Real3D-AD 或 PO3AD 需要重依赖，应走 P9 独立环境，不污染 `pasdf`。

## 12. 测试计划

先写失败测试，再写实现。

必须覆盖：

- `test_boundary_margin_strict_pass_and_failure`
- `test_build_feature_matrix_uses_requested_features_only`
- `test_confidence_gate_reduces_low_confidence_high_score`
- `test_calibrate_scores_leave_one_class_out_does_not_train_on_heldout_class`
- `test_summarize_calibration_reports_false_positive_top1`
- `test_train_p7_calibration_cli_dry_run_outputs_expected_paths`

回归测试：

- P7-A prototype tests 仍需通过。
- P6 boundary/failure mode 相关 tests 不应被改坏。

## 13. 产物规范

输出目录：

```text
experiments/P7_B_calibration/four_class/
  README.md
  config.yaml
  git_hash.txt
  calibration_records.csv
  metrics.csv
  boundary_margin.csv
  failure_toplist.csv
```

阶段记录：

```text
docs/document/stage_record/YYYY-MM-DD_p7_b_positive_calibration_summary.md
docs/document/stage_record/YYYY-MM-DD_p7_b_positive_calibration_summary.csv
```

README 必须写清：

- 输入 CSV。
- 使用的 split mode。
- 是否使用 label 训练 calibration。
- 每个方法的 boundary margin。
- `cap3_positive9/7/10` 排名是否下降。
- 是否进入 P7-C。

## 14. Go/No-Go 规则

Go：

- 至少一个 failure class 的 `boundary_margin` 明显改善，且 `ashtray0` control 不退化。
- 或 `cap3_positive9/7/10` calibrated score 排名下降，真实 anomaly 不被同步压低。
- 或明确证明 non-training calibration 上限不足，为 P7-C 提供强证据。

No-Go：

- 只有 diagnostic oracle 有改善，leave-one-class-out 完全无效，且无法解释。
- calibration 通过压低所有样本获得表面改善。
- false positive toplist 仍由同一批 positive 样本主导且 confidence gating 不起作用。
- `ashtray0` control 明显退化。

## 15. 下一步实现顺序

1. 新建 `src/pcdad/calibration/positive_aware.py` 和测试。
2. 实现 record loading、boundary margin、feature matrix、confidence gate。
3. 实现 `pasdf_raw`、`template_residual`、`confidence_gate` 三个 non-learning baseline。
4. 实现 `isotonic_pasdf` 与 `logistic_l2`。
5. 新建 `scripts/train_p7_calibration.py`。
6. 在 `Anomaly` 容器内跑四类 P7-B 实验。
7. 写 stage record，commit 并 push。

## 16. References

1. Chuan Guo, Geoff Pleiss, Yu Sun, Kilian Q. Weinberger. **On Calibration of Modern Neural Networks**. ICML 2017 / PMLR. https://proceedings.mlr.press/v70/guo17a.html
2. Karsten Roth, Latha Pemula, Joaquin Zepeda, Bernhard Schölkopf, Thomas Brox, Peter Gehler. **Towards Total Recall in Industrial Anomaly Detection**. CVPR 2022. https://openaccess.thecvf.com/content/CVPR2022/papers/Roth_Towards_Total_Recall_in_Industrial_Anomaly_Detection_CVPR_2022_paper.pdf
3. Abhijit Bendale, Terrance E. Boult. **Towards Open Set Deep Networks**. CVPR 2016. https://www.cv-foundation.org/openaccess/content_cvpr_2016/html/Bendale_Towards_Open_Set_CVPR_2016_paper.html
4. Jiaqi Liu, Guoyang Xie, Ruitao Chen, Xinpeng Li, Jinbao Wang, Yong Liu, Chengjie Wang, Feng Zheng. **Real3D-AD: A Dataset of Point Cloud Anomaly Detection**. NeurIPS 2023 Datasets and Benchmarks. https://openreview.net/forum?id=zGthDp4yYe
5. Real3D-AD official repository. https://github.com/M-3LAB/Real3D-AD
6. scikit-learn User Guide, **Probability calibration**. https://scikit-learn.org/stable/modules/calibration.html
7. scikit-learn API, **LogisticRegression**. https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
8. scikit-learn API, **IsotonicRegression**. https://scikit-learn.org/stable/modules/generated/sklearn.isotonic.IsotonicRegression.html
9. scikit-learn API, **roc_auc_score**. https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html
10. scikit-learn API, **average_precision_score**. https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html
