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
- Project contributions: normal residuals, multi-scale curvature residuals, top-k/local
  consistency aggregation, PAM contribution analysis, and failure analysis by category
  and defect type.

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

## Reproducibility Rules

Each experiment must have a config under `configs/experiment/` and a run directory under
`experiments/{expid}_{date}_{githash}/`. Run directories must contain the config snapshot,
git hash, environment lock, logs, metrics CSV, and key visualizations.

Datasets, checkpoints, SDF samples, logs, and generated meshes are not committed. They are
reproduced from documented links, configs, and lock files.
