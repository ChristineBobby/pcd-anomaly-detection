# P6 Alpha Sweep And Positive-Aware Gating 架构计划

撰写日期：2026-06-13

适用阶段：P6 targeted diagnostics prototype 之后

## 目录

- [1. 背景与问题](#1-背景与问题)
- [2. 本轮目标](#2-本轮目标)
- [3. 方法选择](#3-方法选择)
- [4. 代码框架](#4-代码框架)
- [5. 核心接口](#5-核心接口)
- [6. 实验样本](#6-实验样本)
- [7. 通过标准](#7-通过标准)
- [8. 输出文件](#8-输出文件)
- [9. 测试策略](#9-测试策略)
- [10. 执行命令](#10-执行命令)

## 1. 背景与问题

P6 targeted diagnostics prototype 的结论是：

- `cap3_positive9/7/10` 的 nearest-neighbor distance residual 明显高于 `cap3` anomaly 对照，支持人工观察到的 registration/template mismatch。
- `tap1` 的 naive additive hybrid 提升了 `tap1_broken2/broken3/hole0` 的 GT/background 分离。
- 但 `tap1_positive0` 的 hybrid object score 为 `1.439421`，高于部分 anomaly，说明 naive additive hybrid 会带来明显 false-positive 风险。

因此下一步不能继续扩大 naive hybrid。必须先做 positive-aware selection：

```text
如果 fusion 提升 anomaly，但同时把 positive 也抬得更高，则不能作为可用方案。
```

## 2. 本轮目标

本轮只解决一个问题：

> 是否存在一个 alpha 或 gating 策略，让 `tap1` anomaly 的 GT/background 分离优于 PASDF，同时 positive object score 不压过 anomaly？

具体目标：

1. 对 alpha 做 sweep，例如 `0.0, 0.1, 0.25, 0.5, 0.75, 1.0`。
2. 对每个 alpha 计算 `tap1_broken2/broken3/hole0` 与 positive 对照的 hybrid object score。
3. 计算 anomaly 的 hybrid GT/background separation gain。
4. 选择满足 positive-aware 约束的候选配置。
5. 若没有配置满足约束，记录为负结果，不扩大实验。

## 3. 方法选择

### 3.1 alpha sweep

保持当前 hybrid 形式：

```text
hybrid = robust_minmax(PASDF) + alpha * robust_minmax(geometry)
```

alpha 越大，geometry 权重越高。

优点：

- 简单、可解释。
- 能直接显示 false-positive 风险随 alpha 增长的趋势。

缺点：

- 不能解决 geometry 对 positive 同样高的问题。
- 若 positive 和 anomaly 的 geometry residual 都高，则 sweep 可能找不到可用 alpha。

### 3.2 positive-aware selection

对每个 alpha 计算：

```text
min_anomaly_hybrid_object
max_positive_hybrid_object
mean_anomaly_hybrid_separation_gain
```

通过条件：

```text
min_anomaly_hybrid_object > max_positive_hybrid_object
mean_anomaly_hybrid_separation_gain > 0
```

如果这个条件过严，可以记录 soft condition：

```text
mean_anomaly_hybrid_object > max_positive_hybrid_object
mean_anomaly_hybrid_separation_gain > 0
```

本轮报告同时给出 strict 和 soft 判断。

### 3.3 gating 暂不实现复杂模型

本轮不训练 gating 模型，不做 learned calibration。原因：

- 当前样本数太少，训练模型没有统计意义。
- P6 目标是验证方向，不是引入新方法导致不可解释。
- 如果 alpha sweep 已经失败，复杂 gating 应等到更多 positive/anomaly 样本后再做。

## 4. 代码框架

复用：

- `src/pcdad/analysis/targeted_p6.py`
- `scripts/run_p6_targeted_diagnostics.py`

新增或扩展：

- `AlphaSweepRecord`
- `AlphaSweepSummary`
- `run_alpha_sweep(...)`
- `write_alpha_sweep_csv(...)`
- `render_alpha_sweep_markdown(...)`
- CLI 参数：
  - `--alpha-grid`
  - `--alpha-sweep-csv`

## 5. 核心接口

### 5.1 AlphaSweepRecord

```python
@dataclass(frozen=True)
class AlphaSweepRecord:
    alpha: float
    class_name: str
    sample_id: str
    label: int
    hybrid_object_score: float
    pasdf_object_score: float
    geometry_object_score: float
    pasdf_separation: float | None
    hybrid_separation: float | None
    separation_gain: float | None
```

### 5.2 AlphaSweepSummary

```python
@dataclass(frozen=True)
class AlphaSweepSummary:
    alpha: float
    anomaly_count: int
    positive_count: int
    min_anomaly_hybrid_object: float | None
    mean_anomaly_hybrid_object: float | None
    max_positive_hybrid_object: float | None
    mean_anomaly_separation_gain: float | None
    strict_pass: bool
    soft_pass: bool
```

### 5.3 run_alpha_sweep

```python
def run_alpha_sweep(
    *,
    score_root: Path,
    template_root: Path,
    anomaly_sample_ids: Sequence[str],
    positive_sample_ids: Sequence[str],
    alpha_grid: Sequence[float],
) -> tuple[AlphaSweepRecord, ...]:
    ...
```

行为：

- 对每个 alpha 和 sample 复用现有 `compute_hybrid_score_record`。
- 不生成 SVG，避免 sweep 产生大量图片。
- 输出 per-sample record。

## 6. 实验样本

Anomaly：

```text
tap1_broken2
tap1_broken3
tap1_hole0
```

Positive：

```text
tap1_positive0
tap1_positive1
tap1_positive2
tap1_positive3
tap1_positive4
```

如果这些 positive NPZ 存在，则优先使用 5 个 positive，而不是只用 `tap1_positive0`。这样能更稳健地评估 false-positive 风险。

## 7. 通过标准

本轮只允许进入更大实验的条件：

1. 至少一个 alpha 满足 `strict_pass=True`。
2. 或者没有 strict pass，但有 soft pass 且人工确认 positive score 未出现明显不可接受抬高。

如果全部失败，则结论是：

```text
tap1 geometry residual 有定位补充价值，但当前 additive fusion 不适合继续扩大。
```

## 8. 输出文件

```text
experiments/P6_alpha_sweep/tap1_alpha_sweep_records.csv
experiments/P6_alpha_sweep/tap1_alpha_sweep_summary.csv
docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.md
docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.csv
```

## 9. 测试策略

新增测试：

- `tests/test_targeted_p6_alpha_sweep.py`
  - 验证 alpha grid 产生正确 record 数。
  - 验证 alpha=0 等价于 PASDF norm object score 方向。
  - 验证 strict/soft pass 判断。
  - 验证 CSV/Markdown 稳定。
- `tests/test_run_p6_alpha_sweep_cli.py`
  - fake NPZ + fake OBJ 验证 CLI 写 summary。

质量门：

```bash
PYTHONPATH=src pytest -q
ruff check src scripts tests
black --check src scripts tests
mypy src/pcdad
pre-commit run --all-files
```

## 10. 执行命令

```bash
PYTHONPATH=src python scripts/run_p6_targeted_diagnostics.py \
  --score-root experiments/P5_pasdf_scores/representative \
  --template-root third_party/PASDF/data/ShapeNetAD \
  --cap3-samples \
    cap3_positive9 cap3_positive7 cap3_positive10 \
    cap3_hole0 cap3_hole1 cap3_broken2 cap3_broken3 \
  --tap1-samples tap1_broken2 tap1_broken3 tap1_hole0 \
  --tap1-positive-samples \
    tap1_positive0 tap1_positive1 tap1_positive2 tap1_positive3 tap1_positive4 \
  --alpha-grid 0.0 0.1 0.25 0.5 0.75 1.0 \
  --output-dir experiments/P6_alpha_sweep \
  --summary-md docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.md \
  --summary-csv docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.csv \
  --alpha-sweep-csv experiments/P6_alpha_sweep/tap1_alpha_sweep_records.csv \
  --max-points 4096
```
