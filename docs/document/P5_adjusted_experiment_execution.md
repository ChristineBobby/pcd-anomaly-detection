# P5 调整后实验执行计划

撰写日期：2026-06-10
适用阶段：P5 起步，承接 P4 几何增强 smoke 收口
当前基线：PASDF official-weight full 40-class evaluation，P4 registration/voxel sweep，A2/A3/A4 geometry smoke

---

## 目录

- [1. 调整原因](#1-调整原因)
- [2. 阶段目标](#2-阶段目标)
- [3. 执行顺序](#3-执行顺序)
- [4. 代码框架](#4-代码框架)
- [5. 核心接口设计](#5-核心接口设计)
- [6. 测试策略](#6-测试策略)
- [7. 实验与产物策略](#7-实验与产物策略)
- [8. 验收标准](#8-验收标准)

---

## 1. 调整原因

SOP 原始 P5 假设 P4 的 A2/A3/A4 几何增强在代表类别 smoke 中已经出现正向趋势，因此下一步可以按“代表类别小跑 -> 固定超参 -> 40 类全量”的顺序扩展。

当前实测结论不同。`docs/document/stage_record/2026-06-09_p4_geometry_closure.md` 已记录：

- A2/A3/A4 在 `cap3/tap1/helmet1/ashtray0` 的 2 sample/class smoke 中没有稳定拉开 anomaly 与 positive control。
- normal/curvature 权重主要放大 score 尺度，没有解决排序问题。
- 曲率当前为 CPU PCA，多尺度 16k 点 smoke 已明显耗时，不适合未经优化直接扩到 40 类。
- 单 template residual 对 template 差异、整体形变和采样分布敏感。

因此 P5 不能机械执行“40 类 A2/A3/A4 全量消融”。调整后的 P5 先把 PASDF baseline 的样本级和点级分数导出来，明确 baseline 真正失败在哪些样本、哪些点、哪些异常类型，再决定是否继续投入几何增强。

---

## 2. 阶段目标

P5 调整后的目标是把 P3/P4 已有产物转化为可解释实验证据：

1. 导出 PASDF per-sample/per-point score，补齐官方 `evaluation_results.csv` 缺失的样本级证据。
2. 生成可追溯的样本级摘要：object score、label、point count、GT point ratio、score 分位数、top-k score。
3. 输出失败分析候选清单：false positive、false negative、GT 内外分数倒挂、点级定位弱样本。
4. 建立 Real3D-AD 抽样验证的目录检查和 dry-run 准备，不把真实数据泛化留到 P6。
5. 将 P4 的 A2/A3/A4 定位为“弱几何 smoke 负结果”，只在 PASDF score 失败定位清楚后再做 targeted 几何可视化。

---

## 3. 执行顺序

### Task 1：PASDF per-sample score 导出

输入：

- `configs/experiment/E1_pasdf_baseline.yaml`
- PASDF 官方配置快照：`experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml`
- PASDF dataset/scorer/registration：`third_party/PASDF`

输出：

```text
experiments/P5_pasdf_scores/{class_name}/sample_scores.csv
experiments/P5_pasdf_scores/{class_name}/points/{sample_id}.npz
docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md
docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.csv
```

默认策略：

- `sample_scores.csv` 必须生成，进入轻量 stage record 汇总。
- per-point `npz` 默认可选，保留在 `experiments/`，不进入 git。
- 每个 `npz` 保存 aligned points、GT mask、PASDF point score、sample metadata，便于后续 heatmap/GT overlay。

### Task 2：样本级失败排序

基于 Task 1 输出：

- object-level：按类别内 positive/negative 分数阈值或 AUROC 排序，列出 false positive 和 false negative 候选。
- point-level：计算 GT 点内外 score mean、top-k overlap、GT point ratio，列出定位失败样本。
- 对 `helmet1` 这类“object 高、pixel 低”的类别优先看 GT 内外分数是否倒挂。

### Task 3：Real3D-AD 数据准备 dry-run

先不承诺全量推理，只做目录与点数口径检查：

- 检查 `configs/data/real3d.yaml` 与实际数据目录是否一致。
- 统计可用类别、样本数、点数范围。
- 选择首批 2 类候选，记录原始点数和下采样策略。

如果 Real3D-AD 数据尚未下载，本任务输出阻塞记录，不阻塞 Task 1/2。

### Task 4：targeted geometry 复查

只在 PASDF score 明确失败的样本上使用 P4 几何模块：

- `cap3/cap4/tap1`：优先检查 object false negative 或 registration warning 样本。
- `helmet1/vase1/bowl2`：优先检查 point-level GT 内外分数倒挂样本。
- 如果几何 residual 仍无正信号，记录为 P5 负结果，不扩 40 类。

---

## 4. 代码框架

### 4.1 `pcdad.analysis.pasdf_scores`

职责：定义 PASDF 样本级和点级分数的数据结构、统计函数和 CSV/Markdown 渲染。该模块不依赖 GPU，不直接 import 第三方 PASDF。

拟新增：

```text
src/pcdad/analysis/pasdf_scores.py
tests/test_pasdf_score_export.py
```

### 4.2 `scripts/export_pasdf_scores.py`

职责：薄 CLI，运行时把 `third_party/PASDF` 加入 `sys.path`，复用官方 dataset、registration 和 `SDFScorer`，逐样本导出分数。业务统计交给 `pcdad.analysis.pasdf_scores`。

拟新增：

```text
scripts/export_pasdf_scores.py
```

该脚本只在 Docker/conda `pasdf` 环境中执行。宿主机缺少 torch/open3d 时不应影响纯单测。

### 4.3 `pcdad.data.real3d`

职责：Real3D-AD dry-run 的目录与点数统计。若当前数据未就绪，本阶段只规划接口，不急于实现复杂 loader。

后续可新增：

```text
src/pcdad/data/real3d.py
scripts/inspect_real3d_data.py
tests/test_real3d_inspection.py
```

---

## 5. 核心接口设计

### 5.1 PASDF score 数据结构

```python
@dataclass(frozen=True)
class PasdfSampleScore:
    class_name: str
    sample_id: str
    sample_path: str
    label: int
    point_count: int
    object_score: float
    topk_score: float
    score_mean: float
    score_p95: float
    score_max: float
    gt_point_count: int
    gt_point_ratio: float
    gt_score_mean: float | None
    background_score_mean: float | None
    point_score_path: str | None = None
```

### 5.2 统计函数

```python
def summarize_point_scores(
    *,
    class_name: str,
    sample_id: str,
    sample_path: str,
    point_scores: np.ndarray,
    mask: np.ndarray,
    label: int,
    top_k: int,
    point_score_path: str | None = None,
) -> PasdfSampleScore:
    ...
```

行为约束：

- `point_scores` 必须是一维数组。
- `mask` 必须与 `point_scores` 等长。
- `top_k` 小于 1 时抛 `ValueError`；大于点数时自动截断为点数。
- positive 样本没有 GT 点时，`gt_score_mean=None`，`background_score_mean=score_mean`。

### 5.3 汇总与渲染

```python
def write_sample_scores_csv(records: Sequence[PasdfSampleScore], path: Path) -> Path:
    ...

def render_score_export_markdown(records: Sequence[PasdfSampleScore], title: str) -> str:
    ...
```

Markdown 至少包含：

- 总样本数、类别数、异常样本数、positive 样本数。
- 每类 object score 均值、positive/anomaly 均值、GT 内外 score 均值。
- 分数倒挂或异常/positive 分不开的优先样本。

---

## 6. 测试策略

先做纯 NumPy TDD：

- `summarize_point_scores` 正确计算 top-k、p95、GT 内外均值。
- positive 样本没有 GT 点时，不产生 NaN 字符串污染 CSV。
- 长度不一致、空分数、非法 `top_k` 报错清晰。
- CSV round-trip 字段稳定，便于后续 stage record 复用。
- Markdown 渲染能在空记录时报错，在正常记录中包含关键类别和样本。

需要 PASDF 环境的脚本只做轻量 import/dry-run 测试，真实导出在 Docker `pasdf` 环境中运行。

---

## 7. 实验与产物策略

进入 git：

- `src/pcdad/analysis/pasdf_scores.py`
- `scripts/export_pasdf_scores.py`
- `tests/test_pasdf_score_export.py`
- `docs/document/stage_record/*_p5_pasdf_score_export_summary.md`
- `docs/document/stage_record/*_p5_pasdf_score_export_summary.csv`

不进入 git：

- `experiments/P5_pasdf_scores/**/points/*.npz`
- 完整 run log、可视化大图、mesh、权重、数据。

命令模板：

```bash
PYTHONPATH=src python scripts/export_pasdf_scores.py \
  --config experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml \
  --pasdf-root third_party/PASDF \
  --classes cap3 helmet1 tap1 ashtray0 \
  --output-dir experiments/P5_pasdf_scores/representative \
  --summary-md docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md \
  --summary-csv docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.csv \
  --save-point-scores
```

---

## 8. 验收标准

- P5 文档与 SOP/P4 closure 口径一致：A2/A3/A4 不再默认扩 40 类。
- PASDF per-sample score 导出脚本可在 `pasdf` 环境中对 1-4 个代表类别运行。
- 样本级 CSV/Markdown 能指出下一批失败分析对象。
- 纯代码质量门通过：`pytest`、`ruff`、`black --check`、`mypy src/pcdad`。
- 若 Docker 容器不可用，代码与纯单测仍能完成；真实 PASDF 导出标记为环境待执行，不伪造结果。
