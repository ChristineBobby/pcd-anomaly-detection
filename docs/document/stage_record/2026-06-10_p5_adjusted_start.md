# P5 调整启动记录

记录日期：2026-06-10

## 1. 对照 SOP 的阶段判断

P4 已经完成几何基础设施、A2/A3/A4 配置化 smoke、代表类别输出和单测，但 P4 closure 的实测结论不支持把 A2/A3/A4 直接扩展到 40 类：

- `cap3/tap1/helmet1/ashtray0` 的代表类别 smoke 没有稳定拉开异常样本与 positive control。
- normal/curvature 加权主要放大分数尺度，没有稳定改善排序。
- 当前曲率实现为 CPU PCA，多尺度 16k 点 smoke 成本偏高。

因此 P5 当前不按原 SOP 的“直接 A2/A3/A4 全量消融”执行，而是先进入 P5 调整主线：

1. 导出 PASDF per-sample/per-point score。
2. 用样本级统计定位 false positive、false negative 和 GT 内外分数倒挂样本。
3. 只对 PASDF 明确失败的样本做 targeted geometry 复查。
4. 并行准备 Real3D-AD dry-run。

执行依据已写入：

```text
docs/document/P5_adjusted_experiment_execution.md
```

## 2. 已新增代码框架

新增纯分析模块：

```text
src/pcdad/analysis/pasdf_scores.py
```

职责：

- 定义 `PasdfSampleScore`。
- 计算单样本 object/top-k/均值/p95/max/GT 内外均值。
- 写稳定字段顺序的 sample-level CSV。
- 渲染中文 Markdown stage summary。

新增导出脚本：

```text
scripts/export_pasdf_scores.py
```

职责：

- 运行时延迟导入官方 PASDF 的 dataset、registration 和 `SDFScorer`。
- 每个类别只初始化一次 PASDF scorer。
- 输出 `experiments/P5_pasdf_scores/{class}/sample_scores.csv`。
- 可选输出 `experiments/P5_pasdf_scores/{class}/points/{sample_id}.npz`，包含 aligned points、GT mask、PASDF point scores、label、object score 和原始 sample path。
- 输出轻量 stage record Markdown/CSV。

新增测试：

```text
tests/test_pasdf_score_export.py
tests/test_export_pasdf_scores.py
```

覆盖：

- top-k、p95、GT 内外均值统计。
- positive 样本无 GT 点时的空值处理。
- 空分数、长度不一致、非法 top-k 的报错。
- CSV 字段顺序。
- Markdown 类别摘要和优先复查样本。
- CLI 在 fake PASDF runtime 下写 summary CSV/Markdown 和 point NPZ。

## 3. 当前验证状态

已在宿主机完成：

```bash
python3 -m py_compile src/pcdad/analysis/pasdf_scores.py scripts/export_pasdf_scores.py tests/test_pasdf_score_export.py tests/test_export_pasdf_scores.py
git diff --check
```

结果：通过。

在用户新启动的 Docker 容器 `b3b4c371c25d`（名称 `0609`）中完成：

```bash
PYTHONPATH=src pytest tests/test_pasdf_score_export.py tests/test_export_pasdf_scores.py -q
PYTHONPATH=src pytest -q
ruff check src scripts tests
black --check src scripts tests
mypy src/pcdad
pre-commit run --all-files
```

结果：

- 新增测试：`7 passed`
- 全量测试：`73 passed`
- `ruff check`：通过
- `black --check`：通过
- `mypy src/pcdad`：通过
- `pre-commit run --all-files`：通过

## 4. 下一步命令

已导出代表类别 PASDF score：

```bash
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}
PYTHONPATH=src python scripts/export_pasdf_scores.py \
  --config experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml \
  --pasdf-root third_party/PASDF \
  --classes cap3 helmet1 tap1 ashtray0 \
  --output-dir experiments/P5_pasdf_scores/representative \
  --summary-md docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md \
  --summary-csv docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.csv \
  --save-point-scores
```

导出结果：

- 类别：`cap3/helmet1/tap1/ashtray0`
- 样本数：125
- 点级 NPZ：125 个，位于 `experiments/P5_pasdf_scores/representative/**/points/*.npz`，不进入 git。
- 轻量 summary：
  - `docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md`
  - `docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.csv`

下一批分析重点：

- `cap3/tap1`：object-level 异常与 positive 是否分不开。
- `helmet1`：GT 内外 score 是否倒挂，解释 pixel AUROC 低但 object AUROC 高。
- `ashtray0`：高分稳定类别作为 sanity check。
