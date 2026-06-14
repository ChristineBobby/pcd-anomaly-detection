# P7-A 多模板与配准置信度设计

撰写日期：2026-06-14

文档定位：本文件是 P7-A 的执行依据，承接 `P7_innovation_research_roadmap.md`、`SOP_P7_innovation_workflow.md` 和 `P7_code_framework_and_dependency_preresearch.md`。目标是在进入训练型 DSDF 前，先用低风险 non-training 模块验证 `cap3` 的 template mismatch 是否能被多模板与 registration confidence 解释或缓解。

<!-- TOC START -->
## 目录

- [1. 背景与问题](#1-背景与问题)
- [2. P7-A 目标](#2-p7-a-目标)
- [3. 输入与输出](#3-输入与输出)
- [4. 代码框架](#4-代码框架)
- [5. 核心接口](#5-核心接口)
- [6. 指标定义](#6-指标定义)
- [7. 实验流程](#7-实验流程)
- [8. 测试计划](#8-测试计划)
- [9. 产物规范](#9-产物规范)
- [10. Go/No-Go 规则](#10-gono-go-规则)
<!-- TOC END -->

## 1. 背景与问题

P6 已将 `cap3` 收口为 registration/template false positive：

- `cap3_positive9/7/10` 是 positive 样本，但 PASDF object score 高。
- 高 PASDF 分数区域与 template residual 高分区域高度重叠。
- 只调 top-k ratio 不能修复 object boundary。

因此 P7-A 先不训练新模型，而是回答：

> 多个 normal template 能否更稳定地解释正常形态差异，并用 registration confidence 把 template mismatch 从真实 anomaly 中区分出来？

## 2. P7-A 目标

最低目标：

- 建立可复用 `src/pcdad/prototypes/` 模块。
- 对 `cap3/tap1/helmet1/ashtray0` 输出多模板 assignment 与 registration confidence。
- 重点检查 `cap3_positive9/7/10` 与 `cap3_hole0/hole1/broken2/broken3`。

理想目标：

- `cap3_positive9/7/10` 在 multi-template top-1 residual 或 confidence 上显著低于单模板 residual。
- `cap3` positive false-positive 样本的 high PASDF/high residual overlap 被显式标记为 template mismatch risk。

## 3. 输入与输出

输入：

```text
experiments/P5_pasdf_scores/representative/<class>/points/*.npz
third_party/PASDF/data/ShapeNetAD/<class>/<class>_template*.obj
data/Anomaly-ShapeNet-v2/dataset/16384/<class>/train/<class>_template*.pcd
```

模板模式：

- `pasdf_obj`：使用 PASDF 官方 OBJ template，主要用于保持与 P3/P5/P6 的单模板口径一致。
- `train_pcd`：使用 Anomaly-ShapeNet 16384 train split 中的 4 个 normal PCD templates，作为 P7-A 真多模板实验的主口径。

输出：

```text
experiments/P7_A_multitemplate/four_class_train_pcd/
  config.yaml
  git_hash.txt
  template_assignments.csv
  per_sample_scores.csv
  failure_toplist.csv
  README.md
```

## 4. 代码框架

新增：

```text
src/pcdad/prototypes/
  __init__.py
  template_bank.py
  registration_confidence.py

scripts/
  run_p7_multitemplate.py

tests/
  test_template_bank.py
  test_registration_confidence.py
  test_run_p7_multitemplate_cli.py
```

职责：

- `template_bank.py`：加载/表示 template bank；对一个 sample 计算每个模板 residual summary；按 residual/confidence 排序。
- `registration_confidence.py`：把 residual、PASDF/residual top-k overlap、assignment entropy 等转成 0-1 confidence 和 risk reason。
- `run_p7_multitemplate.py`：薄 CLI，负责路径解析、批量样本枚举、CSV/README 输出。

## 5. 核心接口

```python
@dataclass(frozen=True)
class TemplatePrototype:
    class_name: str
    template_id: str
    points: np.ndarray
    source_path: Path | None = None
```

```python
@dataclass(frozen=True)
class TemplateAssignment:
    class_name: str
    sample_id: str
    template_id: str
    rank: int
    nn_mean: float
    nn_p95: float
    nn_topk_mean: float
    residual_overlap: float | None
    bbox_ratio: float
    pair_ratio: float
    assignment_entropy: float
    registration_confidence: float
    risk_reason: str
```

```python
def build_template_assignments(
    *,
    class_name: str,
    sample_id: str,
    sample_points: np.ndarray,
    templates: Sequence[TemplatePrototype],
    pasdf_scores: np.ndarray | None,
    top_ratio: float,
) -> tuple[TemplateAssignment, ...]:
    ...
```

```python
def registration_confidence_from_features(
    *,
    nn_topk_mean: float,
    assignment_entropy: float,
    residual_overlap: float | None,
    bbox_ratio: float,
    pair_ratio: float,
    config: RegistrationConfidenceConfig,
) -> RegistrationConfidenceResult:
    ...
```

## 6. 指标定义

| 指标 | 定义 | 用途 |
|---|---|---|
| `nn_mean` | sample 到 template 最近邻距离均值 | 全局 residual |
| `nn_p95` | 最近邻距离 95 分位 | 局部高 residual |
| `nn_topk_mean` | 最近邻距离 top-k 均值 | object-level template residual |
| `residual_overlap` | PASDF top-k 与 residual top-k 的交集比例 | 判断 PASDF 高分是否来自 template mismatch |
| `bbox_ratio` | residual top-k 点 bbox diagonal / 全样本 bbox diagonal | 高 residual 是否局部集中 |
| `pair_ratio` | residual top-k 点 mean pair distance / 全样本 bbox diagonal | 高 residual 区域是否集中 |
| `assignment_entropy` | 多模板 soft score 分布熵，归一化到 0-1 | 多模板解释不确定性 |
| `registration_confidence` | 0-1，越高越可信 | 后续 calibration 特征 |
| `top1_top2_margin` | top-2 template residual - top-1 template residual | 判断 template selection 是否稳定 |
| `top1_top2_relative_margin` | `top1_top2_margin / top1_nn_topk_mean` | 跨类比较 template selection 间隔 |

## 7. 实验流程

1. 先对合成小数组写单测，确保排序、entropy、overlap、confidence 可解释。
2. 对 `cap3` 运行真实 smoke，样本固定：

```text
cap3_positive9 cap3_positive7 cap3_positive10
cap3_hole0 cap3_hole1 cap3_broken2 cap3_broken3
```

3. 扩到四类：

```text
cap3 tap1 helmet1 ashtray0
```

4. 输出 stage record：

```text
docs/document/stage_record/YYYY-MM-DD_p7_a_multitemplate_registration_summary.md
docs/document/stage_record/YYYY-MM-DD_p7_a_multitemplate_registration_summary.csv
```

5. 若 `train_pcd` 多模板没有压低 `cap3_positive9/7/10`，不要继续无约束增加模板数量，应转向 explicit registration、positive-aware calibration 或训练型 discriminative SDF。

## 8. 测试计划

必须先写失败测试：

- `test_build_template_assignments_ranks_closer_template_first`
- `test_build_template_assignments_reports_pasdf_residual_overlap`
- `test_assignment_entropy_is_zero_for_single_template`
- `test_registration_confidence_decreases_for_high_overlap_and_entropy`
- `test_registration_confidence_rejects_negative_features`
- `test_run_p7_multitemplate_cli_dry_run_writes_expected_paths`

## 9. 产物规范

CSV 字段：

```text
class_name,sample_id,label,point_count,gt_point_count,pasdf_object_score,
template_id,rank,nn_mean,nn_p95,nn_topk_mean,residual_overlap,
bbox_ratio,pair_ratio,assignment_entropy,registration_confidence,risk_reason
```

`per_sample_scores.csv` 额外包含：

```text
top2_nn_topk_mean,top1_top2_margin,top1_top2_relative_margin
```

README 必须包含：

- 命令。
- git hash。
- 输入路径。
- 样本数。
- top false positive 样本。
- go/no-go 结论。

## 10. Go/No-Go 规则

Go：

- `cap3_positive9/7/10` 的 risk reason 能稳定标记 template mismatch。
- 或 multi-template top-1 明显降低 positive residual，同时不压低 anomaly。
- 或 registration confidence 能成为 P7-B calibration 的有效输入特征。

No-Go：

- 多模板 assignment 不稳定。
- positive 与 anomaly 的 residual/confidence 分布没有差异。
- 真实 smoke 无法复现 P6 cap3 residual overlap 结论。
