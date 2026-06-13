# P6 Region Explanation And Cap3 Residual Diagnostics 架构计划

撰写日期：2026-06-13

适用阶段：P6 alpha sweep positive-aware gating 失败后的小范围后续诊断

## 目录

- [1. 背景与结论输入](#1-背景与结论输入)
- [2. 本轮目标](#2-本轮目标)
- [3. 方法设计](#3-方法设计)
- [4. 代码框架](#4-代码框架)
- [5. 核心接口](#5-核心接口)
- [6. 实验样本](#6-实验样本)
- [7. 输出文件](#7-输出文件)
- [8. 测试策略](#8-测试策略)
- [9. 执行命令](#9-执行命令)
- [10. 验收标准](#10-验收标准)

## 1. 背景与结论输入

P5/P6 已经给出三条稳定结论：

1. `cap3_positive9/7/10` 的红蓝 overlay 存在明显局部错位，没有明显尺度问题；P6 nearest-neighbor residual 进一步显示这 3 个 positive 的 top5% template residual 明显高于 `cap3` anomaly 对照。
2. `tap1_broken2/broken3/hole0` 的 PASDF 图整体偏蓝，geometry residual 图有更多高分区域，且可见 GT 黑边附近更接近高分区域。
3. `tap1` naive additive fusion 和 alpha sweep 都没有通过 positive-aware object 排序约束；geometry residual 不能直接作为 additive object score 扩大实验。

因此本轮不继续调 alpha，也不做 40 类 full hybrid。后续应转成两条诊断线：

- `cap3`：解释 high residual 区域是否与 PASDF 高分区域重叠，进一步确认 false positive 是否来自局部模板错位。
- `tap1`：比较 PASDF 与 geometry 的 top-k 高分点是否更贴近 GT 或 GT 邻域，只把 geometry 当局部解释信号。

## 2. 本轮目标

本轮只做可解释诊断，不改 PASDF 模型，不训练新模型，不改变官方评估协议。

目标一：`cap3` high residual region diagnostics

- 计算 PASDF top-k 点与 template residual top-k 点的重叠率。
- 计算 residual top-k 点的局部集中程度，用最近邻半径或 bounding-box 占比描述。
- 对 positive 与 anomaly 对照分别输出统计，判断 high residual 是否是 `cap3_positive9/7/10` 的异常高分来源。

目标二：`tap1` region-level explanation

- 对每个 anomaly 样本分别计算 PASDF top-k、geometry top-k 对 GT 点的命中率。
- 引入 GT-neighborhood 命中：高分点距离最近 GT 点小于阈值时，记为邻域命中。
- 输出 top-k hit rate、GT coverage、neighborhood hit rate、enrichment。
- 对比 PASDF 与 geometry，判断 geometry 是否只是在全局抬分，还是更贴近 GT 局部区域。

## 3. 方法设计

### 3.1 top-k 区域定义

对每个 score 向量按分数从高到低选取 top-k：

```text
k = max(1, ceil(point_count * top_ratio))
top_ratio 默认 0.05
```

如果分数存在并列，不额外做复杂排序；使用稳定 `np.argsort(..., kind="mergesort")` 保证复现。

### 3.2 GT 命中与覆盖

对 anomaly 样本：

```text
topk_gt_hit_rate = topk 中 GT 点数量 / topk 点数量
gt_coverage = topk 中 GT 点数量 / 全部 GT 点数量
```

这两个指标含义不同：

- `topk_gt_hit_rate` 看高分区域里有多少是真 GT。
- `gt_coverage` 看 GT 被高分区域覆盖了多少。

### 3.3 GT-neighborhood 命中

GT 点很少，尤其 `tap1_broken2/broken3/hole0` 的 GT 占比低。为了避免只用精确 GT 点过于苛刻，增加邻域命中：

```text
topk_gt_neighbor_hit_rate = topk 中距离最近 GT 点 <= radius 的点数 / topk 点数量
```

radius 默认按当前样本的点云尺度自动确定：

```text
radius = bbox_diagonal * radius_ratio
radius_ratio 默认 0.02
```

如果用户后续认为邻域过宽或过窄，可在 CLI 中调 `--neighbor-radius-ratio`。

### 3.4 enrichment

为了比较 top-k 区域相对随机点的提升，定义：

```text
gt_enrichment = topk_gt_hit_rate / gt_fraction
neighbor_enrichment = topk_gt_neighbor_hit_rate / neighbor_fraction
```

其中：

- `gt_fraction = gt_point_count / point_count`
- `neighbor_fraction = GT 邻域点数量 / point_count`

enrichment 大于 1 表示高分区域比随机点更靠近 GT 或 GT 邻域。

### 3.5 cap3 residual/PASDF overlap

`cap3` positive 没有 GT，因此看两个 top-k 集合：

```text
pasdf_topk_indices
residual_topk_indices
overlap = |intersection| / k
```

若 `cap3_positive9/7/10` 的 overlap 高，说明 PASDF 高分点和 template residual 高点一致，支持“局部模板错位导致 false positive”的解释。

同时计算 residual top-k 的空间集中程度：

```text
residual_topk_bbox_diag / sample_bbox_diag
residual_topk_mean_pair_distance / sample_bbox_diag
```

值越小，说明 high residual 更集中在局部区域；值越大，说明是更全局的对齐问题。

## 4. 代码框架

复用并扩展：

- `src/pcdad/analysis/targeted_p6.py`
  - 新增 region explanation dataclass 与纯函数。
  - 复用 `load_pasdf_point_score`、`load_pasdf_template_points`、`compute_distance_geometry_scores`、`robust_minmax`。
  - 不新增训练依赖。
- `scripts/run_p6_targeted_diagnostics.py`
  - 新增可选参数触发 region diagnostics。
  - 保持已有 P6 targeted diagnostics 与 alpha sweep 行为不变。
- `tests/test_targeted_p6_region_explanation.py`
  - 测 top-k、GT 命中、邻域命中、cap3 overlap、CSV/Markdown。
- `tests/test_run_p6_region_explanation_cli.py`
  - 测 CLI 能写出 region explanation summary。

## 5. 核心接口

### 5.1 TopKRegionMetrics

```python
@dataclass(frozen=True)
class TopKRegionMetrics:
    score_name: str
    top_ratio: float
    top_count: int
    gt_hit_count: int
    gt_hit_rate: float | None
    gt_coverage: float | None
    gt_neighbor_hit_count: int
    gt_neighbor_hit_rate: float | None
    gt_neighbor_coverage: float | None
    gt_enrichment: float | None
    gt_neighbor_enrichment: float | None
```

### 5.2 Tap1RegionExplanationRecord

```python
@dataclass(frozen=True)
class Tap1RegionExplanationRecord:
    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    neighbor_radius: float
    pasdf_topk_gt_hit_rate: float | None
    geometry_topk_gt_hit_rate: float | None
    pasdf_gt_coverage: float | None
    geometry_gt_coverage: float | None
    pasdf_neighbor_hit_rate: float | None
    geometry_neighbor_hit_rate: float | None
    pasdf_neighbor_enrichment: float | None
    geometry_neighbor_enrichment: float | None
```

### 5.3 Cap3ResidualRegionRecord

```python
@dataclass(frozen=True)
class Cap3ResidualRegionRecord:
    class_name: str
    sample_id: str
    label: int
    point_count: int
    pasdf_object_score: float
    residual_topk_mean: float
    residual_topk_p95: float
    pasdf_residual_topk_overlap: float
    residual_topk_bbox_ratio: float
    residual_topk_mean_pair_distance_ratio: float
```

### 5.4 函数接口

```python
def topk_indices(scores: np.ndarray, *, ratio: float) -> np.ndarray:
    ...
```

```python
def compute_topk_region_metrics(
    *,
    points: np.ndarray,
    scores: np.ndarray,
    mask: np.ndarray,
    score_name: str,
    top_ratio: float,
    neighbor_radius_ratio: float,
) -> TopKRegionMetrics:
    ...
```

```python
def compute_tap1_region_explanation_record(
    *,
    score_path: Path,
    template_root: Path,
    top_ratio: float,
    neighbor_radius_ratio: float,
) -> Tap1RegionExplanationRecord:
    ...
```

```python
def compute_cap3_residual_region_record(
    *,
    score_path: Path,
    template_root: Path,
    top_ratio: float,
) -> Cap3ResidualRegionRecord:
    ...
```

```python
def render_region_explanation_markdown(
    *,
    tap1_records: Sequence[Tap1RegionExplanationRecord],
    cap3_records: Sequence[Cap3ResidualRegionRecord],
) -> str:
    ...
```

## 6. 实验样本

### 6.1 cap3

```text
cap3_positive9
cap3_positive7
cap3_positive10
cap3_hole0
cap3_hole1
cap3_broken2
cap3_broken3
```

### 6.2 tap1

```text
tap1_broken2
tap1_broken3
tap1_hole0
```

本轮 tap1 不需要 positive 对照，因为我们不再输出 additive object score；positive-aware 风险已经由 alpha sweep 记录为负结果。

## 7. 输出文件

实验产物：

```text
experiments/P6_region_explanation/cap3_residual_regions.csv
experiments/P6_region_explanation/tap1_region_explanation.csv
```

阶段记录：

```text
docs/document/stage_record/2026-06-13_p6_region_explanation_summary.md
docs/document/stage_record/2026-06-13_p6_region_explanation_summary.csv
```

CSV summary 可合并写 tap1 与 cap3，使用 `record_type` 字段区分。

## 8. 测试策略

新增单测：

1. `topk_indices` 对 ratio、空数组、非有限值进行校验。
2. `compute_topk_region_metrics` 在人工构造数据上验证 GT hit、coverage、neighbor hit、enrichment。
3. `compute_tap1_region_explanation_record` 验证 geometry 与 PASDF 两套指标都存在。
4. `compute_cap3_residual_region_record` 验证 PASDF/residual top-k overlap 和集中度指标。
5. CSV 与 Markdown 输出稳定。
6. CLI 可以写出两个 CSV 和一个 Markdown summary。

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
  --run-region-explanation \
  --region-output-dir experiments/P6_region_explanation \
  --region-summary-md docs/document/stage_record/2026-06-13_p6_region_explanation_summary.md \
  --region-summary-csv docs/document/stage_record/2026-06-13_p6_region_explanation_summary.csv \
  --top-ratio 0.05 \
  --neighbor-radius-ratio 0.02
```

## 10. 验收标准

代码验收：

- 所有新增指标均有单测覆盖。
- 新 CLI 参数不破坏已有 P6 targeted diagnostics 和 alpha sweep。
- 输出 CSV/Markdown 字段稳定，文档为中文。

实验验收：

- `cap3_positive9/7/10` 输出 PASDF/residual top-k overlap 和 residual 局部集中度，用于解释 false positive。
- `tap1_broken2/broken3/hole0` 输出 PASDF 与 geometry 的 GT/GT-neighborhood top-k 对照，用于判断 geometry 是否更接近 GT 局部区域。
- 若 geometry 的 neighbor enrichment 明显高于 PASDF，则后续可以考虑非加性 region-level explanation；若没有明显优势，则暂停 geometry 主线，转向 PASDF 点级定位失败分析。
