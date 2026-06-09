# P4 几何诊断与增强执行计划

撰写日期：2026-06-08
适用阶段：P4 后半段，稳定性复核、样本级几何诊断、几何增强 smoke
当前基线：PASDF official-weight full 40-class evaluation 与 P4 voxel sweep 小实验

---

## 目录

- [1. 当前状态](#1-当前状态)
- [2. 阶段目标](#2-阶段目标)
- [3. 执行顺序](#3-执行顺序)
- [4. 代码框架](#4-代码框架)
- [5. 核心接口设计](#5-核心接口设计)
- [6. 测试策略](#6-测试策略)
- [7. 实验与产物策略](#7-实验与产物策略)
- [8. 验收标准](#8-验收标准)

---

## 1. 当前状态

已完成：

- P3 PASDF full 40-class baseline。
- P4 failure summary。
- Open3D warning 的 class-level 与 sample-level 归因。
- `cap3/cap4/tap1/helmet2` 小规模 voxel sweep。

关键结论：

- `cap3` 对 registration 参数敏感，`voxel_size=0.04` 消除 warning，object AUROC 提升到 `0.771930`。
- `cap4` 在 `voxel_size=0.05` 有小幅提升，但 warning 仍存在，说明不是单纯 voxel 参数问题。
- `tap1` 没有 Open3D warning，官方 voxel size 也没有改善。
- `helmet2` 单类 rerun 明显低于 P3 full-run，需要先做稳定性复核。

---

## 2. 阶段目标

P4 后半段不直接追求 40 类指标提升，而是先把失败类型分清楚：

1. 确认 `helmet2` 单类评估是否稳定。
2. 建立样本级几何诊断能力：nearest-neighbor、Chamfer、对齐前后 overlay。
3. 建立可测试的几何基础算子：kNN、PCA 法向、多尺度曲率。
4. 建立几何 residual score 与对象级聚合。
5. 在少量代表类别上做 geometry smoke，判断是否值得进入 P5 消融。

---

## 3. 执行顺序

### Task 1：PASDF 稳定性复核

优先类别：

- `helmet2`：P3 full-run object AUROC 为 `0.776812`，但单类 rerun 为 `0.640580`。
- 可选复核：`cap3` 的 `voxel_size=0.04`，确认 registration 修复结果是否稳定。

执行内容：

- 新增 PASDF stability summary 模块。
- 复跑 `helmet2` 2-3 次，固定 `seed=42`、`voxel_size=0.03`。
- 汇总每次 pixel/object AUROC、warning 数、run 目录。
- 输出中文 stage record。

### Task 2：几何基础模块

新增：

```text
src/pcdad/geometry/neighbors.py
src/pcdad/geometry/normals.py
src/pcdad/geometry/curvature.py
```

先用合成点云 TDD，不接 PASDF。

### Task 3：几何 residual 与 score 聚合

新增：

```text
src/pcdad/geometry/residuals.py
src/pcdad/scoring/aggregate.py
src/pcdad/scoring/geometric.py
```

先实现纯 NumPy 版本，避免引入 GPU 或 Open3D 依赖。

### Task 4：样本级诊断与可视化

新增：

```text
src/pcdad/analysis/sample_geometry.py
scripts/analyze_sample_geometry.py
scripts/run_geometry_smoke.py
```

输出：

- sample-level CSV summary。
- 小规模 SVG overlay。
- 中文 stage record。

---

## 4. 代码框架

### 4.1 `pcdad.analysis`

保持“读实验产物、产出轻量记录”的职责：

- `pasdf_stability.py`：重复 run 的结果汇总。
- `sample_geometry.py`：样本级点云与 template 的几何诊断。

### 4.2 `pcdad.geometry`

只放几何基础算子，不依赖 PASDF：

- `neighbors.py`：kNN 与 nearest-neighbor。
- `normals.py`：PCA 法向估计和法向夹角 residual。
- `curvature.py`：PCA 曲率和多尺度曲率。
- `residuals.py`：sample 到 template 的几何 residual。

### 4.3 `pcdad.scoring`

只放 score 聚合与融合：

- `aggregate.py`：top-k、percentile、局部平滑。
- `geometric.py`：distance/normal/curvature residual 到 point/object score。

---

## 5. 核心接口设计

### 5.1 稳定性复核

```python
@dataclass(frozen=True)
class PasdfRunRecord:
    class_name: str
    run_id: str
    voxel_size: float
    pixel_auc: float
    object_auc: float
    warning_count: int
    warning_sample_count: int
    run_dir: Path

@dataclass(frozen=True)
class PasdfStabilitySummary:
    rows: tuple[PasdfRunRecord, ...]
    by_class: dict[str, ClassStabilitySummary]
```

```python
def collect_pasdf_stability_runs(root: Path, classes: tuple[str, ...]) -> PasdfStabilitySummary:
    ...

def render_stability_markdown(summary: PasdfStabilitySummary) -> str:
    ...
```

### 5.2 邻域与 NN

```python
@dataclass(frozen=True)
class NeighborResult:
    distances: np.ndarray
    indices: np.ndarray

def nearest_neighbors(query: np.ndarray, reference: np.ndarray, *, k: int = 1) -> NeighborResult:
    ...

def knn_indices(points: np.ndarray, *, k: int) -> np.ndarray:
    ...
```

### 5.3 法向与曲率

```python
@dataclass(frozen=True)
class NormalEstimationResult:
    normals: np.ndarray
    eigenvalues: np.ndarray
    curvature: np.ndarray

def estimate_pca_normals(points: np.ndarray, *, k: int = 32) -> NormalEstimationResult:
    ...

def normal_angle_residual(source_normals: np.ndarray, target_normals: np.ndarray) -> np.ndarray:
    ...
```

```python
@dataclass(frozen=True)
class CurvatureResult:
    per_scale: dict[int, np.ndarray]
    mean_curvature: np.ndarray
    max_curvature: np.ndarray

def estimate_multiscale_curvature(
    points: np.ndarray,
    *,
    k_values: tuple[int, ...] = (16, 32, 64),
) -> CurvatureResult:
    ...
```

### 5.4 几何 residual 与 score

```python
@dataclass(frozen=True)
class GeometryResidualResult:
    nn_distance: np.ndarray
    normal_angle: np.ndarray | None
    curvature_delta: np.ndarray | None
    template_indices: np.ndarray

def point_to_template_residuals(
    sample_points: np.ndarray,
    template_points: np.ndarray,
    *,
    k_normal: int = 32,
    k_curvature: tuple[int, ...] = (16, 32, 64),
    use_normals: bool = True,
    use_curvature: bool = True,
) -> GeometryResidualResult:
    ...
```

```python
@dataclass(frozen=True)
class GeometryScoreConfig:
    distance_weight: float = 1.0
    normal_weight: float = 0.5
    curvature_weight: float = 0.5
    topk_ratio: float = 0.05
    smooth_k: int = 16

@dataclass(frozen=True)
class GeometryScoreResult:
    point_scores: np.ndarray
    object_score: float
    components: dict[str, np.ndarray]
```

```python
def score_geometry_residuals(
    residuals: GeometryResidualResult,
    config: GeometryScoreConfig,
) -> GeometryScoreResult:
    ...
```

---

## 6. 测试策略

所有新代码先写测试，再实现。

必须覆盖：

- 空点云、shape 错误、`k` 非法值。
- 平面点云法向稳定，曲率接近 0。
- 球面或抛物面曲率高于平面。
- top-k 聚合在少量异常点存在时能提高 object score。
- 全相等分数和单点输入行为明确。
- PASDF stability 汇总能正确读多个 run 目录，并给出 mean/std。

文档只检查内容和实验数据对得上，不把章节格式写死。

---

## 7. 实验与产物策略

进入 git：

- 代码、测试、配置。
- 中文 stage record。
- 小型 CSV summary。

不进入 git：

- 数据集。
- PASDF 权重。
- 完整 run.log。
- 大量 per-sample score。
- 大图和点云可视化批量产物。

实验输出目录：

```text
experiments/P4_stability/
experiments/P4_geometry_smoke/
```

---

## 8. 验收标准

Task 1 验收：

- `helmet2` 至少 2-3 次稳定性复跑完成。
- 中文 stage record 说明均值、标准差、warning 情况和是否稳定。
- `pytest/ruff/black/mypy/pre-commit` 对代码通过。

P4 后半段完整验收：

- `geometry/` 和 `scoring/` 模块有单测。
- 至少 1 个低分类别完成 geometry smoke。
- 产物能说明增强是否值得进入 P5。
- 如果指标无提升，给出负结果解释。

---

## 9. 后半段落地清单

本节作为后续代码编写的执行依据。原则是先把可复用几何能力写小、写清楚，再用轻量 smoke 去接真实数据。

### 9.1 已完成：PASDF 稳定性复核

文件：

```text
src/pcdad/analysis/pasdf_stability.py
scripts/summarize_pasdf_stability.py
tests/test_pasdf_stability_analysis.py
tests/test_summarize_pasdf_stability.py
docs/document/stage_record/2026-06-08_p4_stability_summary.md
docs/document/stage_record/2026-06-08_p4_stability_summary.csv
```

验收命令：

```bash
PYTHONPATH=src pytest tests/test_pasdf_stability_analysis.py tests/test_summarize_pasdf_stability.py -q
```

当前 `helmet2` 3 次单类复跑结论：

- object AUROC：`0.652174`、`0.579710`、`0.689855`。
- mean object AUROC：`0.640580`。
- std object AUROC：`0.045708`。
- warning 总数：`0`。

解释：`helmet2` 单类结果低于 P3 full-run，且不是 Open3D warning 直接造成。进入几何增强前，不把 `helmet2` 当作稳定正例。

### 9.2 几何基础算子

文件：

```text
src/pcdad/geometry/neighbors.py
src/pcdad/geometry/normals.py
src/pcdad/geometry/curvature.py
tests/test_geometry_neighbors.py
tests/test_geometry_normals_curvature.py
```

接口：

```python
nearest_neighbors(query, reference, k=1) -> NeighborResult
knn_indices(points, k) -> np.ndarray
estimate_pca_normals(points, k=32) -> NormalEstimationResult
normal_angle_residual(source_normals, target_normals) -> np.ndarray
estimate_multiscale_curvature(points, k_values=(16, 32, 64)) -> CurvatureResult
```

验收重点：

- 输入必须是 `(N, 3)` 点云。
- `k` 必须为正，且不能超过 reference 数量。
- 平面点云曲率接近 `0`。
- 抛物面或球面曲率高于平面。
- 法向夹角 residual 对正负法向方向不敏感。

### 9.3 residual 与 score

文件：

```text
src/pcdad/geometry/residuals.py
src/pcdad/scoring/aggregate.py
src/pcdad/scoring/geometric.py
tests/test_geometry_residuals.py
tests/test_geometric_scoring.py
```

接口：

```python
point_to_template_residuals(sample_points, template_points, ...) -> GeometryResidualResult
topk_mean(scores, ratio=0.05) -> float
percentile_score(scores, percentile=95.0) -> float
smooth_point_scores(points, scores, k=16) -> np.ndarray
score_geometry_residuals(residuals, config) -> GeometryScoreResult
```

策略：

- distance residual 是第一优先级，normal/curvature residual 是可选增强。
- point score 采用 robust min-max 归一化后加权融合。
- object score 采用 top-k mean，先不替代 PASDF，只作为 smoke 诊断指标。

### 9.4 样本级几何诊断与 smoke

文件：

```text
src/pcdad/analysis/sample_geometry.py
scripts/analyze_sample_geometry.py
scripts/run_geometry_smoke.py
tests/test_sample_geometry_analysis.py
tests/test_analyze_sample_geometry.py
tests/test_run_geometry_smoke.py
```

真实数据默认路径：

```text
data/Anomaly-ShapeNet-v2/dataset/16384
```

默认优先类别：

```text
cap3, cap4, tap1
```

默认产物：

```text
experiments/P4_geometry_smoke/
docs/document/stage_record/2026-06-08_p4_geometry_smoke_summary.md
docs/document/stage_record/2026-06-08_p4_geometry_smoke_summary.csv
```

smoke 只生成少量 CSV 和 SVG，完整 per-point score、大日志和批量图继续留在 ignored `experiments/`。
