# P6 PASDF Calibration And Registration Robustness 架构计划

撰写日期：2026-06-14

适用阶段：P6 targeted diagnostics 后续小范围实验

## 目录

- [1. 当前进度核对](#1-当前进度核对)
- [2. 本轮问题定义](#2-本轮问题定义)
- [3. 本轮不做什么](#3-本轮不做什么)
- [4. 方案选择](#4-方案选择)
- [5. 代码框架](#5-代码框架)
- [6. 核心接口设计](#6-核心接口设计)
- [7. 指标口径](#7-指标口径)
- [8. 实验范围](#8-实验范围)
- [9. 输出文件](#9-输出文件)
- [10. 测试策略](#10-测试策略)
- [11. 执行命令](#11-执行命令)
- [12. 验收标准](#12-验收标准)

## 1. 当前进度核对

本计划基于以下已完成事实，不重新推翻前面结论：

1. P0-P3 已完成。PASDF 官方 40 类 baseline 已复现，mean object AUROC 为 `0.900214149779`，mean pixel AUROC 为 `0.896009030694`。
2. P4 几何增强 smoke 已关闭为负结果。A2/A3/A4 在 `cap3/tap1/helmet1/ashtray0` 上没有稳定拉开 anomaly 与 positive control，因此不扩展 naive geometry 到 40 类。
3. P5 已导出代表类别 PASDF per-point score，覆盖 `ashtray0/cap3/helmet1/tap1`。`experiments/P5_pasdf_scores/representative` 是本轮主要输入。
4. P6 targeted diagnostics 已完成：
   - `cap3_positive9/7/10` 存在明显 registration/template mismatch 证据。
   - `tap1` additive fusion 与 alpha sweep 均未通过 positive-aware object 排序约束。
   - `tap1` region explanation 显示 geometry 的 top-k GT-neighborhood enrichment 在 `0/3` 个样本上高于 PASDF。
5. 报告 `docs/document/report/2026-06-13_p5_targeted_case_study_report.md` 的下一步建议是：
   - `cap3`：继续 registration/template robustness。
   - `tap1`：转向 PASDF object score calibration、top-k ratio、score amplitude、GT 稀疏解释。
   - `helmet1`：进入点级定位失败解释。

## 2. 本轮问题定义

本轮不再问“geometry residual 能不能直接提升 PASDF”，而是问三个更窄的问题：

### 2.1 cap3：false positive 是否能靠 top-k 聚合缓解

已知 `cap3_positive9/7/10` 的 PASDF 高分点与 template residual 高分点高度重叠。本轮需要检查：

- 改变 PASDF top-k ratio 后，positive false-positive 是否仍压过 anomaly。
- 如果不同 top-k ratio 下 positive 仍高，说明问题主要不是聚合超参，而是 registration/template mismatch。

### 2.2 tap1：低 object score 是否来自 top-k 口径和 score 幅度

`tap1_broken2/broken3/hole0` 的 GT 附近有 PASDF 局部信号，但 object score 很低。本轮需要检查：

- `1%/2%/5%/10%` top-k ratio 下 anomaly 与 positive 的对象级排序变化。
- top-k 高分点对 GT 的命中率、覆盖率和 enrichment。
- 是否存在一个 PASDF-only 聚合口径能提高 anomaly 排序，同时不引入 positive false-positive。

### 2.3 helmet1：对象级可分但点级弱的定位证据

P3/P5 已显示 `helmet1` object AUROC 高但 pixel AUROC 低，且 GT/background 均值差很小。本轮需要检查：

- top-k 高分点是否集中在 GT 区域。
- 哪些 anomaly 样本的 GT enrichment 低或 GT/background gap 很小。
- `helmet1` 是否与 `tap1` 同属“局部排序弱或 score 幅度弱”，还是另一个 failure mode。

## 3. 本轮不做什么

为保持代码简洁和实验结论干净，本轮明确不做：

1. 不训练新模型。
2. 不做 learned calibration。
3. 不继续 additive geometry fusion。
4. 不把 A2/A3/A4 扩到 40 类。
5. 不新增复杂多模板匹配实现。`cap3` 本轮只用已有 template residual 和 PASDF score 证据判断后续是否值得做多模板。
6. 不提交 `experiments/` 下的大量实验产物；只提交阶段记录和代码。

## 4. 方案选择

### 4.1 备选方案 A：继续扩展 `targeted_p6.py`

优点：复用已有 top-k region utilities。

缺点：`targeted_p6.py` 已经同时包含 registration、hybrid、alpha sweep、region explanation。继续把 PASDF-only calibration 塞进去会让文件职责变混。

### 4.2 备选方案 B：新增轻量 PASDF calibration 模块

优点：

- 只依赖 PASDF point-score NPZ，不依赖 geometry/viz。
- 逻辑边界清楚：读取 score、计算不同 top-k ratio、写 CSV/Markdown。
- 后续可服务 `tap1/helmet1/cap3`，但不引入新训练路径。

缺点：会新增一个分析模块和一个 CLI。

### 4.3 选择

选择方案 B。理由是本轮本质是 PASDF-only score aggregation 和定位诊断，不应该继续扩大 geometry-oriented 的 `targeted_p6.py`。

## 5. 代码框架

新增：

- `src/pcdad/analysis/pasdf_calibration.py`
  - PASDF top-k calibration 的 dataclass、纯函数、CSV/Markdown 渲染。
  - 只复用 `load_pasdf_point_score` 与 `topk_mean`。
- `scripts/run_p6_pasdf_calibration.py`
  - CLI 薄封装，负责参数解析、样本发现、输出文件。
- `tests/test_pasdf_calibration.py`
  - 单元测试核心指标、汇总逻辑和 Markdown/CSV 稳定性。
- `tests/test_run_p6_pasdf_calibration_cli.py`
  - CLI smoke test，使用临时 NPZ，不依赖真实数据。

输出：

- `docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.md`
- `docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.csv`
- `experiments/P6_pasdf_calibration/topk_calibration_records.csv`

## 6. 核心接口设计

### 6.1 PasdfTopKCalibrationRecord

```python
@dataclass(frozen=True)
class PasdfTopKCalibrationRecord:
    class_name: str
    sample_id: str
    label: int
    point_count: int
    gt_point_count: int
    gt_point_ratio: float
    top_ratio: float
    stored_object_score: float
    topk_score: float
    score_mean: float
    score_p95: float
    gt_score_mean: float | None
    background_score_mean: float | None
    gt_background_gap: float | None
    topk_gt_hit_rate: float | None
    gt_coverage: float | None
    gt_enrichment: float | None
```

说明：

- `stored_object_score` 是 NPZ 中 PASDF 导出的原 object score。
- `topk_score` 是本轮按 `top_ratio` 重新计算的 object score。
- `topk_gt_hit_rate` 表示 top-k 点中多少是 GT 点。
- `gt_coverage` 表示 GT 点有多少被 top-k 覆盖。
- `gt_enrichment` 表示 top-k GT 命中率相对随机采样的提升。

### 6.2 PasdfCalibrationSummary

```python
@dataclass(frozen=True)
class PasdfCalibrationSummary:
    class_name: str
    top_ratio: float
    sample_count: int
    anomaly_count: int
    positive_count: int
    mean_anomaly_topk: float | None
    mean_positive_topk: float | None
    min_anomaly_topk: float | None
    max_positive_topk: float | None
    strict_object_pass: bool
    soft_object_pass: bool
    mean_gt_background_gap: float | None
    mean_topk_gt_hit_rate: float | None
    mean_gt_coverage: float | None
    mean_gt_enrichment: float | None
    weak_localization_count: int
```

说明：

- `strict_object_pass`：`min anomaly topk > max positive topk`。
- `soft_object_pass`：`mean anomaly topk > max positive topk`。
- `weak_localization_count`：异常样本中 `gt_enrichment <= 1` 或 GT/background gap 不大于 0 的样本数。

### 6.3 主要函数

```python
def compute_pasdf_topk_calibration_record(
    *,
    score_path: Path,
    top_ratio: float,
) -> PasdfTopKCalibrationRecord:
    ...
```

```python
def build_pasdf_topk_calibration_records(
    *,
    score_paths: Sequence[Path],
    top_ratios: Sequence[float],
) -> tuple[PasdfTopKCalibrationRecord, ...]:
    ...
```

```python
def summarize_pasdf_calibration(
    records: Sequence[PasdfTopKCalibrationRecord],
) -> tuple[PasdfCalibrationSummary, ...]:
    ...
```

```python
def render_pasdf_calibration_markdown(
    *,
    records: Sequence[PasdfTopKCalibrationRecord],
    summaries: Sequence[PasdfCalibrationSummary],
) -> str:
    ...
```

## 7. 指标口径

### 7.1 top-k score

```text
k = max(1, ceil(point_count * top_ratio))
topk_score = mean(largest k PASDF point scores)
```

object score 越高表示越异常。

### 7.2 GT hit rate

```text
topk_gt_hit_rate = top-k 中 GT 点数量 / top-k 点数量
```

### 7.3 GT coverage

```text
gt_coverage = top-k 中 GT 点数量 / 全部 GT 点数量
```

### 7.4 GT enrichment

```text
gt_enrichment = topk_gt_hit_rate / gt_point_ratio
```

若 `gt_enrichment > 1`，说明 top-k 区域比随机点更偏向 GT；若 `<= 1`，说明 PASDF 高分区域对 GT 没有显著集中。

### 7.5 weak localization

异常样本满足任一条件时记为 weak localization：

- `gt_enrichment <= 1`
- `gt_background_gap <= 0`

这个定义故意保守。它不是最终 pixel AUROC，只用于把人工复查样本排出来。

## 8. 实验范围

默认类别：

```text
cap3 tap1 helmet1
```

默认 top-k ratio：

```text
0.01 0.02 0.05 0.10
```

输入来自：

```text
experiments/P5_pasdf_scores/representative/{class}/points/*.npz
```

## 9. 输出文件

### 9.1 records CSV

路径：

```text
experiments/P6_pasdf_calibration/topk_calibration_records.csv
```

用途：保存每个样本、每个 top-k ratio 的完整指标。该文件不提交，只用于本机追溯。

### 9.2 summary CSV

路径：

```text
docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.csv
```

用途：保存类别级、ratio 级汇总，可提交。

### 9.3 summary Markdown

路径：

```text
docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.md
```

用途：中文阶段记录，可提交。

## 10. 测试策略

### 10.1 单元测试

`tests/test_pasdf_calibration.py` 覆盖：

1. 单样本 top-k score、GT hit、coverage、enrichment。
2. positive 样本没有 GT 时 nullable 字段稳定。
3. 多 ratio、多类别 summary 的 strict/soft pass。
4. weak localization 计数。
5. CSV/Markdown 输出列顺序稳定。

### 10.2 CLI 测试

`tests/test_run_p6_pasdf_calibration_cli.py` 使用临时目录写小型 NPZ，验证：

1. CLI 能按 class 发现样本。
2. records CSV、summary CSV、summary Markdown 都能写出。
3. Markdown 包含中文结论和关键样本。

## 11. 执行命令

单测：

```bash
PYTHONPATH=src pytest -q tests/test_pasdf_calibration.py tests/test_run_p6_pasdf_calibration_cli.py
```

真实代表类别运行：

```bash
PYTHONPATH=src python scripts/run_p6_pasdf_calibration.py \
  --score-root experiments/P5_pasdf_scores/representative \
  --classes cap3 tap1 helmet1 \
  --top-ratios 0.01 0.02 0.05 0.10 \
  --records-csv experiments/P6_pasdf_calibration/topk_calibration_records.csv \
  --summary-csv docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.csv \
  --summary-md docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.md
```

质量门：

```bash
PYTHONPATH=src pytest -q
ruff check src scripts tests
black --check src scripts tests
mypy src/pcdad
pre-commit run --all-files
```

## 12. 验收标准

本轮完成后应能回答：

1. `cap3` 的 false positive 是否能通过 top-k ratio 调整缓解；如果不能，应继续归因到 registration/template robustness。
2. `tap1` 是否存在 PASDF-only top-k ratio 能改善 anomaly/positive object 排序。
3. `helmet1` 的点级定位弱是否表现为低 GT enrichment 或低 GT/background gap。
4. 所有新增代码有单测，CLI 能在临时数据和真实代表类别上运行。
5. 新增文档为中文，且与实验数据一致。
