# 复现与证据清单

## 目录

- [1. 环境边界](#1-环境边界)
- [2. 最小复现命令](#2-最小复现命令)
- [3. 证据索引](#3-证据索引)
- [4. 本包内 CSV](#4-本包内-csv)
- [5. 质量门](#5-质量门)
- [6. 未纳入本包的大型产物](#6-未纳入本包的大型产物)

## 1. 环境边界

- Docker/conda 容器用于训练、评估、测试和生成实验产物。
- Git push/pull/fetch 在宿主机执行。
- 大型数据、权重、NPZ、日志和完整实验目录不进入 git。
- 当前交付 tag：`v0.1-p6-delivery`。

## 2. 最小复现命令

### 2.1 PASDF 40 类 baseline

```bash
PYTHONPATH=src CUDA_VISIBLE_DEVICES=0 python scripts/evaluate.py \
  --config configs/experiment/E1_pasdf_baseline.yaml \
  --output-dir experiments/E1_pasdf_baseline/full_40cls
```

### 2.2 P5 score export

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

### 2.3 P5 case study 图像

```bash
PYTHONPATH=src python scripts/visualize_pasdf_scores.py \
  --score-root experiments/P5_pasdf_scores/representative \
  --template-root third_party/PASDF/data/ShapeNetAD \
  --output-dir experiments/P5_case_study \
  --summary-md docs/document/stage_record/2026-06-13_p5_targeted_case_study.md \
  --summary-csv docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv
```

### 2.4 P6 failure-mode closure

```bash
PYTHONPATH=src python scripts/run_p6_failure_mode_closure.py
```

### 2.5 本交付包重建

```bash
python3 docs/document/delivery_pack/2026-06-14_p6_delivery_pack/scripts/build_delivery_pack.py
```

## 3. 证据索引

| 证据 | 本包内路径 | 原始来源 |
|---|---|---|
| P3 40 类评估 CSV | `assets/csv/p3_pasdf_40cls_evaluation_results.csv` | `experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv` |
| P6 evidence index | `assets/csv/p6_delivery_evidence_index.csv` | `docs/document/stage_record/2026-06-14_p6_delivery_evidence_index.csv` |
| P6 failure closure CSV | `assets/csv/p6_failure_mode_closure.csv` | `docs/document/stage_record/2026-06-14_p6_failure_mode_closure.csv` |

## 4. 本包内 CSV

`assets/csv/p3_pasdf_40cls_evaluation_results.csv` 前 8 行预览：

| class | pixel_auc | object_auc |
| --- | --- | --- |
| ashtray0 | 0.9218458730960621 | 1.0 |
| bag0 | 0.9388999079460693 | 0.980952380952381 |
| bottle0 | 0.9496217055310339 | 1.0 |
| bottle1 | 0.9336039342382227 | 1.0 |
| bottle3 | 0.9397082336368436 | 1.0 |
| bowl0 | 0.9680143724369973 | 1.0 |
| bowl1 | 0.9055837068614379 | 0.9851851851851852 |
| bowl2 | 0.8162675393786828 | 1.0 |

## 5. 质量门

最近一次交付阶段在 Docker `0613` 的 `pasdf` 环境中通过：

```text
pytest -q: 114 passed
ruff check src scripts tests: passed
black --check src scripts tests: passed
mypy src/pcdad: passed
```

## 6. 未纳入本包的大型产物

- `data/Anomaly-ShapeNet-v2/`：原始与预处理数据。
- `third_party/PASDF/results/` 与权重：PASDF 官方资产。
- `experiments/P5_pasdf_scores/representative/**/points/*.npz`：点级分数数组。
- 完整 run.log、mesh、checkpoint 和大规模中间产物。
