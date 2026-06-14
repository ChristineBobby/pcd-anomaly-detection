# P6 交付证据包架构计划

撰写日期：2026-06-14

适用阶段：P6 交付归档、最终报告证据索引与答辩冻结

## 目录

- [1. 背景](#1-背景)
- [2. 本轮目标](#2-本轮目标)
- [3. 本轮不做什么](#3-本轮不做什么)
- [4. 证据包设计](#4-证据包设计)
- [5. 代码框架](#5-代码框架)
- [6. 核心接口](#6-核心接口)
- [7. 默认证据条目](#7-默认证据条目)
- [8. 输出文件](#8-输出文件)
- [9. 测试策略](#9-测试策略)
- [10. 执行命令](#10-执行命令)
- [11. 验收标准](#11-验收标准)

## 1. 背景

截至 `2d3f338 feat(analysis): add p6 failure mode closure`，项目已经完成：

1. P0-P3：PASDF 官方 40 类 baseline 复现完成，mean object AUROC 为 `0.900214149779`，mean pixel AUROC 为 `0.896009030694`。
2. P4：A2/A3/A4 naive geometry smoke 被收口为负结果，不进入 40 类主表。
3. P5：代表类别 PASDF per-point score、cap3 template overlay、tap1 PASDF vs geometry 并排图已产出。
4. P6：targeted diagnostics、positive-aware alpha sweep、region explanation、PASDF top-k calibration、failure-mode closure 已完成。

当前已经不适合继续堆叠新方法。P6 的主要任务应转为：把已有结论、指标、stage record、实验产物路径、生成命令和 commit hash 组织成一个可复查的交付证据包。

## 2. 本轮目标

本轮目标是生成一个轻量、可提交、可复现的交付证据包：

1. 建立最终证据索引 CSV：每条结论都能追溯到 stage record、轻量 CSV、`experiments/` artifact 路径、生成命令和 commit hash。
2. 生成中文 Markdown 证据包：用目录、阶段状态表、关键结论表和下一步建议服务最终报告。
3. 更新 README 的结果摘要和复现入口，让外部读者能快速理解当前可复现范围。
4. 保持 `experiments/`、`data/`、权重和完整日志不入库，只在证据包中记录路径。

## 3. 本轮不做什么

本轮明确不做：

1. 不新增 anomaly score 或 fusion 算法。
2. 不重新跑 40 类 PASDF baseline。
3. 不把 `experiments/` 下的大型 CSV、SVG、日志或 NPZ 提交到 git。
4. 不引入数据库、复杂配置系统或额外依赖。
5. 不把旧的 `2026-06-10_p5_targeted_case_study.*` 未跟踪残留文件纳入本阶段提交。

## 4. 证据包设计

### 4.1 数据来源

证据包只读取和记录已有产物：

- `docs/document/stage_record/` 下的阶段记录与轻量 CSV。
- `docs/document/report/2026-06-13_p5_targeted_case_study_report.md`。
- `experiments/` 下的本机实验产物路径。
- 当前 git commit hash。

### 4.2 记录粒度

一条证据记录对应一个可答辩结论，而不是一个文件。例如：

- P3 baseline 达到 PASDF 论文级 object AUROC。
- P4 naive geometry enhancement 不进入主表。
- P6 alpha sweep 拒绝 additive geometry fusion。
- P6 failure-mode closure 固定 cap3/tap1/helmet1 三类后续解释。

### 4.3 路径策略

CSV/Markdown 中使用 repo-relative 路径，便于在服务器和远端仓库之间迁移。

`experiments/` 路径允许不存在于 git，但生成器会标注本机是否存在：

- `tracked_exists`：stage record/report/README 等应入库文件是否存在。
- `artifact_exists`：`experiments/` 本机产物是否存在。

如果 artifact 不存在，证据记录仍保留路径和生成命令，状态标为 `missing_artifact`，不阻塞文档生成。

## 5. 代码框架

新增：

- `src/pcdad/analysis/delivery_evidence.py`
  - 定义 `DeliveryEvidenceRecord`。
  - 构建默认证据记录。
  - 写出证据索引 CSV。
  - 渲染中文 Markdown 证据包。
- `scripts/build_p6_delivery_evidence_pack.py`
  - 解析输出路径和 commit hash。
  - 调用 analysis 模块生成 CSV/Markdown。
- `tests/test_delivery_evidence.py`
  - 测试默认记录、路径状态、CSV/Markdown 稳定性。
- `tests/test_build_p6_delivery_evidence_pack_cli.py`
  - CLI smoke test，使用临时输出目录，不依赖真实数据。

更新：

- `README.md`
  - 增加当前核心结果、P6 证据包入口、最小复现命令和 artifact 管理说明。

## 6. 核心接口

### 6.1 DeliveryEvidenceRecord

```python
@dataclass(frozen=True)
class DeliveryEvidenceRecord:
    stage: str
    evidence_id: str
    claim: str
    conclusion: str
    status: str
    stage_record_path: str
    result_csv_path: str
    artifact_paths: tuple[str, ...]
    generation_command: str
    commit_hash: str
    notes: str
```

### 6.2 build_default_delivery_evidence_records

```python
def build_default_delivery_evidence_records(
    *,
    repo_root: str | Path,
    commit_hash: str,
) -> tuple[DeliveryEvidenceRecord, ...]:
    ...
```

该函数只组织证据，不修改文件。

### 6.3 write_delivery_evidence_csv

```python
def write_delivery_evidence_csv(
    records: Sequence[DeliveryEvidenceRecord],
    path: str | Path,
) -> Path:
    ...
```

CSV 字段顺序固定，便于最终报告引用。

### 6.4 render_delivery_evidence_markdown

```python
def render_delivery_evidence_markdown(
    records: Sequence[DeliveryEvidenceRecord],
    *,
    title: str = "P6 Delivery Evidence Pack",
) -> str:
    ...
```

Markdown 使用中文说明，英文标题保留阶段名以匹配现有 P6 文件命名。

## 7. 默认证据条目

默认证据条目覆盖以下阶段：

1. P3 PASDF baseline：`docs/document/stage_record/2026-06-08_p0_p3_stage_check.md` 与 `experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv`。
2. P4 geometry closure：`docs/document/stage_record/2026-06-09_p4_geometry_closure.md`。
3. P5 PASDF score export：`docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md`。
4. P5 targeted case study：`docs/document/report/2026-06-13_p5_targeted_case_study_report.md` 与 `docs/document/stage_record/2026-06-13_p5_targeted_case_study.md`。
5. P6 targeted diagnostics：`docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.md`。
6. P6 alpha sweep：`docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.md`。
7. P6 region explanation：`docs/document/stage_record/2026-06-13_p6_region_explanation_summary.md`。
8. P6 PASDF calibration：`docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.md`。
9. P6 failure-mode closure：`docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md`。

## 8. 输出文件

本轮新增轻量结果：

```text
docs/document/stage_record/2026-06-14_p6_delivery_evidence_index.csv
docs/document/stage_record/2026-06-14_p6_delivery_evidence_pack.md
docs/document/report/2026-06-14_final_delivery_report_draft.md
```

其中 report draft 可以复用 evidence pack 的核心表，并补充最终报告的建议结构。

## 9. 测试策略

1. 单元测试：
   - 默认证据条目数量和关键 `evidence_id` 稳定。
   - `tracked_exists` 和 `artifact_exists` 能正确反映临时文件状态。
   - CSV 字段顺序稳定。
   - Markdown 包含目录、核心结果和下一步建议。
2. CLI 测试：
   - 临时输出 CSV/MD。
   - 指定 fake commit hash。
   - 确认 stdout 输出写入路径和记录数量。

## 10. 执行命令

测试：

```bash
PYTHONPATH=src pytest -q tests/test_delivery_evidence.py tests/test_build_p6_delivery_evidence_pack_cli.py
```

真实生成：

```bash
PYTHONPATH=src python scripts/build_p6_delivery_evidence_pack.py \
  --repo-root . \
  --output-csv docs/document/stage_record/2026-06-14_p6_delivery_evidence_index.csv \
  --output-md docs/document/stage_record/2026-06-14_p6_delivery_evidence_pack.md \
  --report-draft docs/document/report/2026-06-14_final_delivery_report_draft.md
```

全量质量门：

```bash
PYTHONPATH=src pytest -q
ruff check src scripts tests
black --check src scripts tests
mypy src/pcdad
```

## 11. 验收标准

本轮完成后应满足：

1. 证据索引 CSV 和中文 Markdown 证据包已生成并进入 git。
2. 每条关键结论都有 stage record、CSV 或 artifact 路径、生成命令和 commit hash。
3. README 指向最小复现入口和 P6 evidence pack。
4. 新增代码不依赖真实数据集或 GPU，单测可在普通 Python 环境中快速运行。
5. 质量门通过；若某个检查因当前环境缺依赖失败，需在 stage record 和最终回复中明确记录。
