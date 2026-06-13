# P6 Region Explanation

## 结论摘要

- 本轮不再扩大 additive fusion，而是检查局部高分区域是否贴近 GT 或模板残差。
- tap1 region-level explanation 用 top-k GT/GT-neighborhood 指标判断 geometry 是否更像局部解释信号。
- cap3 residual region diagnostics 用 PASDF/residual top-k overlap 判断 false positive 是否来自模板错位。

## tap1 region-level explanation

| sample | label | GT点数 | radius | PASDF GT hit | Geometry GT hit | PASDF GT cover | Geometry GT cover | PASDF neighbor | Geometry neighbor | PASDF neigh enrich | Geometry neigh enrich |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `tap1_broken2` | 1 | 26 | 0.021398 | 0.019512 | 0.006098 | 0.615385 | 0.192308 | 0.050000 | 0.006098 | 6.113433 | 0.745541 |
| `tap1_broken3` | 1 | 43 | 0.021418 | 0.036585 | 0.010976 | 0.697674 | 0.209302 | 0.089024 | 0.015854 | 8.786600 | 1.564737 |
| `tap1_hole0` | 1 | 87 | 0.021321 | 0.046341 | 0.024390 | 0.436782 | 0.229885 | 0.178049 | 0.026829 | 9.627562 | 1.450728 |

## cap3 residual region diagnostics

| sample | label | PASDF object | residual topk mean | residual topk p95 | PASDF/residual overlap | residual bbox ratio | residual pair ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| `cap3_positive9` | 0 | 0.109517 | 0.073342 | 0.115427 | 0.986585 | 0.459868 | 0.127015 |
| `cap3_positive7` | 0 | 0.096982 | 0.054389 | 0.094158 | 0.989024 | 0.497670 | 0.131435 |
| `cap3_positive10` | 0 | 0.064902 | 0.020964 | 0.052750 | 0.903659 | 0.999944 | 0.235032 |
| `cap3_hole0` | 1 | 0.006392 | 0.003005 | 0.004936 | 0.269512 | 0.996477 | 0.356347 |
| `cap3_hole1` | 1 | 0.010446 | 0.003518 | 0.007867 | 0.326829 | 0.998097 | 0.361764 |
| `cap3_broken2` | 1 | 0.012887 | 0.003962 | 0.009887 | 0.440244 | 0.999043 | 0.373308 |
| `cap3_broken3` | 1 | 0.028583 | 0.009030 | 0.022729 | 0.635366 | 0.992880 | 0.343603 |

## 下一步判断

- tap1 中 `0/3` 个样本的 geometry GT-neighborhood enrichment 高于 PASDF；当前结果不支持把 geometry 作为主局部解释信号。
- cap3 中 `4/7` 个样本的 PASDF/residual top-k overlap 不低于 0.5；positive 样本若 overlap 高，应继续优先排查模板错位。
