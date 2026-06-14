# P6 Failure Mode Closure

## 结论摘要

- 本轮不恢复 additive geometry fusion，也不扩 40 类 hybrid。
- `cap3` 按 registration/template false positive 收口。
- `tap1` 按 PASDF soft object boundary 与低幅度局部信号收口。
- `helmet1` 按点级定位弱和 positive boundary 混淆收口。

## 类别闭环结论

| 类别 | Failure mode | Object boundary | Localization | Evidence | Next action |
|---|---|---|---|---|---|
| cap3 | registration/template false positive | failed | 5 weak-localization anomaly samples | top-k calibration failed; cap3 positive residual overlap should be checked | continue registration/template robustness; do not tune PASDF top-k only |
| helmet1 | point-level localization weakness | failed | 3 weak-localization anomaly samples | mean anomaly can be high but positive boundary still overlaps | audit weak-localization anomalies and high positive boundary samples |
| tap1 | soft object boundary with low-amplitude local PASDF signal | soft_pass | 2 weak-localization anomaly samples | PASDF-only calibration soft-passes; additive geometry fusion remains rejected | audit positive boundary and low-score anomalies; keep geometry as diagnostic only |

## Object Boundary 样本

| 类别 | top-k ratio | highest positive | positive score | lowest anomaly | anomaly score | margin |
|---|---:|---|---:|---|---:|---:|
| cap3 | 0.010000 | `cap3_positive9` | 0.098255 | `cap3_hole0` | 0.002774 | -0.095481 |
| tap1 | 0.010000 | `tap1_positive7` | 0.001367 | `tap1_broken2` | 0.000467 | -0.000900 |
| helmet1 | 0.010000 | `helmet1_positive6` | 0.018515 | `helmet1_concavity4` | 0.015434 | -0.003081 |

## Weak Localization 样本

| 类别 | 样本 | top-k ratio | GT-bg | GT enrich | 原因 |
|---|---|---:|---:|---:|---|
| cap3 | `cap3_broken2` | 0.010000 | 0.001022 | 0.000000 | gt_enrichment<=1 |
| cap3 | `cap3_broken3` | 0.010000 | -0.000658 | 0.000000 | gt_enrichment<=1;gt_background_gap<=0 |
| cap3 | `cap3_bulge3` | 0.010000 | 0.004049 | 0.000000 | gt_enrichment<=1 |
| cap3 | `cap3_concavity3` | 0.010000 | 0.003580 | 0.000000 | gt_enrichment<=1 |
| cap3 | `cap3_hole1` | 0.010000 | 0.000047 | 0.000000 | gt_enrichment<=1 |
| tap1 | `tap1_concavity6` | 0.010000 | -0.000013 | 0.000000 | gt_enrichment<=1;gt_background_gap<=0 |
| tap1 | `tap1_hole0` | 0.010000 | 0.000156 | 0.000000 | gt_enrichment<=1 |
| helmet1 | `helmet1_concavity1` | 0.010000 | 0.001685 | 0.000000 | gt_enrichment<=1 |
| helmet1 | `helmet1_concavity2` | 0.010000 | 0.000093 | 0.393834 | gt_enrichment<=1 |
| helmet1 | `helmet1_concavity4` | 0.010000 | 0.000402 | 0.000000 | gt_enrichment<=1 |

## cap3 Template Mismatch 证据

说明：只有 label=0 的 positive 样本会被解释为 false-positive template mismatch；label=1 的 anomaly 行用于对照 residual/PASDF overlap，不作为 false-positive 证据。

| 样本 | label | PASDF object | residual topk mean | overlap | bbox ratio | pair ratio | closure |
|---|---:|---:|---:|---:|---:|---:|---|
| `cap3_positive9` | 0 | 0.109517 | 0.108291 | 0.902439 | 0.253991 | 0.070628 | strong_positive_template_mismatch |
| `cap3_positive7` | 0 | 0.096982 | 0.088546 | 0.932927 | 0.247716 | 0.070634 | strong_positive_template_mismatch |
| `cap3_positive10` | 0 | 0.064902 | 0.047493 | 0.975610 | 0.294513 | 0.083563 | strong_positive_template_mismatch |
| `cap3_hole0` | 1 | 0.006392 | 0.004198 | 0.689024 | 0.987707 | 0.318130 | anomaly_residual_overlap_control |
| `cap3_hole1` | 1 | 0.010446 | 0.006353 | 0.878049 | 0.684899 | 0.255302 | anomaly_residual_overlap_control |
| `cap3_broken2` | 1 | 0.012887 | 0.007817 | 0.829268 | 0.708517 | 0.224815 | anomaly_residual_overlap_control |
| `cap3_broken3` | 1 | 0.028583 | 0.019507 | 0.969512 | 0.359087 | 0.108537 | anomaly_residual_overlap_control |

## 下一步

- `cap3`：进入 registration/template robustness 方案设计，优先考虑 template selection 或局部对齐诊断。
- `tap1`：保留 PASDF calibration 结论，不恢复 naive geometry fusion。
- `helmet1`：补充 heatmap/GT overlay 人工复查，服务最终报告。
