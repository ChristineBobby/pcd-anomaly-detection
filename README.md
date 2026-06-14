# PCD Anomaly Detection

Production-grade course project for unsupervised 3D point-cloud anomaly detection.

## Goal

The project targets object-level and point-level anomaly detection on Anomaly-ShapeNet.
The main backbone is PASDF, reproduced from official weights first, then extended with
geometry-aware scoring and systematic analysis.

## Scope

- Main dataset: Anomaly-ShapeNet, official 40-class protocol.
- Main backbone: PASDF.
- Comparison anchor: PO3AD, with Point-MAE as a fallback.
- Project contributions: PASDF reproduction, geometry residual diagnostics,
  positive-aware failure analysis, and category-specific failure-mode closure.

## Current Results

As of `2026-06-14`, the frozen Anomaly-ShapeNet 40-class PASDF baseline is:

| Method | Protocol | Mean object AUROC | Mean pixel AUROC | Evidence |
|---|---|---:|---:|---|
| PASDF official weights | Anomaly-ShapeNet 40 classes | `0.900214149779` | `0.896009030694` | `docs/document/stage_record/2026-06-08_p0_p3_stage_check.md` |

The P4-P6 analysis is frozen as a negative/diagnostic result:

- A2/A3/A4 naive geometry enhancement did not stably separate anomaly samples from
  positive controls, so it is not expanded to the 40-class main table.
- `tap1` additive PASDF + geometry fusion is rejected by positive-aware alpha sweep.
- `cap3` is closed as a registration/template false-positive case.
- `tap1` is closed as a PASDF soft-boundary and low-amplitude local-signal case.
- `helmet1` is closed as point-localization weakness with positive-boundary confusion.

Final evidence index:

```text
docs/document/stage_record/2026-06-14_p6_delivery_evidence_pack.md
docs/document/stage_record/2026-06-14_p6_delivery_evidence_index.csv
docs/document/report/2026-06-14_final_delivery_report_draft.md
```

## Repository Layout

```text
configs/          YAML configs for data, models, and experiments
src/pcdad/        Project package
scripts/          Thin command wrappers
tests/            Fast unit tests
third_party/      Git submodules for external repositories
docs/             Project documents
data/             Local datasets, ignored by git
experiments/      Local experiment outputs, ignored by git
```

## Quick Start

```bash
make setup
make test
make lint
```

If the container does not provide `make`, use the equivalent Python commands:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m black --check .
python -m mypy src/pcdad
```

The PASDF runtime environment is created in P1. P0 only verifies the repository scaffold,
Python package import, lint configuration, and CI wiring.

## Reproduce Key Artifacts

Run experiments and tests inside the Docker/conda environment. Git push/pull should be
done from the host terminal.

PASDF 40-class baseline:

```bash
PYTHONPATH=src CUDA_VISIBLE_DEVICES=0 python scripts/evaluate.py \
  --config configs/experiment/E1_pasdf_baseline.yaml \
  --output-dir experiments/E1_pasdf_baseline/full_40cls
```

P6 delivery evidence pack:

```bash
PYTHONPATH=src python scripts/build_p6_delivery_evidence_pack.py \
  --repo-root . \
  --output-csv docs/document/stage_record/2026-06-14_p6_delivery_evidence_index.csv \
  --output-md docs/document/stage_record/2026-06-14_p6_delivery_evidence_pack.md \
  --report-draft docs/document/report/2026-06-14_final_delivery_report_draft.md
```

## Reproducibility Rules

Each experiment must have a config under `configs/experiment/` and a run directory under
`experiments/{expid}_{date}_{githash}/`. Run directories must contain the config snapshot,
git hash, environment lock, logs, metrics CSV, and key visualizations.

Datasets, checkpoints, SDF samples, logs, and generated meshes are not committed. They are
reproduced from documented links, configs, and lock files.
