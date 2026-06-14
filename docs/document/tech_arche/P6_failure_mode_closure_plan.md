# P6 Failure Mode Closure 架构计划

撰写日期：2026-06-14

适用阶段：P6 后续小范围诊断收口与报告证据固化

## 目录

- [1. 背景与输入结论](#1-背景与输入结论)
- [2. 本轮目标](#2-本轮目标)
- [3. 本轮不做什么](#3-本轮不做什么)
- [4. 方案设计](#4-方案设计)
- [5. 代码框架](#5-代码框架)
- [6. 核心接口](#6-核心接口)
- [7. 判定规则](#7-判定规则)
- [8. 实验范围](#8-实验范围)
- [9. 输出文件](#9-输出文件)
- [10. 测试策略](#10-测试策略)
- [11. 执行命令](#11-执行命令)
- [12. 验收标准](#12-验收标准)

## 1. 背景与输入结论

截至 `a8af4ed`，当前实验进度已经完成：

1. P0-P3：PASDF 官方 40 类 baseline 复现完成，mean object AUROC 为 `0.900214149779`，mean pixel AUROC 为 `0.896009030694`。
2. P4：A2/A3/A4 几何增强 smoke 被关闭为负结果，不能直接扩 naive geometry 到 40 类。
3. P5：代表类别 `ashtray0/cap3/helmet1/tap1` 的 PASDF per-point score 已导出。
4. P6 targeted diagnostics：
   - `cap3_positive9/7/10` 的 PASDF 高分区域与 template residual 高分区域高度重叠。
   - `tap1` additive fusion 与 alpha sweep 都没有通过 positive-aware object 排序约束。
   - `tap1` region explanation 显示 geometry 的 top-k GT-neighborhood enrichment 在 `0/3` 个样本上优于 PASDF。
5. P6 PASDF calibration：
   - `cap3` 调整 top-k ratio 后仍没有通过 object 排序约束。
   - `tap1` 在 `1%/2%/5%/10%` top-k ratio 下只有 soft pass，没有 strict pass。
   - `helmet1` mean anomaly 高于 mean positive，但最高 positive 仍压住 object 边界。

因此下一步不是继续寻找新的 fusion 分数，而是把三个代表 failure mode 收口成报告可用的证据链。

## 2. 本轮目标

本轮目标是产出一个可复现的 failure mode closure：

1. `cap3`：确认 failure mode 是 registration/template false positive，而不是 top-k 聚合超参问题。
2. `tap1`：确认 failure mode 是 PASDF 局部有信号但 strict object boundary 不稳，且不支持恢复 additive geometry fusion。
3. `helmet1`：确认 failure mode 是点级定位弱或 positive boundary 混淆，并列出下一步人工复查样本。
4. 输出一份中文 stage record，直接服务最终报告与答辩。

## 3. 本轮不做什么

本轮明确不做：

1. 不训练新模型。
2. 不新增 learned calibration。
3. 不恢复 PASDF + geometry additive fusion。
4. 不扩 A2/A3/A4 到 40 类。
5. 不实现 multi-template/template selection，只判断是否值得进入下一阶段。
6. 不提交 `experiments/` 下的大量明细 CSV 或 SVG；只提交轻量 stage record。

## 4. 方案设计

### 4.1 证据来源

本轮只使用已经存在的两类证据：

- PASDF calibration evidence：来自 `src/pcdad/analysis/pasdf_calibration.py`，包含 top-k score、GT hit、GT coverage、GT enrichment、strict/soft pass。
- cap3 residual evidence：来自 `src/pcdad/analysis/targeted_p6.py`，包含 PASDF/residual top-k overlap、residual top-k bbox ratio、pair distance ratio。

### 4.2 输出层

新增一个轻量汇总模块：

```text
src/pcdad/analysis/failure_modes.py
```

该模块不重新计算复杂几何，只把已有诊断函数输出整合为：

- `FailureModeClosureRecord`：类别级结论。
- `BoundarySampleRecord`：每类最高 positive 和最低 anomaly 的边界样本。
- `WeakLocalizationRecord`：点级定位弱样本。
- `Cap3TemplateMismatchRecord`：cap3 positive false-positive 的 residual overlap 证据。

CLI：

```text
scripts/run_p6_failure_mode_closure.py
```

负责读取代表类别 NPZ、调用模块、写出 CSV/Markdown。

## 5. 代码框架

新增：

- `src/pcdad/analysis/failure_modes.py`
  - failure mode dataclass。
  - class-level closure 汇总。
  - CSV/Markdown 渲染。
- `scripts/run_p6_failure_mode_closure.py`
  - 参数解析、样本发现、输出 stage record。
- `tests/test_failure_modes.py`
  - 纯函数单测，不依赖真实数据。
- `tests/test_run_p6_failure_mode_closure_cli.py`
  - CLI smoke test，使用临时 NPZ 与 template OBJ。

复用：

- `compute_pasdf_topk_calibration_record`
- `summarize_pasdf_calibration`
- `compute_cap3_residual_region_record`
- `topk_indices`

## 6. 核心接口

### 6.1 FailureModeClosureRecord

```python
@dataclass(frozen=True)
class FailureModeClosureRecord:
    class_name: str
    primary_failure_mode: str
    object_boundary_status: str
    localization_status: str
    evidence: str
    next_action: str
```

### 6.2 BoundarySampleRecord

```python
@dataclass(frozen=True)
class BoundarySampleRecord:
    class_name: str
    top_ratio: float
    highest_positive_sample: str | None
    highest_positive_score: float | None
    lowest_anomaly_sample: str | None
    lowest_anomaly_score: float | None
    boundary_margin: float | None
```

`boundary_margin = lowest_anomaly_score - highest_positive_score`。大于 0 表示 strict pass，小于等于 0 表示 positive 边界压住 anomaly。

### 6.3 WeakLocalizationRecord

```python
@dataclass(frozen=True)
class WeakLocalizationRecord:
    class_name: str
    sample_id: str
    top_ratio: float
    gt_background_gap: float | None
    gt_enrichment: float | None
    reason: str
```

### 6.4 Cap3TemplateMismatchRecord

```python
@dataclass(frozen=True)
class Cap3TemplateMismatchRecord:
    sample_id: str
    label: int
    pasdf_object_score: float
    residual_topk_mean: float
    pasdf_residual_topk_overlap: float
    residual_topk_bbox_ratio: float
    residual_topk_mean_pair_distance_ratio: float
    closure_label: str
```

## 7. 判定规则

### 7.1 object boundary

- `strict_pass`：`min anomaly topk > max positive topk`
- `soft_pass`：`mean anomaly topk > max positive topk`
- `failed`：以上都不满足

### 7.2 weak localization

异常样本满足任一条件：

- `gt_enrichment <= 1`
- `gt_background_gap <= 0`

### 7.3 cap3 template mismatch

positive 样本满足以下条件，标记为 strong template-mismatch evidence：

- `pasdf_residual_topk_overlap >= 0.8`
- `pasdf_object_score` 高于同类低分 anomaly

若 overlap 介于 `0.5` 和 `0.8`，标记为 partial evidence。

## 8. 实验范围

默认类别：

```text
cap3 tap1 helmet1
```

默认 top-k ratio：

```text
0.01
```

cap3 residual 样本：

```text
cap3_positive9 cap3_positive7 cap3_positive10
cap3_hole0 cap3_hole1 cap3_broken2 cap3_broken3
```

## 9. 输出文件

轻量 stage record：

```text
docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md
docs/document/stage_record/2026-06-14_p6_failure_mode_closure.csv
```

本机明细：

```text
experiments/P6_failure_mode_closure/failure_mode_closure_records.csv
```

## 10. 测试策略

1. 单元测试 closure rule：
   - strict/soft/failed object boundary。
   - weak localization 识别。
   - cap3 strong/partial/no evidence。
2. Markdown/CSV 测试：
   - 中文标题和结论存在。
   - 表格列顺序稳定。
3. CLI smoke：
   - 临时写入 cap3/tap1/helmet1 小型 NPZ。
   - 临时写入 cap3 template OBJ。
   - 确认 summary md/csv 可生成。

## 11. 执行命令

单测：

```bash
PYTHONPATH=src pytest -q tests/test_failure_modes.py tests/test_run_p6_failure_mode_closure_cli.py
```

真实运行：

```bash
PYTHONPATH=src python scripts/run_p6_failure_mode_closure.py \
  --score-root experiments/P5_pasdf_scores/representative \
  --template-root third_party/PASDF/data/ShapeNetAD \
  --classes cap3 tap1 helmet1 \
  --top-ratio 0.01 \
  --records-csv experiments/P6_failure_mode_closure/failure_mode_closure_records.csv \
  --summary-csv docs/document/stage_record/2026-06-14_p6_failure_mode_closure.csv \
  --summary-md docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md
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

1. 三个类别都有明确 failure mode closure。
2. `cap3` 能给出 template mismatch 证据强度。
3. `tap1` 能说明为什么不恢复 additive geometry fusion。
4. `helmet1` 能列出点级定位弱和 positive boundary 样本。
5. stage record 为中文，结论与已有 P5/P6 实验数据一致。
