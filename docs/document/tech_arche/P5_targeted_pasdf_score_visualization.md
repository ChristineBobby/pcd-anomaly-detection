# P5 Targeted Case Study 架构与接口设计

撰写日期：2026-06-13
适用阶段：P5 调整主线，PASDF 样本级分数导出之后

---

## 目录

- [1. 背景与目标](#1-背景与目标)
- [2. 输入与输出](#2-输入与输出)
- [3. 代码框架](#3-代码框架)
- [4. 核心接口](#4-核心接口)
- [5. 样本清单](#5-样本清单)
- [6. 测试策略](#6-测试策略)
- [7. 执行命令](#7-执行命令)
- [8. 验收标准](#8-验收标准)

---

## 1. 背景与目标

P5 已经完成 PASDF per-sample/per-point score 导出：

```text
experiments/P5_pasdf_scores/representative/{class}/points/{sample_id}.npz
docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md
docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.csv
```

P5 score summary 指出：

- `cap3` 的 positive object score 均值高于 anomaly，是对象级排序失败的首要类别。
- `tap1` 的 object-level 分离明显，但 `broken/hole` 局部异常分数偏弱。
- P4 geometry smoke 显示 `tap1_broken2` 在几何 residual 上有局部正信号，适合做 PASDF vs geometry 对照。

本阶段目标不是扩展 A2/A3/A4 到 40 类，而是做 targeted case study：

1. 为 `cap3_positive9/7/10` 生成 registration/template overlay，判断 false positive 是否来自配准或模板差异。
2. 为 `tap1_broken2/broken3/hole0` 生成 PASDF score 与 geometry score 并排图，判断 PASDF 漏检区域是否可由几何 residual 解释。
3. 保留 PASDF heatmap/GT overlay，作为 case-study 基础视图。

---

## 2. 输入与输出

### 2.1 输入

PASDF point-score NPZ：

```text
experiments/P5_pasdf_scores/representative/cap3/points/cap3_positive9.npz
experiments/P5_pasdf_scores/representative/cap3/points/cap3_positive7.npz
experiments/P5_pasdf_scores/representative/cap3/points/cap3_positive10.npz
experiments/P5_pasdf_scores/representative/tap1/points/tap1_broken2.npz
experiments/P5_pasdf_scores/representative/tap1/points/tap1_broken3.npz
experiments/P5_pasdf_scores/representative/tap1/points/tap1_hole0.npz
```

PASDF template OBJ：

```text
third_party/PASDF/data/ShapeNetAD/{class}/{class}_template0.obj
```

说明：

- P5 NPZ 中的 `points` 是经过 PASDF registration 后的 aligned points。
- registration/template overlay 使用同一 canonical 坐标系下的 aligned sample points 和 PASDF template vertices。
- geometry score 使用 aligned sample points 到 PASDF template vertices 的 nearest-neighbor distance residual。当前 targeted 对照先使用 distance-only geometry，避免再次引入 CPU PCA 曲率开销。

### 2.2 输出

大图输出到 ignored 实验目录：

```text
experiments/P5_case_study/pasdf_scores/{class}/{sample_id}_pasdf_score.svg
experiments/P5_case_study/template_overlay/{class}/{sample_id}_template_overlay.svg
experiments/P5_case_study/pasdf_vs_geometry/{class}/{sample_id}_pasdf_vs_geometry.svg
```

轻量记录进入 git：

```text
docs/document/stage_record/2026-06-13_p5_targeted_case_study.md
docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv
```

---

## 3. 代码框架

### 3.1 `src/pcdad/viz/pointcloud.py`

职责：通用 SVG 渲染，不依赖 PASDF 业务。

新增接口：

```python
def write_pointcloud_score_svg(...) -> None:
    """单个点云 score heatmap + GT overlay。"""

def write_pointcloud_template_overlay_svg(...) -> None:
    """sample/template registration overlay。"""

def write_pointcloud_score_comparison_svg(...) -> None:
    """同一批点的两个 score map 并排对照。"""
```

### 3.2 `src/pcdad/analysis/pasdf_case_study.py`

职责：读取 P5 NPZ、加载 PASDF template、计算 targeted case-study 统计，并调用可视化函数。

新增/扩展接口：

```python
@dataclass(frozen=True)
class PasdfCaseStudySpec:
    score_root: Path
    sample_ids: tuple[str, ...]
    output_dir: Path
    template_root: Path = Path("third_party/PASDF/data/ShapeNetAD")
    overlay_sample_ids: tuple[str, ...] = ()
    comparison_sample_ids: tuple[str, ...] = ()
    max_points: int = 4096
    seed: int = 42
```

```python
@dataclass(frozen=True)
class PasdfCaseStudyRecord:
    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    object_score: float
    score_mean: float
    score_p95: float
    score_max: float
    gt_score_mean: float | None
    background_score_mean: float | None
    svg_path: str
    point_score_path: str
    template_overlay_path: str | None
    geometry_comparison_path: str | None
    geometry_object_score: float | None
    geometry_gt_score_mean: float | None
    geometry_background_score_mean: float | None
```

### 3.3 `scripts/visualize_pasdf_scores.py`

职责：薄 CLI，只解析参数并调用 `pcdad.analysis.pasdf_case_study`。

关键参数：

```text
--score-root
--samples
--template-root
--template-overlay-samples
--geometry-comparison-samples
--output-dir
--summary-md
--summary-csv
--max-points
--seed
```

---

## 4. 核心接口

### 4.1 Template 读取与旋转

```python
def load_pasdf_template_points(template_root: Path, class_name: str) -> np.ndarray:
    ...
```

行为：

- 读取 `{class}/{class}_template0.obj` 中以 `v ` 开头的 vertex。
- 应用 PASDF ShapeNetAD 官方同款 canonical rotation。
- 返回 `(N, 3)` float32 数组。

### 4.2 Geometry score

```python
def compute_distance_geometry_scores(points: np.ndarray, template_points: np.ndarray) -> GeometryScoreResult:
    ...
```

行为：

- 使用 `point_to_template_residuals(..., use_normals=False, use_curvature=False)`。
- 使用 `score_geometry_residuals` 得到 point/object score。
- 当前 targeted case study 只使用 distance component，后续若需要再扩 normal/curvature。

### 4.3 Markdown 解读

Markdown 需要包含：

- 每个样本的 PASDF object score、GT 点数、GT/背景均值。
- 若生成 template overlay，记录 overlay SVG 路径。
- 若生成 PASDF-vs-geometry 对照，记录 geometry object score 与 GT/背景均值。
- 对 positive 高分样本标注“false-positive/template/registration 候选”。
- 对 anomaly GT 内均值不高于背景的样本标注“点级定位失败优先样本”。

---

## 5. 样本清单

本轮必须覆盖：

```text
cap3_positive9
cap3_positive7
cap3_positive10
tap1_broken2
tap1_broken3
tap1_hole0
```

默认可继续保留 P5 score summary 中其他 case：

```text
cap3_hole0
cap3_hole1
cap3_broken2
cap3_broken3
helmet1_concavity2
helmet1_concavity4
helmet1_concavity3
```

产物分类：

- `cap3_positive9/7/10`：必须生成 PASDF heatmap 和 template overlay。
- `tap1_broken2/broken3/hole0`：必须生成 PASDF heatmap 和 PASDF-vs-geometry comparison。
- 其他样本：生成 PASDF heatmap，用于后续人工复查。

---

## 6. 测试策略

采用 TDD：

1. `tests/test_visualize.py`
   - 覆盖 score heatmap SVG。
   - 覆盖 template overlay SVG。
   - 覆盖 score comparison SVG。
2. `tests/test_pasdf_case_study.py`
   - 构造 fake NPZ 和 fake OBJ。
   - 验证 `run_pasdf_case_study` 写出 PASDF SVG、overlay SVG、comparison SVG。
   - 验证 CSV 字段稳定。
   - 验证 Markdown 包含 overlay/comparison 路径与 geometry 统计。
3. `tests/test_visualize_pasdf_scores.py`
   - 通过 CLI fake data 验证 summary Markdown/CSV/SVG 生成。

质量门：

```bash
PYTHONPATH=src pytest -q
ruff check src scripts tests
black --check src scripts tests
mypy src/pcdad
pre-commit run --all-files
```

---

## 7. 执行命令

```bash
PYTHONPATH=src python scripts/visualize_pasdf_scores.py \
  --score-root experiments/P5_pasdf_scores/representative \
  --samples \
    cap3_positive9 cap3_positive7 cap3_positive10 \
    cap3_hole0 cap3_hole1 cap3_broken2 cap3_broken3 \
    helmet1_concavity2 helmet1_concavity4 helmet1_concavity3 \
    tap1_broken2 tap1_broken3 tap1_hole0 \
  --template-overlay-samples cap3_positive9 cap3_positive7 cap3_positive10 \
  --geometry-comparison-samples tap1_broken2 tap1_broken3 tap1_hole0 \
  --template-root third_party/PASDF/data/ShapeNetAD \
  --output-dir experiments/P5_case_study \
  --summary-md docs/document/stage_record/2026-06-13_p5_targeted_case_study.md \
  --summary-csv docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv \
  --max-points 4096
```

---

## 8. 验收标准

- `cap3_positive9/7/10` 均有 registration/template overlay。
- `tap1_broken2/broken3/hole0` 均有 PASDF-vs-geometry 并排对照。
- 默认 13 个 targeted sample 均有 PASDF score heatmap。
- Markdown/CSV 进入 `docs/document/stage_record/`。
- `experiments/P5_case_study/` 不进入 git。
- 全量质量门通过。
