# P6 PASDF Top-k Calibration

## 结论摘要

- object score 越高表示越异常。
- 本轮只检查 PASDF 自身的 top-k 聚合、score 幅度和 GT 局部命中，不继续 additive geometry fusion。
- `cap3` 没有通过 object 排序约束，优先排查校准或模板问题。
- `cap3` 在 top-k ratio `1.00%` 下有 `5` 个 anomaly 呈现 weak localization。
- `helmet1` 没有通过 object 排序约束，优先排查校准或模板问题。
- `helmet1` 在 top-k ratio `1.00%` 下有 `3` 个 anomaly 呈现 weak localization。
- `tap1` 只有 soft object pass ratio：1.00%, 2.00%, 5.00%, 10.00%，需要复查 positive 边界。
- `tap1` 在 top-k ratio `1.00%` 下有 `2` 个 anomaly 呈现 weak localization。

## 类别与 top-k ratio 汇总

| 类别 | top-k ratio | 样本数 | anomaly | positive | mean anomaly topk | max positive topk | strict | soft | mean GT-bg | mean topk GT hit | mean GT cover | mean GT enrich | weak localization |
|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|
| cap3 | 0.010000 | 34 | 19 | 15 | 0.017041 | 0.098255 | False | False | 0.005412 | 0.428755 | 0.293740 | 29.345380 | 5 |
| cap3 | 0.020000 | 34 | 19 | 15 | 0.012419 | 0.091445 | False | False | 0.005412 | 0.339217 | 0.470016 | 23.477853 | 3 |
| cap3 | 0.050000 | 34 | 19 | 15 | 0.006831 | 0.071249 | False | False | 0.005412 | 0.184916 | 0.624027 | 12.468364 | 2 |
| cap3 | 0.100000 | 34 | 19 | 15 | 0.004177 | 0.042974 | False | False | 0.005412 | 0.098423 | 0.678223 | 6.779749 | 2 |
| helmet1 | 0.010000 | 29 | 14 | 15 | 0.018043 | 0.018515 | False | False | 0.002900 | 0.418990 | 0.145413 | 14.527125 | 3 |
| helmet1 | 0.020000 | 29 | 14 | 15 | 0.015806 | 0.016759 | False | False | 0.002900 | 0.300523 | 0.211024 | 10.540919 | 1 |
| helmet1 | 0.050000 | 29 | 14 | 15 | 0.012362 | 0.014644 | False | False | 0.002900 | 0.235540 | 0.417749 | 8.346837 | 0 |
| helmet1 | 0.100000 | 29 | 14 | 15 | 0.010244 | 0.013020 | False | False | 0.002900 | 0.141942 | 0.501564 | 5.013808 | 0 |
| tap1 | 0.010000 | 33 | 18 | 15 | 0.015977 | 0.001367 | False | True | 0.008790 | 0.590786 | 0.283166 | 28.288964 | 2 |
| tap1 | 0.020000 | 33 | 18 | 15 | 0.012705 | 0.001169 | False | True | 0.008790 | 0.503218 | 0.449980 | 22.477034 | 1 |
| tap1 | 0.050000 | 33 | 18 | 15 | 0.007679 | 0.000911 | False | True | 0.008790 | 0.301965 | 0.631329 | 12.614260 | 1 |
| tap1 | 0.100000 | 33 | 18 | 15 | 0.004301 | 0.000720 | False | True | 0.008790 | 0.169378 | 0.696611 | 6.963564 | 1 |

## 优先复查样本

| 类别 | 样本 | label | top-k ratio | topk score | GT-bg | GT enrich | 原因 |
|---|---|---:|---:|---:|---:|---:|---|
| cap3 | `cap3_broken3` | 1 | 0.010000 | 0.019075 | -0.000658 | 0.000000 | weak localization |
| cap3 | `cap3_broken3` | 1 | 0.020000 | 0.013771 | -0.000658 | 0.000000 | weak localization |
| tap1 | `tap1_concavity6` | 1 | 0.010000 | 0.000899 | -0.000013 | 0.000000 | weak localization |
| tap1 | `tap1_concavity6` | 1 | 0.020000 | 0.000683 | -0.000013 | 0.000000 | weak localization |
| cap3 | `cap3_broken2` | 1 | 0.010000 | 0.006559 | 0.001022 | 0.000000 | weak localization |
| cap3 | `cap3_bulge3` | 1 | 0.010000 | 0.038061 | 0.004049 | 0.000000 | weak localization |
| cap3 | `cap3_concavity3` | 1 | 0.010000 | 0.059377 | 0.003580 | 0.000000 | weak localization |
| cap3 | `cap3_concavity3` | 1 | 0.020000 | 0.051387 | 0.003580 | 0.000000 | weak localization |
| cap3 | `cap3_hole1` | 1 | 0.010000 | 0.005026 | 0.000047 | 0.000000 | weak localization |
| cap3 | `cap3_hole1` | 1 | 0.020000 | 0.003216 | 0.000047 | 0.000000 | weak localization |
| cap3 | `cap3_hole1` | 1 | 0.050000 | 0.001816 | 0.000047 | 0.000000 | weak localization |
| helmet1 | `helmet1_concavity1` | 1 | 0.010000 | 0.017064 | 0.001685 | 0.000000 | weak localization |

## 阶段解读

- `cap3`：最佳候选 top-k ratio 为 `1.00%`。mean anomaly topk 为 `0.017041`，max positive topk 为 `0.098255`，strict=False，soft=False。
- `helmet1`：最佳候选 top-k ratio 为 `1.00%`。mean anomaly topk 为 `0.018043`，max positive topk 为 `0.018515`，strict=False，soft=False。
- `tap1`：最佳候选 top-k ratio 为 `1.00%`。mean anomaly topk 为 `0.015977`，max positive topk 为 `0.001367`，strict=False，soft=True。

## 下一步建议

- `cap3`：top-k ratio 调整没有解决 object 排序问题，继续优先做 registration/template robustness，而不是调 PASDF 聚合超参。
- `tap1`：PASDF-only 聚合有稳定 soft pass，但没有 strict pass；后续应检查 positive 边界样本和低分 anomaly，暂不恢复 additive geometry fusion。
- `helmet1`：mean anomaly 高于 mean positive，但最高 positive 仍压住排序边界；下一步应做点级定位失败解释和 positive 边界复查。
