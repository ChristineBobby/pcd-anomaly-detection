# P6 Targeted Diagnostics

## 结论摘要

- object score 越高表示越异常。
- cap3 registration/template mismatch 先看 sample/template distance residual。
- tap1 PASDF + geometry fusion 先看 hybrid 是否提升 GT/background 分离，同时检查 positive object score 是否被抬高。

## cap3 registration/template mismatch

| sample | label | PASDF object | NN mean | NN p95 | NN p99 | NN top5 mean |
|---|---:|---:|---:|---:|---:|---:|
| `cap3_positive9` | 0 | 0.109517 | 0.006001 | 0.037221 | 0.095074 | 0.073342 |
| `cap3_positive7` | 0 | 0.096982 | 0.004349 | 0.020448 | 0.077369 | 0.054389 |
| `cap3_positive10` | 0 | 0.064902 | 0.002514 | 0.002931 | 0.035992 | 0.020964 |
| `cap3_hole0` | 1 | 0.006392 | 0.001592 | 0.002542 | 0.003038 | 0.003005 |
| `cap3_hole1` | 1 | 0.010446 | 0.001647 | 0.002592 | 0.003623 | 0.003518 |
| `cap3_broken2` | 1 | 0.012887 | 0.001706 | 0.002678 | 0.004526 | 0.003962 |
| `cap3_broken3` | 1 | 0.028583 | 0.003561 | 0.005110 | 0.012814 | 0.009030 |

## tap1 PASDF + geometry fusion

| sample | label | PASDF obj | Geometry obj | Hybrid obj | PASDF GT-bg | Geometry GT-bg | Hybrid GT-bg | SVG |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `tap1_broken2` | 1 | 0.001698 | 0.936926 | 1.289039 | 0.000220 | 0.101950 | 0.580160 | `experiments/P6_targeted_diagnostics/tap1_hybrid_scores/tap1/tap1_broken2_hybrid.svg` |
| `tap1_broken3` | 1 | 0.002379 | 0.931026 | 1.276239 | 0.000246 | 0.102920 | 0.615309 | `experiments/P6_targeted_diagnostics/tap1_hybrid_scores/tap1/tap1_broken3_hybrid.svg` |
| `tap1_hole0` | 1 | 0.001395 | 0.934251 | 1.429934 | 0.000157 | 0.120071 | 0.429856 | `experiments/P6_targeted_diagnostics/tap1_hybrid_scores/tap1/tap1_hole0_hybrid.svg` |
| `tap1_positive0` | 0 | 0.001332 | 0.929091 | 1.439421 | NA | NA | NA | `experiments/P6_targeted_diagnostics/tap1_hybrid_scores/tap1/tap1_positive0_hybrid.svg` |

## 下一步判断

- cap3 positive 中 `cap3_positive9` 的 NN top5 mean 最高，应优先和人工 overlay 结论对照，确认 false positive 是否来自局部模板错位。
- tap1 anomaly 中 `3/3` 个样本的 hybrid GT/background 分离高于 PASDF。
- tap1 positive 对照的 hybrid object score 均值为 `1.439421`；后续扩大实验时必须继续监控 false positive 风险。

## 人工观察纳入后的解释

`cap3_positive9/7/10` 的 nearest-neighbor distance 统计与人工 overlay 观察一致：

- `cap3_positive9` 的 NN top5 mean 为 `0.073342`，显著高于 `cap3_hole0/hole1/broken2/broken3`。
- `cap3_positive7` 的 NN top5 mean 为 `0.054389`，同样高于 anomaly 对照。
- `cap3_positive10` 的 NN top5 mean 为 `0.020964`，低于前两者但仍高于所有 anomaly 对照。

这说明 `cap3` positive 高分不是普通阈值问题。它更像 sample/template 局部错位导致的 residual 放大，尤其与人工看到的帽檐、鸭舌区域局部分布差异一致。后续如果继续处理 `cap3`，应先做 registration/template robustness，而不是直接融合 geometry residual。

`tap1` 的 hybrid 结果同时包含正信号和风险：

- 正信号：三个 anomaly 的 hybrid GT/background 分离都明显高于 PASDF 原始分离。
- 风险：`tap1_positive0` 的 hybrid object score 为 `1.439421`，甚至高于 `tap1_broken2` 和 `tap1_broken3`。

因此，本轮不能宣称 PASDF + geometry fusion 已经解决 `tap1`。更准确的结论是：geometry residual 对异常区域有补充信号，但 naive additive hybrid 会明显抬高 positive score，存在 false-positive 风险。下一步如果继续 fusion，必须加入 calibration 或 positive-aware gating。

## 下一阶段建议

1. `cap3`：暂停 fusion，进入 registration/template mismatch 诊断增强。
2. `tap1`：不要直接扩大 naive additive hybrid；先尝试 alpha sweep、positive-aware threshold 或只在 PASDF 弱响应区域中引入 geometry。
3. 若要进入更大代表类别实验，必须同时报告 anomaly improvement 和 positive false-positive 增量，不能只看 GT/background 分离。
