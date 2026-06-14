# 实验结果与失败模式分析

## 目录

- [1. 结果总览](#1-结果总览)
- [2. P4 naive geometry 为什么关闭](#2-p4-naive-geometry-为什么关闭)
- [3. cap3：registration/template false positive](#3-cap3registrationtemplate-false-positive)
- [4. tap1：PASDF soft boundary 与 fusion 拒绝](#4-tap1pasdf-soft-boundary-与-fusion-拒绝)
- [5. helmet1：点级定位弱](#5-helmet1点级定位弱)
- [6. 最终 failure-mode closure](#6-最终-failure-mode-closure)

## 1. 结果总览

| 问题 | 结论 | 证据 |
|---|---|---|
| PASDF baseline 是否达标 | 达标 | 40 类 mean object AUROC=`0.900214149779` |
| 几何 residual 是否能直接提升主表 | 当前不能 | P4 A2/A3/A4 positive control 同样高分 |
| cap3 失败原因 | template/registration false positive | positive overlay 错位 + residual top-k overlap 高 |
| tap1 是否恢复 additive fusion | 不恢复 | alpha sweep 全部 strict=False/soft=False |
| helmet1 如何处理 | 报告中作为 localization weakness 局限案例 | calibration 和 closure 记录 |

## 2. P4 naive geometry 为什么关闭

P4 A2/A3/A4 尝试把 distance、normal、curvature residual 组合成几何异常分数。结果显示，几何分数能放大局部差异，但不能稳定区分 anomaly 和 positive control。这类负结果很重要，因为它阻止我们把一个看起来有热力图响应、但对象级排序不可靠的分数扩大到 40 类主实验。

![P4 A4 cap3 anomaly](assets/02_p4_geometry/a4_cap3_bending0.svg)

![P4 A4 cap3 positive](assets/02_p4_geometry/a4_cap3_positive0.svg)

## 3. cap3：registration/template false positive

### 3.1 现象

`cap3_positive9/7/10` 是正常样本，但 PASDF object score 很高：

| sample | label | PASDF object score | 解释 |
|---|---:|---:|---|
| `cap3_positive9` | 0 | `0.109517` | 最高优先级 false positive |
| `cap3_positive7` | 0 | `0.096982` | 第二优先级 false positive |
| `cap3_positive10` | 0 | `0.064902` | 少量 top-k 高分点拉高 object score |

### 3.2 图像证据

![cap3 positive9 overlay](assets/03_cap3_overlay/cap3_positive9_template_overlay.svg)

![cap3 positive7 overlay](assets/03_cap3_overlay/cap3_positive7_template_overlay.svg)

![cap3 positive10 overlay](assets/03_cap3_overlay/cap3_positive10_template_overlay.svg)

人工观察和图像都显示：红蓝点云不是良好重合状态，错位集中在帽檐、鸭舌状突出结构等局部区域。这说明 `cap3` 的高分不适合简单解释为阈值过低，而更像 template/canonical alignment 问题。

### 3.3 定量证据

| sample | label | PASDF object | residual overlap | closure |
|---|---:|---:|---:|---|
| `cap3_positive9` | 0 | `0.109517` | `0.902439` | strong positive template mismatch |
| `cap3_positive7` | 0 | `0.096982` | `0.932927` | strong positive template mismatch |
| `cap3_positive10` | 0 | `0.064902` | `0.975610` | strong positive template mismatch |

这些 positive 样本的 PASDF top-k 高分点和 template residual top-k 高分点高度重叠，直接支持 registration/template false positive 结论。

## 4. tap1：PASDF soft boundary 与 fusion 拒绝

### 4.1 P5 图像证据

![tap1 broken2 PASDF vs geometry](assets/05_tap1_comparison/tap1_broken2_pasdf_vs_geometry.svg)

![tap1 broken3 PASDF vs geometry](assets/05_tap1_comparison/tap1_broken3_pasdf_vs_geometry.svg)

![tap1 hole0 PASDF vs geometry](assets/05_tap1_comparison/tap1_hole0_pasdf_vs_geometry.svg)

P5 图像上，geometry residual 右图更容易出现红色高分区域，PASDF 左图整体更蓝。但这只是视觉现象，不能直接推出 geometry 对对象级判断更好。

### 4.2 P6 positive-aware 诊断

alpha sweep 的核心约束是：提升 anomaly 的同时，不能把 positive object score 一起抬高。结果所有 alpha 都没有通过 strict 或 soft positive-aware gating。

| alpha | min anomaly obj | mean anomaly obj | max positive obj | strict | soft |
|---:|---:|---:|---:|---|---|
| `0.0` | `0.651312` | `0.701104` | `0.799581` | False | False |
| `0.5` | `0.934062` | `0.988108` | `1.097702` | False | False |
| `1.0` | `1.276239` | `1.331737` | `1.439421` | False | False |

下图是 positive counterexample。它说明 hybrid 分数能把正常样本也打高，不能直接作为最终对象级分数。

![tap1 positive0 hybrid](assets/07_p6_hybrid/tap1_positive0_hybrid.svg)

## 5. helmet1：点级定位弱

`helmet1` 的 mean anomaly 可以高于 positive 均值，但最高 positive 仍压住 object boundary。因此它不适合继续用简单 top-k 或 fusion 调参处理，更适合作为报告中的点级定位局限案例。

![helmet1 concavity4 PASDF heatmap](assets/06_helmet1/helmet1_concavity4_pasdf_score.svg)

## 6. 最终 failure-mode closure

| 类别 | Failure mode | Object boundary | 后续处理 |
|---|---|---|---|
| `cap3` | registration/template false positive | failed | 优先 template selection / registration robustness |
| `tap1` | soft object boundary with low-amplitude local PASDF signal | soft_pass | 不恢复 additive fusion，保留 PASDF calibration 结论 |
| `helmet1` | point-level localization weakness | failed | 补 heatmap/GT overlay 复查，作为局限案例 |
