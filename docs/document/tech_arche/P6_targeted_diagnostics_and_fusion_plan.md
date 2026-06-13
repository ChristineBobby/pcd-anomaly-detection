# P6 Targeted Diagnostics And Fusion 架构与执行计划

撰写日期：2026-06-13

适用阶段：P5 targeted case study 完成后，进入 P6 小范围定量验证

## 目录

- [1. 背景与目标](#1-背景与目标)
- [2. 设计判断](#2-设计判断)
- [3. 输入与输出](#3-输入与输出)
- [4. 代码框架](#4-代码框架)
- [5. 核心接口设计](#5-核心接口设计)
- [6. 实验样本](#6-实验样本)
- [7. 指标口径](#7-指标口径)
- [8. 测试策略](#8-测试策略)
- [9. 执行命令](#9-执行命令)
- [10. 验收标准](#10-验收标准)

## 1. 背景与目标

P5 targeted case study 给出两个明确发现：

1. `cap3_positive9/7/10` 的 template overlay 存在明显 sample/template 局部错位，尤其在帽檐、类似鸭舌的突出结构附近；没有明显尺度问题。
2. `tap1_broken2/broken3/hole0` 的 PASDF score 图整体偏蓝，说明 PASDF 局部响应弱；geometry distance score 图出现更强高分区域，并且更接近可见 GT 点。

因此 P6 不直接做 40 类 full hybrid，而是拆成两个小目标：

- `cap3`：定量诊断 registration/template mismatch，解释 positive false positive。
- `tap1`：做 PASDF + geometry 小范围 fusion prototype，验证 geometry residual 是否能改善局部缺陷响应。

## 2. 设计判断

当前不做 GT-preserving sampling。原因：

- 用户已经完成视觉判读，认为现有图足够支持下一步。
- `tap1` GT 点很少是数据本身特点，当前图的 black outline 虽少但仍能辅助判断。
- 下一步核心是定量 fusion 和 residual 统计，不是继续优化可视化。

当前不扩 40 类。原因：

- `cap3` 和 `tap1` 的失败模式不同。
- `cap3` 的 geometry residual 可能被 registration/template mismatch 放大，直接 fusion 会污染结论。
- `tap1` 的结果支持小范围 fusion，但尚不能证明全类别稳健。

## 3. 输入与输出

### 3.1 输入

PASDF point-score NPZ：

```text
experiments/P5_pasdf_scores/representative/{class}/points/{sample_id}.npz
```

PASDF template OBJ：

```text
third_party/PASDF/data/ShapeNetAD/{class}/{class}_template0.obj
```

已有 P5 case-study 记录：

```text
docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv
docs/document/report/2026-06-13_p5_targeted_case_study_report.md
```

### 3.2 输出

实验产物目录：

```text
experiments/P6_targeted_diagnostics/
```

计划输出：

```text
experiments/P6_targeted_diagnostics/cap3_registration_diagnostics.csv
experiments/P6_targeted_diagnostics/tap1_hybrid_scores.csv
experiments/P6_targeted_diagnostics/tap1_hybrid_scores/{sample_id}_hybrid_comparison.svg
docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.md
docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.csv
```

## 4. 代码框架

### 4.1 `src/pcdad/analysis/pasdf_case_study.py`

复用已有能力：

- `load_pasdf_point_score`
- `load_pasdf_template_points`
- `compute_distance_geometry_scores`

不在该文件继续堆新逻辑，避免 case-study 工具膨胀。

### 4.2 `src/pcdad/analysis/targeted_p6.py`

新增 P6 小范围诊断模块。

职责：

- 计算 sample/template distance residual 统计。
- 计算 PASDF/geometry/hybrid point score。
- 生成稳定 CSV record。
- 渲染中文 Markdown summary。

建议数据结构：

```python
@dataclass(frozen=True)
class RegistrationDiagnosticRecord:
    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    nn_distance_mean: float
    nn_distance_p95: float
    nn_distance_p99: float
    nn_distance_top5_mean: float
    pasdf_object_score: float
```

```python
@dataclass(frozen=True)
class HybridScoreRecord:
    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    pasdf_object_score: float
    geometry_object_score: float
    hybrid_object_score: float
    pasdf_gt_mean: float | None
    pasdf_background_mean: float | None
    geometry_gt_mean: float | None
    geometry_background_mean: float | None
    hybrid_gt_mean: float | None
    hybrid_background_mean: float | None
    svg_path: str | None
```

### 4.3 `src/pcdad/viz/pointcloud.py`

复用已有：

- `write_pointcloud_score_comparison_svg`

新增一个三面板 SVG 可以后续再做，本轮先避免扩大范围。当前用两张并排图：

- PASDF vs geometry：已有。
- PASDF vs hybrid 或 geometry vs hybrid：本轮优先写 PASDF vs hybrid。

### 4.4 `scripts/run_p6_targeted_diagnostics.py`

新增薄 CLI：

```text
--score-root
--template-root
--cap3-samples
--tap1-samples
--tap1-positive-samples
--output-dir
--summary-md
--summary-csv
--alpha
--max-points
--seed
```

CLI 只负责解析参数、调用 `targeted_p6.py`、写文件。

## 5. 核心接口设计

### 5.1 Registration diagnostics

```python
def compute_registration_diagnostic(
    *,
    score_path: Path,
    template_root: Path,
) -> RegistrationDiagnosticRecord:
    ...
```

行为：

- 从 NPZ 读取 aligned points、mask、label、object_score。
- 从 template OBJ 读取 canonical template points。
- 使用 `point_to_template_residuals(..., use_normals=False, use_curvature=False)` 计算 nearest-neighbor distance。
- 记录 mean、p95、p99、top5 mean。

### 5.2 Hybrid score

```python
def compute_hybrid_score(
    *,
    score_path: Path,
    template_root: Path,
    alpha: float,
) -> HybridScoreRecord:
    ...
```

行为：

- PASDF point score 使用 NPZ 中 `point_scores`。
- Geometry point score 使用 distance-only geometry score。
- 两者先分别 robust min-max 到 `[0, 1]`。
- hybrid point score：

```text
hybrid = pasdf_norm + alpha * geometry_norm
```

- hybrid object score 使用 top 5% mean。
- 输出 PASDF/geometry/hybrid 的 GT mean 与 background mean。

### 5.3 Markdown summary

```python
def render_p6_targeted_summary(
    registration_records: Sequence[RegistrationDiagnosticRecord],
    hybrid_records: Sequence[HybridScoreRecord],
) -> str:
    ...
```

Markdown 必须包含：

- `cap3` registration residual 表。
- `tap1` hybrid fusion 表。
- anomaly 与 positive 对照。
- 明确说明 object score 越高越异常。
- 结论：是否支持进入更大代表类别实验。

## 6. 实验样本

### 6.1 cap3 registration diagnostics

必须包含：

```text
cap3_positive9
cap3_positive7
cap3_positive10
```

建议同时加入 anomaly 对照：

```text
cap3_hole0
cap3_hole1
cap3_broken2
cap3_broken3
```

目的：判断 positive 高分是否对应异常高的 template distance residual。

### 6.2 tap1 hybrid fusion

必须包含 anomaly：

```text
tap1_broken2
tap1_broken3
tap1_hole0
```

必须加入 positive 对照：

```text
tap1_positive0
```

如果 P5 score root 没有 `tap1_positive0.npz`，本轮先在代表样本 score root 中查找；若不存在，记录阻塞，不伪造 positive 对照。

## 7. 指标口径

### 7.1 object score

object score 越高表示越异常。

本轮关注：

- anomaly sample 的 object score 是否高于 positive。
- hybrid 是否提高 anomaly 的 GT/background 分离。
- hybrid 是否同时抬高 positive，导致 false positive 风险。

### 7.2 GT/background 分离

对 anomaly sample：

```text
separation = gt_score_mean - background_score_mean
```

越大越好。

对 positive sample：

- 没有 GT 点。
- 重点看 object score 是否异常升高。

## 8. 测试策略

采用 TDD：

1. `tests/test_targeted_p6.py`
   - 构造 fake NPZ 和 fake OBJ。
   - 验证 registration diagnostic 字段稳定。
   - 验证 hybrid score 使用 `pasdf_norm + alpha * geometry_norm`。
   - 验证 CSV/Markdown 包含 cap3/tap1 结论。
2. `tests/test_run_p6_targeted_diagnostics.py`
   - 通过 CLI fake data 验证 summary CSV/Markdown 和 SVG 输出。

质量门：

```bash
PYTHONPATH=src pytest -q
ruff check src scripts tests
black --check src scripts tests
mypy src/pcdad
pre-commit run --all-files
```

## 9. 执行命令

```bash
PYTHONPATH=src python scripts/run_p6_targeted_diagnostics.py \
  --score-root experiments/P5_pasdf_scores/representative \
  --template-root third_party/PASDF/data/ShapeNetAD \
  --cap3-samples \
    cap3_positive9 cap3_positive7 cap3_positive10 \
    cap3_hole0 cap3_hole1 cap3_broken2 cap3_broken3 \
  --tap1-samples tap1_broken2 tap1_broken3 tap1_hole0 \
  --tap1-positive-samples tap1_positive0 \
  --output-dir experiments/P6_targeted_diagnostics \
  --summary-md docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.md \
  --summary-csv docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.csv \
  --alpha 1.0 \
  --max-points 4096
```

## 10. 验收标准

- report 已补充人工判读结论。
- `cap3` registration diagnostics 输出 positive 与 anomaly 对照表。
- `tap1` hybrid fusion 输出 anomaly 与 positive 对照表。
- 若 `tap1_positive0` 不存在，summary 必须明确记录缺少 positive 对照，不能把 anomaly-only 结果解释成模型改进。
- 至少生成 `tap1_broken2/broken3/hole0` 的 PASDF vs hybrid SVG。
- 所有测试和质量门通过。
- 阶段记录写入中文 Markdown/CSV。
