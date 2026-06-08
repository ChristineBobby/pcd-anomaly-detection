# P4 失败分析与几何增强执行计划

撰写日期：2026-06-08
适用阶段：P4 失败分析、registration 诊断、几何增强开发
当前基线：PASDF official-weight full 40-class evaluation

---

## 目录

- [1. 阶段目标](#1-阶段目标)
- [2. Entry 复核](#2-entry-复核)
- [3. 代码框架与接口](#3-代码框架与接口)
- [4. 执行任务](#4-执行任务)
- [5. Artifact 策略](#5-artifact-策略)
- [6. 当前 P4 优先类别](#6-当前-p4-优先类别)
- [7. 验收标准](#7-验收标准)

---

## 1. 阶段目标

P4 不直接从几何增强开始。当前 PASDF baseline 已达到论文 object AUROC 目标，因此 P4 的第一目标是解释 baseline 的低分类别和 Open3D registration warning，再用这些证据指导几何增强。

P4 的执行顺序：

1. 固化轻量结果记录，避免只有 ignored experiment 目录可查。
2. 建立 PASDF failure analysis CLI，结构化解析 `evaluation_results.csv` 和 `run.log`。
3. 识别 object/pixel failure classes、Open3D warning 分布和优先分析类别。
4. 再进入法向残差、多尺度曲率残差、top-k/局部一致性聚合。

---

## 2. Entry 复核

已满足：

```text
P3 PASDF full 40-class evaluation: done
mean_object_auc: 0.900214149779
mean_pixel_auc: 0.896009030694
P3 metric DoD: met
```

本地资产：

```text
results csv: experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv
run log: experiments/E1_pasdf_baseline/full_40cls/run.log
generated PASDF config: experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml
fixed dataset: data/Anomaly-ShapeNet-v2/dataset/16384
```

注意：

- `experiments/E1_pasdf_baseline/` 被 `.gitignore` 忽略。
- P4 轻量 summary 应写入 `docs/document/stage_record/`。
- 大日志、权重、数据和大图不入 git，只记录路径、大小、hash 或生成命令。

---

## 3. 代码框架与接口

### 3.1 核心分析模块

```text
src/pcdad/analysis/pasdf_failures.py
```

职责：

- 读取 PASDF 官方 `evaluation_results.csv`。
- 解析 PASDF `run.log` 中 Open3D “Too few correspondences” warning。
- 根据当前 `Evaluating [class]` 上下文把 warning 归因到类别。
- 按阈值输出 object failure、pixel failure、min object、min pixel 和 P4 priority classes。
- 渲染轻量 Markdown summary。

核心数据结构：

```python
@dataclass(frozen=True)
class FailureThresholds:
    pixel_auc: float = 0.85
    object_auc: float = 0.8

@dataclass(frozen=True)
class ClassFailureRecord:
    class_name: str
    pixel_auc: float
    object_auc: float
    open3d_warning_count: int = 0

@dataclass(frozen=True)
class PasdfFailureSummary:
    class_count: int
    mean_pixel_auc: float
    mean_object_auc: float
    pixel_failures: tuple[ClassFailureRecord, ...]
    object_failures: tuple[ClassFailureRecord, ...]
    min_pixel: ClassFailureRecord
    min_object: ClassFailureRecord
```

### 3.2 CLI 入口

```text
scripts/analyze_pasdf_failures.py
```

职责：

- 解析 CLI 参数。
- 调用 `pcdad.analysis.pasdf_failures`。
- 输出 Markdown 到 stage record。
- 在 stdout 打印 class count、mean AUROC、Open3D warning count 和 priority classes。

默认命令：

```bash
PYTHONPATH=src python scripts/analyze_pasdf_failures.py
```

默认输出：

```text
docs/document/stage_record/2026-06-08_p4_failure_summary.md
```

---

## 4. 执行任务

### Task 1：P4 failure analysis 基础设施

状态：已实现。

文件：

```text
src/pcdad/analysis/__init__.py
src/pcdad/analysis/pasdf_failures.py
scripts/analyze_pasdf_failures.py
tests/test_pasdf_failure_analysis.py
tests/test_analyze_pasdf_failures.py
```

验证：

```bash
PYTHONPATH=src pytest tests/test_pasdf_failure_analysis.py -q
PYTHONPATH=src pytest tests/test_analyze_pasdf_failures.py -q
```

### Task 2：生成当前 P4 failure summary

命令：

```bash
PYTHONPATH=src python scripts/analyze_pasdf_failures.py \
  --results experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv \
  --log experiments/E1_pasdf_baseline/full_40cls/run.log \
  --output docs/document/stage_record/2026-06-08_p4_failure_summary.md
```

输出：

```text
docs/document/stage_record/2026-06-08_p4_failure_summary.md
```

### Task 3：registration warning 细化分析

下一步执行。

目标：

- 从 warning summary 进入 per-class 诊断。
- 优先查看 warning 多、object/pixel 低的类别。
- 设计对齐前后 overlay、Chamfer/NN 距离和 `voxel_size` 小网格扫描。

### Task 4：几何增强模块

后续执行。

目标文件：

```text
src/pcdad/geometry/normals.py
src/pcdad/geometry/curvature.py
src/pcdad/scoring/aggregate.py
src/pcdad/scoring/geometric.py
```

原则：

- 先 TDD，再实现。
- 先合成小样本验证几何行为，再接 PASDF 输出。
- 所有 k 值、权重、top-k 比例进入 YAML。

---

## 5. Artifact 策略

进入 git：

- `docs/document/stage_record/*_p4_failure_summary.md`
- 轻量 CSV/JSON summary，若后续需要可放到 `docs/document/stage_record/artifacts/`
- 配置 YAML
- 分析脚本和单测

不进入 git：

- `experiments/E1_pasdf_baseline/full_40cls/run.log`
- 大图、mesh、点云、权重、数据集
- 大量 per-sample score 文件

---

## 6. 当前 P4 优先类别

根据 P3 baseline：

```text
object_auc < 0.8:
cap3, cap4, cap5, helmet2, microphone0, shelf0, tap1

pixel_auc < 0.85:
bowl2, cap3, headset1, helmet0, helmet1, helmet2, vase1
```

优先级建议：

1. `cap3`：object 最低，是检测失败优先案例。
2. `helmet1`：pixel 最低但 object 高，是定位失败优先案例。
3. `helmet2`：object 和 pixel 都低。
4. `tap1`、`cap4`、`cap5`：object 低，适合 registration/voxel_size 诊断。

---

## 7. 验收标准

Task 1-2 的 DoD：

- failure analysis 核心单测通过。
- CLI 单测通过。
- 当前 P3 full 40-class 结果可生成 P4 failure summary。
- summary 写入 `docs/document/stage_record/`，可被 git 跟踪。
- `ruff/black/mypy/pytest/pre-commit` 通过。

P4 完整 DoD 见 `docs/document/SOP_engineering_workflow.md`。
