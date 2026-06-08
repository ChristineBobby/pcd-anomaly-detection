# P4 PASDF Voxel Sweep 执行计划

## 记录范围

本次是小规模诊断 sweep，不是 40 类调参。

输入基线：

- 结果 CSV：`experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv`
- 运行日志：`experiments/E1_pasdf_baseline/full_40cls/run.log`
- Sweep 根目录：`experiments/P4_registration_sweep`
- 摘要输出：`docs/document/stage_record/2026-06-08_p4_voxel_sweep_summary.md`
- CSV 输出：`docs/document/stage_record/2026-06-08_p4_voxel_sweep_summary.csv`

## 选择类别

主要 registration warning 类别：

- `cap3`：object AUROC 最低，且有 8 个 Open3D warning 事件。
- `cap4`：object AUROC 第二低，且有 6 个 Open3D warning 事件。

低 object AUROC 但 P3 日志中没有 Open3D warning 的对照类别：

- `tap1`：object AUROC 低于 0.8，官方 PASDF voxel size 与默认值不同。
- `helmet2`：object 和 pixel AUROC 都偏低，但 P3 日志中没有 Open3D warning。

## Sweep 网格

- `cap3`: `0.02, 0.03, 0.04, 0.05`
- `cap4`: `0.02, 0.03, 0.04, 0.05`
- `tap1`: `0.03, 0.04`
- `helmet2`: `0.03`

总共 11 个 PASDF run。这个网格包含默认 `0.03`、官方逐类 voxel size，以及两个 warning 较多的 cap 类别附近的粗粒度备选值。

## 解释规则

- 如果 object AUROC 提升且 warning 减少，registration 参数敏感性很可能是真实原因之一。
- 如果 warning 减少但 AUROC 不提升，Open3D warning 只能说明稳定性风险，不一定是主导误差来源。
- 如果没有 warning 但 AUROC 变化明显，应检查 scorer 行为、GT 分布和缺陷形态，不要只盯 registration。
- 如果某个类别在所有 voxel size 下都偏低，应进入几何残差或 SDF 残差分析。

## 命令

命令由下面的脚本生成：

```bash
PYTHONPATH=src python scripts/plan_pasdf_voxel_sweep.py \
  --max-classes 7
```

本阶段只执行上面列出的子集，并用下面的命令汇总：

```bash
PYTHONPATH=src python scripts/summarize_pasdf_sweep.py \
  --classes cap3 cap4 tap1 helmet2
```
