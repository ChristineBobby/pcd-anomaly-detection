# P5 PASDF 样本级分数导出摘要

## 记录范围

- 样本数：125
- 类别数：4
- 异常样本数：65
- Positive 样本数：60
- 类别：`ashtray0`, `cap3`, `helmet1`, `tap1`

## 类别摘要

| 类别 | 样本数 | 异常数 | Positive 数 | Object 均值 | 异常 Object 均值 | Positive Object 均值 | GT 内均值 | 背景均值 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ashtray0 | 29 | 14 | 15 | 0.029624 | 0.056610 | 0.004438 | 0.015485 | 0.000788 |
| cap3 | 34 | 19 | 15 | 0.030657 | 0.029329 | 0.032340 | 0.006380 | 0.001139 |
| helmet1 | 29 | 14 | 15 | 0.022112 | 0.025223 | 0.019209 | 0.008710 | 0.005838 |
| tap1 | 33 | 18 | 15 | 0.013925 | 0.023089 | 0.002928 | 0.008978 | 0.000146 |

## 优先复查样本

| 类别 | 样本 | Label | Object Score | GT 内均值 | 背景均值 | 原因 |
|---|---|---:|---:|---:|---:|---|
| cap3 | `cap3_positive9` | 0 | 0.109517 | NA | 0.004619 | Positive object score 偏高 |
| cap3 | `cap3_positive7` | 0 | 0.096982 | NA | 0.003096 | Positive object score 偏高 |
| cap3 | `cap3_positive10` | 0 | 0.064902 | NA | 0.001150 | Positive object score 偏高 |
| cap3 | `cap3_positive13` | 0 | 0.042084 | NA | 0.002488 | Positive object score 偏高 |
| cap3 | `cap3_positive6` | 0 | 0.036149 | NA | 0.003199 | Positive object score 偏高 |
| cap3 | `cap3_positive4` | 0 | 0.027145 | NA | 0.000544 | Positive object score 偏高 |
| helmet1 | `helmet1_positive6` | 0 | 0.026289 | NA | 0.006124 | Positive object score 偏高 |
| cap3 | `cap3_positive11` | 0 | 0.021955 | NA | 0.000503 | Positive object score 偏高 |
| cap3 | `cap3_positive12` | 0 | 0.021630 | NA | 0.000485 | Positive object score 偏高 |
| helmet1 | `helmet1_positive4` | 0 | 0.019029 | NA | 0.005515 | Positive object score 偏高 |

## 人工复查结论

### 1. `cap3` 是对象级排序失败的首要目标

`cap3` 的异常 Object 均值为 `0.029329`，Positive Object 均值为 `0.032340`，positive 均值反而更高。这与 P3 full 40-class 中 `cap3` object AUROC 低一致。

优先复查 positive 高分样本：

| 样本 | Object Score | 背景均值 | 判断 |
|---|---:|---:|---|
| `cap3_positive9` | 0.109517 | 0.004619 | false-positive 候选 |
| `cap3_positive7` | 0.096982 | 0.003096 | false-positive 候选 |
| `cap3_positive10` | 0.064902 | 0.001150 | false-positive 候选 |

优先复查 anomaly 低分样本：

| 样本 | Object Score | GT 内均值 | 背景均值 | 判断 |
|---|---:|---:|---:|---|
| `cap3_hole0` | 0.006392 | 0.000711 | 0.000257 | 低分异常 |
| `cap3_hole1` | 0.010446 | 0.000392 | 0.000345 | GT/背景几乎贴住 |
| `cap3_broken2` | 0.012887 | 0.001386 | 0.000365 | 低分异常 |
| `cap3_broken3` | 0.028583 | 0.001887 | 0.002546 | GT 内均值低于背景 |

下一步应把 `cap3_positive9/7/10` 与 `cap3_hole0/hole1/broken2/broken3` 作为 targeted geometry 和 registration overlay 的首批样本。

### 2. `helmet1` 更像点级定位弱，而不是对象级完全失败

`helmet1` 的异常 Object 均值为 `0.025223`，Positive Object 均值为 `0.019209`，对象级仍有分离；但 GT 内均值 `0.008710` 与背景均值 `0.005838` 差距较小。

优先复查 GT 内外差最弱样本：

| 样本 | Object Score | GT 内均值 | 背景均值 | GT-背景差 |
|---|---:|---:|---:|---:|
| `helmet1_concavity2` | 0.018686 | 0.006295 | 0.006202 | 0.000093 |
| `helmet1_concavity4` | 0.018856 | 0.006366 | 0.005964 | 0.000402 |
| `helmet1_concavity3` | 0.023174 | 0.006518 | 0.005588 | 0.000930 |

下一步应重点看这些 concavity 样本的 heatmap 是否扩散到正常曲面，判断 PASDF score 是否被整体曲率或模板差异污染。

### 3. `tap1` 对象级分离存在，但局部异常分数很弱

`tap1` 的异常 Object 均值为 `0.023089`，Positive Object 均值为 `0.002928`，对象级分离明显；但 `hole/broken` 类样本点级分数很弱。

优先复查样本：

| 样本 | Object Score | GT 内均值 | 背景均值 | 判断 |
|---|---:|---:|---:|---|
| `tap1_hole0` | 0.001395 | 0.000266 | 0.000109 | 低分异常 |
| `tap1_broken2` | 0.001698 | 0.000261 | 0.000041 | 低分异常 |
| `tap1_broken3` | 0.002379 | 0.000286 | 0.000040 | 低分异常 |
| `tap1_concavity6` | 0.002765 | 0.000048 | 0.000061 | GT 内均值低于背景 |

这些样本适合和 P4 geometry smoke 对照：`tap1_broken2` 在几何 residual 中曾出现局部正信号，应优先生成 PASDF score heatmap 与几何 score heatmap 的并排图。

### 4. `ashtray0` 可作为 sanity check

`ashtray0` 的异常 Object 均值为 `0.056610`，Positive Object 均值为 `0.004438`，分离清楚；GT 内均值 `0.015485` 明显高于背景均值 `0.000788`。下一步主要用它作为正常工作样例，不作为失败分析主目标。

## 下一步

1. 生成 `cap3_positive9/7/10`、`cap3_hole0/hole1/broken2/broken3` 的 PASDF heatmap、GT overlay 和 registration overlay。
2. 生成 `helmet1_concavity2/4/3` 的 PASDF heatmap，检查点级 score 是否扩散到正常背景。
3. 对 `tap1_broken2/broken3/hole0` 做 PASDF score 与 P4 geometry score 并排对照。
4. 暂不扩 A2/A3/A4 到 40 类，先完成上述 targeted case study。
