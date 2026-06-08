# P4 PASDF Voxel Sweep 结果摘要

## 记录范围

- Sweep 根目录：`experiments/P4_registration_sweep`
- 已解析 run 数：11

## 结果解释

- `cap3` 对 registration 参数敏感。`voxel_size=0.04` 消除了 Open3D warning，并把 object AUROC 从 P3 full-run 的 `0.550877` 提升到 `0.771930`。不过它仍低于 0.8，所以后续仍需要做几何残差或 SDF 残差分析；registration 已经可以确认是原因之一。
- `cap4` 在更大的 voxel 下只有小幅改善。最佳 run 是 `voxel_size=0.05`，object AUROC 为 `0.687719`，但 Open3D warning 仍然存在。这说明它同时有 registration 不稳定和非 registration 的误差来源。
- `tap1` 在这次小实验中没有从官方 PASDF voxel size 获益。`0.03` 和 `0.04` 的 object AUROC 都在 `0.77` 附近，且没有 warning；下一步应看 scorer 行为和缺陷形态。
- `helmet2` 单类 run 没有 warning，但 object AUROC 为 `0.640580`，低于 P3 full-run 的 `0.776812`。这应先视为可复现性或稳定性信号，复跑后再下模型层面的结论。

## 各类别最佳结果

| 类别 | Voxel Size | Pixel AUROC | Object AUROC | Warning 数 | Warning 样本数 |
|---|---:|---:|---:|---:|---:|
| cap3 | 0.040 | 0.855043 | 0.771930 | 0 | 0 |
| cap4 | 0.050 | 0.887033 | 0.687719 | 7 | 1 |
| helmet2 | 0.030 | 0.801255 | 0.640580 | 0 | 0 |
| tap1 | 0.030 | 0.903114 | 0.774074 | 0 | 0 |

## 全部 Run

| 类别 | Voxel Size | Pixel AUROC | Object AUROC | Warning 数 | Warning 样本数 |
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
