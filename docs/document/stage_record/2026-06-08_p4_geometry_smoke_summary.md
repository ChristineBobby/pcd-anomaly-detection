# P4 几何 Smoke 摘要

## 结论说明

本次 smoke 使用 distance-only 几何 residual：每个测试点到 `template0` 的 nearest-neighbor 距离，经 robust min-max 归一化后做 top-k object score。目的不是替代 PASDF，而是验证样本级几何诊断链路是否可用。

当前结论：

- `cap3/cap4/tap1` 的异常样本 object score 只比 positive control 略高，区分度不足，不能作为 P5 直接提升指标的证据。
- 部分 `broken` 样本的 GT 区域 point score 明显高于背景，例如 `cap3_broken2`、`tap1_broken2`、`tap1_broken3`，说明局部距离 residual 对缺损类异常有信号。
- `bending/bulge` 样本不稳定，部分 GT 区域均值低于背景，说明单 template distance residual 容易受整体形变、模板差异和采样分布影响。
- 下一步如果继续几何增强，应优先做 normal/curvature residual 与多 template/registration 对齐对照，而不是直接把 distance-only object score 融入 PASDF。

可视化产物保存在 ignored 目录：

```text
experiments/P4_geometry_smoke/svg/
```

## 类别摘要

| 类别 | Template | 样本数 | Anomaly Object Score 均值 | Positive Object Score 均值 |
|---|---|---:|---:|---:|
| cap3 | cap3_template0 | 4 | 0.929643 | 0.924108 |
| cap4 | cap4_template0 | 4 | 0.919016 | 0.895146 |
| tap1 | tap1_template0 | 4 | 0.939148 | 0.922196 |

## 样本明细

| 类别 | 样本 | 类型 | 是否异常 | GT 异常点 | Object Score | Max Point Score | Mean NN Distance | Max NN Distance | GT Score Mean | BG Score Mean |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| cap3 | cap3_bending0 | bending | True | 629 | 0.911897 | 1.000000 | 0.092735 | 0.333515 | 0.280577 | 0.315843 |
| cap3 | cap3_broken2 | broken | True | 42 | 0.921592 | 1.000000 | 0.126252 | 0.404545 | 0.854893 | 0.341542 |
| cap3 | cap3_broken3 | broken | True | 44 | 0.955440 | 1.000000 | 0.105140 | 0.263243 | 0.363016 | 0.428059 |
| cap3 | cap3_positive0 | positive | False | 0 | 0.924108 | 1.000000 | 0.091384 | 0.333852 | NA | 0.314994 |
| cap4 | cap4_bending0 | bending | True | 868 | 0.881129 | 1.000000 | 0.096207 | 0.286727 | 0.447793 | 0.365205 |
| cap4 | cap4_broken2 | broken | True | 56 | 0.951870 | 1.000000 | 0.106249 | 0.275066 | 0.424651 | 0.428147 |
| cap4 | cap4_broken3 | broken | True | 14 | 0.924050 | 1.000000 | 0.099207 | 0.314343 | 0.348281 | 0.347636 |
| cap4 | cap4_positive0 | positive | False | 0 | 0.895146 | 1.000000 | 0.094461 | 0.285534 | NA | 0.368367 |
| tap1 | tap1_broken2 | broken | True | 26 | 0.937521 | 1.000000 | 0.171865 | 0.367455 | 0.972597 | 0.481975 |
| tap1 | tap1_broken3 | broken | True | 43 | 0.956616 | 1.000000 | 0.190919 | 0.394963 | 0.793200 | 0.516039 |
| tap1 | tap1_bulge0 | bulge | True | 462 | 0.923307 | 1.000000 | 0.130373 | 0.376195 | 0.171370 | 0.356696 |
| tap1 | tap1_positive0 | positive | False | 0 | 0.922196 | 1.000000 | 0.129698 | 0.375735 | NA | 0.348580 |
