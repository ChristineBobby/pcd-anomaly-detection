# P4 PASDF Voxel Sweep Summary

## Scope

- Sweep root: `experiments/P4_registration_sweep`
- Runs parsed: 11

## Interpretation

- `cap3` is registration-sensitive. `voxel_size=0.04` removes Open3D warning events and raises object AUROC from the P3 full-run value `0.550877` to `0.771930`. It still remains below 0.8, so geometry/SDF residual analysis is still needed, but registration is a confirmed contributor.
- `cap4` improves only mildly at larger voxels. The best run is `voxel_size=0.05` with object AUROC `0.687719`, and Open3D warnings remain. This points to registration instability plus a non-registration error source.
- `tap1` is not helped by the official PASDF voxel value in this small run. `0.03` and `0.04` are both near `0.77` object AUROC with no warnings, so the next analysis should inspect scorer behavior and defect morphology.
- `helmet2` has no warnings in the single-class run, but object AUROC drops to `0.640580` versus the P3 full-run value `0.776812`. This should be treated as a reproducibility/stability signal and rerun before drawing a model-level conclusion.

## Best By Class

| Class | Voxel Size | Pixel AUROC | Object AUROC | Warnings | Warning Samples |
|---|---:|---:|---:|---:|---:|
| cap3 | 0.040 | 0.855043 | 0.771930 | 0 | 0 |
| cap4 | 0.050 | 0.887033 | 0.687719 | 7 | 1 |
| helmet2 | 0.030 | 0.801255 | 0.640580 | 0 | 0 |
| tap1 | 0.030 | 0.903114 | 0.774074 | 0 | 0 |

## All Runs

| Class | Voxel Size | Pixel AUROC | Object AUROC | Warnings | Warning Samples |
|---|---:|---:|---:|---:|---:|
| cap3 | 0.020 | 0.851986 | 0.771930 | 12 | 1 |
| cap3 | 0.030 | 0.851825 | 0.610526 | 8 | 1 |
| cap3 | 0.040 | 0.855043 | 0.771930 | 0 | 0 |
| cap3 | 0.050 | 0.842822 | 0.624561 | 0 | 0 |
| cap4 | 0.020 | 0.882415 | 0.610526 | 2 | 1 |
| cap4 | 0.030 | 0.888519 | 0.589474 | 6 | 1 |
| cap4 | 0.040 | 0.881236 | 0.677193 | 8 | 1 |
| cap4 | 0.050 | 0.887033 | 0.687719 | 7 | 1 |
| helmet2 | 0.030 | 0.801255 | 0.640580 | 0 | 0 |
| tap1 | 0.030 | 0.903114 | 0.774074 | 0 | 0 |
| tap1 | 0.040 | 0.900786 | 0.770370 | 0 | 0 |
