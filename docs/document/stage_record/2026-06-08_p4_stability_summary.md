# P4 PASDF 稳定性复核摘要

## 记录范围

- 稳定性实验根目录：`experiments/P4_stability`
- 已解析 run 数：3

## 结果解释

- `helmet2` 三次单类复跑的 mean object AUROC 为 `0.640580`，低于 P3 full-run 中记录的 `0.776812`。
- 三次 run 的 object AUROC 范围为 `0.579710` 到 `0.689855`，标准差为 `0.045708`，说明单类评估存在明显波动。
- 三次 run 都没有 Open3D “Too few correspondences” warning，因此当前问题不能归因于 Open3D warning。
- 下一步分析 `helmet2` 时应优先检查单类评估与 full-run 评估路径差异、registration 非确定性、SDF scorer 行为和样本缺陷形态。暂时不把 `helmet2` 作为稳定的几何增强正例。

## 类别稳定性摘要

| 类别 | Run 数 | Mean Pixel AUROC | Mean Object AUROC | Std Object AUROC | Min Object AUROC | Max Object AUROC | Warning 总数 |
|---|---:|---:|---:|---:|---:|---:|---:|
| helmet2 | 3 | 0.804011 | 0.640580 | 0.045708 | 0.579710 | 0.689855 | 0 |

## 全部 Run

| 类别 | Run ID | Pixel AUROC | Object AUROC | Warning 数 | Warning 样本数 | Run 目录 |
|---|---|---:|---:|---:|---:|---|
| helmet2 | run_001 | 0.831341 | 0.652174 | 0 | 0 | `experiments/P4_stability/helmet2/run_001` |
| helmet2 | run_002 | 0.783644 | 0.579710 | 0 | 0 | `experiments/P4_stability/helmet2/run_002` |
| helmet2 | run_003 | 0.797047 | 0.689855 | 0 | 0 | `experiments/P4_stability/helmet2/run_003` |
