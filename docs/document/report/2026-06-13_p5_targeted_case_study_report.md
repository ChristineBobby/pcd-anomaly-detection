# P5 Targeted Case Study 技术报告

日期：2026-06-13

## 目录

- [1. 本报告要回答的问题](#1-本报告要回答的问题)
- [2. 你要看的图在哪里](#2-你要看的图在哪里)
- [3. 本轮我们做了什么](#3-本轮我们做了什么)
- [4. 图应该怎么看](#4-图应该怎么看)
- [5. cap3 positive false positive 分析](#5-cap3-positive-false-positive-分析)
- [6. tap1 PASDF vs geometry 分析](#6-tap1-pasdf-vs-geometry-分析)
- [7. 人工判读补充](#7-人工判读补充)
- [8. P6 定量诊断补充](#8-p6-定量诊断补充)
- [9. 当前结论修正](#9-当前结论修正)
- [10. 这些结果代表什么](#10-这些结果代表什么)
- [11. 下一步建议](#11-下一步建议)
- [12. 需要你人工确认的事项](#12-需要你人工确认的事项)
- [13. 本轮代码与验证](#13-本轮代码与验证)

## 1. 本报告要回答的问题

P5 前一轮 PASDF score export 告诉我们两个现象：

1. `cap3` 的正常样本被 PASDF 打了很高的 object score，尤其是 `cap3_positive9/7/10`。
2. `tap1_broken2/broken3/hole0` 的 PASDF object score 很低，但这些样本确实有局部缺陷。

所以本轮不是继续盲目扩实验，而是做 targeted case study：

- 对 `cap3_positive9/7/10` 生成 sample/template overlay，检查 false positive 是否来自 registration 或 template mismatch。
- 对 `tap1_broken2/broken3/hole0` 生成 PASDF score 与 geometry distance score 的并排图，检查几何 residual 是否能补充 PASDF 的弱响应。

核心问题是：原计划是否继续？我的判断是继续，但需要先把 P5 的人工判读做完，再进入 P6 的小范围定量诊断，暂时不要直接扩成 40 类大规模融合。

## 2. 你要看的图在哪里

这 6 张图不在 `docs` 目录下，而是在实验产物目录：

```text
/home/xiaobo.xia/JiafengWu/code_folder/area1/Anomaly/experiments/P5_case_study/
```

绝对路径如下：

| 用途 | 样本 | 绝对路径 |
|---|---|---|
| cap3 overlay | `cap3_positive9` | `/home/xiaobo.xia/JiafengWu/code_folder/area1/Anomaly/experiments/P5_case_study/template_overlay/cap3/cap3_positive9_template_overlay.svg` |
| cap3 overlay | `cap3_positive7` | `/home/xiaobo.xia/JiafengWu/code_folder/area1/Anomaly/experiments/P5_case_study/template_overlay/cap3/cap3_positive7_template_overlay.svg` |
| cap3 overlay | `cap3_positive10` | `/home/xiaobo.xia/JiafengWu/code_folder/area1/Anomaly/experiments/P5_case_study/template_overlay/cap3/cap3_positive10_template_overlay.svg` |
| tap1 comparison | `tap1_broken2` | `/home/xiaobo.xia/JiafengWu/code_folder/area1/Anomaly/experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken2_pasdf_vs_geometry.svg` |
| tap1 comparison | `tap1_broken3` | `/home/xiaobo.xia/JiafengWu/code_folder/area1/Anomaly/experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken3_pasdf_vs_geometry.svg` |
| tap1 comparison | `tap1_hole0` | `/home/xiaobo.xia/JiafengWu/code_folder/area1/Anomaly/experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_hole0_pasdf_vs_geometry.svg` |

下面这份 Markdown 已经直接嵌入这些 SVG。若编辑器的 Markdown 预览不显示 SVG，可以用上面的绝对路径在浏览器中打开。

## 3. 本轮我们做了什么

本轮新增了一个 P5 case-study 工具链：

1. 读取 P5 已经导出的 PASDF per-point score NPZ。
2. 为所有 targeted sample 生成 PASDF heatmap。
3. 对 `cap3_positive9/7/10` 读取 PASDF template OBJ，生成 sample/template overlay。
4. 对 `tap1_broken2/broken3/hole0` 计算点到 template 的 distance-only geometry residual，再生成 PASDF vs geometry 并排图。
5. 输出 Markdown/CSV 阶段记录，保留关键数值和 SVG 路径。

本轮产物数量：

- PASDF heatmap：13 个。
- cap3 template overlay：3 个。
- tap1 PASDF vs geometry：3 个。
- 总 SVG：19 个。

注意：`experiments/P5_case_study/` 是实验产物目录，被 `.gitignore` 排除；git 中只记录了代码、测试、设计文档和阶段记录。

## 4. 图应该怎么看

### 4.1 cap3 template overlay 怎么看

cap3 overlay 图里：

- 红点是当前 sample，也就是 `cap3_positive9/7/10` 的 registered point cloud。
- 蓝点是 PASDF 的 `cap3_template0` template vertices。
- 如果红蓝整体对齐很好，但 PASDF object score 仍然很高，问题更可能在 PASDF score calibration 或 latent representation。
- 如果红蓝存在明显整体错位、旋转偏差、尺度不一致、局部形状不匹配，问题更可能是 registration/template mismatch。

因为这 3 个都是 positive 正常样本，理论上不应该被打高分。它们的 overlay 是判断 false positive 来源的关键。

### 4.2 PASDF vs geometry 图怎么看

tap1 并排图里：

- 左半边是 PASDF per-point score。
- 右半边是 distance-only geometry score。
- 点颜色越偏暖，表示该面板内部的 score 越高；越偏蓝，表示越低。
- 黑色粗边点是 GT anomaly point。

这类图不是为了证明 geometry 已经是最终模型，而是为了回答一个诊断问题：

如果 PASDF 左图对 GT 区域响应弱，而 geometry 右图在 GT 区域更集中，那么说明几何 residual 可以作为后续局部解释或非加性 gating 的候选补充信号。

## 5. cap3 positive false positive 分析

### 5.1 数值概览

| sample | label | PASDF object score | score mean | p95 | 解释 |
|---|---:|---:|---:|---:|---|
| `cap3_positive9` | 0 | 0.109517 | 0.004619 | 0.038568 | 最高优先级 false positive |
| `cap3_positive7` | 0 | 0.096982 | 0.003096 | 0.020172 | 第二优先级 false positive |
| `cap3_positive10` | 0 | 0.064902 | 0.001150 | 0.001088 | 第三优先级 false positive |

这里的 label 是 0，代表正常样本。正常样本却拿到很高 object score，说明 PASDF 在 `cap3` 上存在明确的 false-positive 风险。

### 5.2 `cap3_positive9` overlay

![cap3_positive9 template overlay](../../../experiments/P5_case_study/template_overlay/cap3/cap3_positive9_template_overlay.svg)

需要观察：

- 红蓝两组点是否整体重合。
- 是否有某个局部区域红点明显外扩或蓝点缺失。
- 是否有整体旋转、平移、尺度偏差。

如果这张图里红蓝不重合明显，那么 `cap3_positive9` 的高分更可能是配准或模板问题；如果重合较好，则高分更像 PASDF score 本身误判。

### 5.3 `cap3_positive7` overlay

![cap3_positive7 template overlay](../../../experiments/P5_case_study/template_overlay/cap3/cap3_positive7_template_overlay.svg)

`cap3_positive7` 的 object score 也很高，达到 `0.096982`。它和 `cap3_positive9` 一起看，可以判断 false positive 是个别样本问题，还是 `cap3` template 或 canonical alignment 的系统问题。

### 5.4 `cap3_positive10` overlay

![cap3_positive10 template overlay](../../../experiments/P5_case_study/template_overlay/cap3/cap3_positive10_template_overlay.svg)

`cap3_positive10` 的 mean 很低但 object score 达到 `0.064902`，这通常意味着：不是全局都高，而是少量 top-k 点非常高。人工看图时要注意是否存在局部错位或局部模板不覆盖。

### 5.5 cap3 小结

`cap3` 的问题不是单一问题，而是两层问题：

1. 正常样本 object score 偏高，导致 false positive。
2. 部分真实 anomaly 的点级定位也不稳定，例如前面记录里的 `cap3_broken3` 出现 GT 内均值低于背景。

人工查看 overlay 后，`cap3_positive9/7/10` 的红蓝点云不是良好重合状态；主要差异集中在帽檐、类似鸭舌的突出结构等局部形状区域。用户观察到没有明显尺度问题，但红蓝点云错位较严重，局部分布差异大。

因此 `cap3` 不适合立刻拿来做简单阈值调参。它更适合作为 registration/template robustness 的重点诊断类别。当前更合理的解释是：PASDF 在正常 `cap3` 样本上看到的高分，不一定是异常语义错误，而可能是 registered sample 与 template 在局部结构上没有对齐，导致 SDF residual 被正常结构差异放大。

## 6. tap1 PASDF vs geometry 分析

### 6.1 数值概览

| sample | PASDF object | PASDF GT mean | PASDF bg mean | Geometry object | Geometry GT mean | Geometry bg mean |
|---|---:|---:|---:|---:|---:|---:|
| `tap1_broken2` | 0.001698 | 0.000261 | 0.000041 | 0.936926 | 0.579868 | 0.477918 |
| `tap1_broken3` | 0.002379 | 0.000286 | 0.000040 | 0.931026 | 0.579859 | 0.476939 |
| `tap1_hole0` | 0.001395 | 0.000266 | 0.000109 | 0.934251 | 0.643122 | 0.523051 |

这张表容易误读，所以要分开解释：

- PASDF object score 和 geometry object score 不在同一个数值尺度上，不能直接说 `0.93` 比 `0.001` 好几百倍。
- 需要看同一个 score 内部的 GT mean 和 background mean。
- PASDF 在三例中 GT mean 都高于 background mean，说明它不是完全没响应。
- 但 PASDF 的绝对 score 很低，object score 也低，说明它对 `tap1` 局部缺陷的响应强度不足。
- geometry 的 GT mean 也都高于 background mean，说明点到模板的距离残差对这些局部 broken/hole 有可用信号。

### 6.2 `tap1_broken2` PASDF vs geometry

![tap1_broken2 PASDF vs geometry](../../../experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken2_pasdf_vs_geometry.svg)

数值上：

- PASDF GT mean：`0.000261`
- PASDF background mean：`0.000041`
- Geometry GT mean：`0.579868`
- Geometry background mean：`0.477918`

解释：

PASDF 左图中 GT 区域确实比背景高，但整体分数很低。geometry 右图的 GT 区域相对背景也更高，说明 broken2 的形变或缺损能被距离残差捕捉。这个样本支持继续做小范围局部解释诊断。

### 6.3 `tap1_broken3` PASDF vs geometry

![tap1_broken3 PASDF vs geometry](../../../experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken3_pasdf_vs_geometry.svg)

数值上：

- PASDF GT mean：`0.000286`
- PASDF background mean：`0.000040`
- Geometry GT mean：`0.579859`
- Geometry background mean：`0.476939`

解释：

`tap1_broken3` 和 `tap1_broken2` 很接近。PASDF 能给 GT 区域一点响应，但 object score 仍然很低。geometry 继续提供正向分离。两个 broken 样本结果一致，说明这不是孤例。

### 6.4 `tap1_hole0` PASDF vs geometry

![tap1_hole0 PASDF vs geometry](../../../experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_hole0_pasdf_vs_geometry.svg)

数值上：

- PASDF GT mean：`0.000266`
- PASDF background mean：`0.000109`
- Geometry GT mean：`0.643122`
- Geometry background mean：`0.523051`

解释：

`tap1_hole0` 的 PASDF GT/background 差距比 broken 样本小一些，但 geometry 仍然给出 GT 高于背景的信号。它说明 geometry residual 不只对 broken 有效，对 hole 也有一定诊断价值。

### 6.5 tap1 小结

`tap1` 的关键结论是：PASDF 有方向，但强度不足；geometry distance residual 有补充价值。

这与 `cap3` 不同。`cap3` 的首要问题像 false positive 和 template/registration；`tap1` 的首要问题更像局部缺陷响应太弱。因此这两类不应该用同一种修正策略。

另外，用户在图中观察到 `tap1_broken3` 以及其他 `tap1` bad case 的 PASDF 左图大多为蓝色点，而右侧 geometry 图有更多高分红色点；黑色 GT 点数量不多，但可见的黑色轮廓点附近，右侧 geometry 高分区域更接近 GT。这个人工观察与数值结论一致：PASDF 的 GT 内均值虽然高于背景，但绝对响应弱；geometry residual 对局部 broken/hole 更敏感。

## 7. 人工判读补充

### 7.1 cap3：更像 registration/template mismatch

人工观察结论：

- 红蓝点云没有良好重合。
- 没有明显全局尺度问题。
- 错位主要体现在局部结构分布，例如帽檐、类似鸭舌的突出部分。
- 这些局部结构差异足以解释 normal sample 被 PASDF 打高分。

这说明 `cap3_positive9/7/10` 的 false positive 不能简单归因于阈值过低。更可能的路径是：

```text
sample/template 局部错位
-> SDF residual 局部变大
-> top-k object score 被少量高分点拉高
-> positive 样本被误判为异常
```

下一步对 `cap3` 应做定量 registration/template mismatch 诊断，而不是直接做 fusion。建议新增以下统计：

- sample 到 template 的 nearest-neighbor distance 均值、p95、p99、top5% 均值。
- positive 与 anomaly 的 residual 分布对比。
- 局部高 residual 点是否集中在帽檐/鸭舌区域。
- 多视角 overlay，避免单一 XY 投影误判 3D 对齐质量。

### 7.2 tap1：geometry residual 值得进入小范围局部解释

人工观察结论：

- PASDF 左图大部分为低分蓝点。
- Geometry 右图出现更明显的高分区域。
- GT 点数量少，但可见 GT 黑边附近右侧 geometry 更接近高分区域。

GT 点少不是主要渲染错误。原始数据中 GT 点本身占比极低：

| sample | 总点数 | GT 点数 | GT 占比 | 当前 SVG 中 GT 点数 |
|---|---:|---:|---:|---:|
| `tap1_broken2` | 16384 | 26 | 0.1587% | 7 |
| `tap1_broken3` | 16384 | 43 | 0.2625% | 15 |
| `tap1_hole0` | 16384 | 87 | 0.5310% | 22 |

用户确认暂时不做 GT-preserving sampling，因此下一步不把可视化采样作为主线。我们保留现有图用于定性判断，把精力转向小范围 quantitative diagnosis。

### 7.3 对计划的修正

原计划继续，但分成两条小线：

1. `cap3`：registration/template mismatch 定量诊断。
2. `tap1`：先验证 geometry residual 的局部解释价值，再判断是否能进入 object score 方案。

这比直接做全量 A4/A5 更严谨，因为当前证据显示不同类别的失败模式不同：

- `cap3` 是“正常样本因对齐/模板差异被打高分”。
- `tap1` 是“真实缺陷 PASDF 响应弱，但 geometry residual 有补充信号”。

## 8. P6 定量诊断补充

P5 图像判读之后，我们已经继续做了 P6 targeted diagnostics 和 alpha sweep。这里补充到同一份报告里，避免只看 P5 图时误以为下一步仍然是扩大 additive fusion。

### 8.1 cap3 registration/template mismatch 定量结果

| sample | label | PASDF object | NN mean | NN p95 | NN p99 | NN top5 mean |
|---|---:|---:|---:|---:|---:|---:|
| `cap3_positive9` | 0 | 0.109517 | 0.006001 | 0.037221 | 0.095074 | 0.073342 |
| `cap3_positive7` | 0 | 0.096982 | 0.004349 | 0.020448 | 0.077369 | 0.054389 |
| `cap3_positive10` | 0 | 0.064902 | 0.002514 | 0.002931 | 0.035992 | 0.020964 |
| `cap3_hole0` | 1 | 0.006392 | 0.001592 | 0.002542 | 0.003038 | 0.003005 |
| `cap3_hole1` | 1 | 0.010446 | 0.001647 | 0.002592 | 0.003623 | 0.003518 |
| `cap3_broken2` | 1 | 0.012887 | 0.001706 | 0.002678 | 0.004526 | 0.003962 |
| `cap3_broken3` | 1 | 0.028583 | 0.003561 | 0.005110 | 0.012814 | 0.009030 |

这个结果和人工观察一致：`cap3_positive9/7/10` 虽然是正常样本，但 nearest-neighbor template residual 的 top5% 均值明显高于 `cap3` anomaly 对照。也就是说，PASDF object score 高不是孤立的阈值现象，而是和 sample/template 局部错位强相关。

### 8.2 tap1 naive additive hybrid 结果

| sample | label | PASDF obj | Geometry obj | Hybrid obj | PASDF GT-bg | Geometry GT-bg | Hybrid GT-bg |
|---|---:|---:|---:|---:|---:|---:|---:|
| `tap1_broken2` | 1 | 0.001698 | 0.936926 | 1.289039 | 0.000220 | 0.101950 | 0.580160 |
| `tap1_broken3` | 1 | 0.002379 | 0.931026 | 1.276239 | 0.000246 | 0.102920 | 0.615309 |
| `tap1_hole0` | 1 | 0.001395 | 0.934251 | 1.429934 | 0.000157 | 0.120071 | 0.429856 |
| `tap1_positive0` | 0 | 0.001332 | 0.929091 | 1.439421 | NA | NA | NA |
| `tap1_positive1` | 0 | 0.002814 | 0.935834 | 1.264047 | NA | NA | NA |
| `tap1_positive2` | 0 | 0.002487 | 0.933526 | 1.288088 | NA | NA | NA |
| `tap1_positive3` | 0 | 0.002757 | 0.930304 | 1.290285 | NA | NA | NA |
| `tap1_positive4` | 0 | 0.003375 | 0.929436 | 1.411291 | NA | NA | NA |

这个结果有两面：

- 好的一面：`tap1_broken2/broken3/hole0` 的 hybrid GT/background 分离都高于 PASDF，说明 geometry residual 对局部缺陷位置确实有补充信号。
- 风险的一面：`tap1_positive0` 的 hybrid object score 达到 `1.439421`，高于部分 anomaly；`tap1_positive4` 也达到 `1.411291`。这说明 naive additive hybrid 会把 positive 正常样本一起抬高，不能直接当成可用 object score。

### 8.3 alpha sweep positive-aware 结果

Alpha grid 为 `0.0, 0.1, 0.25, 0.5, 0.75, 1.0`。判定口径如下：

- object score 越高表示越异常。
- strict pass：`min anomaly hybrid object > max positive hybrid object` 且 `mean anomaly separation gain > 0`。
- soft pass：`mean anomaly hybrid object > max positive hybrid object` 且 `mean anomaly separation gain > 0`。

| alpha | min anomaly obj | mean anomaly obj | max positive obj | mean sep gain | strict | soft |
|---:|---:|---:|---:|---:|---|---|
| 0.000000 | 0.651312 | 0.701104 | 0.799581 | 0.433250 | False | False |
| 0.100000 | 0.702899 | 0.753773 | 0.856076 | 0.444082 | False | False |
| 0.250000 | 0.784960 | 0.837125 | 0.943650 | 0.460329 | False | False |
| 0.500000 | 0.934062 | 0.988108 | 1.097702 | 0.487409 | False | False |
| 0.750000 | 1.098221 | 1.153498 | 1.263006 | 0.514488 | False | False |
| 1.000000 | 1.276239 | 1.331737 | 1.439421 | 0.541568 | False | False |

所有 alpha 都没有通过 strict 或 soft positive-aware gating。随着 alpha 增大，anomaly 的分离增益确实上升，但 positive 的 object score 也同步上升，并且始终压过 anomaly 排序边界。

### 8.4 region explanation 结果

alpha sweep 失败后，我们继续做了 region-level explanation，不再看 additive object score，而是看 top-k 高分点是否真的贴近 GT 或 template residual。

`tap1` 的结果如下：

| sample | GT点数 | PASDF GT hit | Geometry GT hit | PASDF GT cover | Geometry GT cover | PASDF neighbor enrichment | Geometry neighbor enrichment |
|---|---:|---:|---:|---:|---:|---:|---:|
| `tap1_broken2` | 26 | 0.019512 | 0.006098 | 0.615385 | 0.192308 | 6.113433 | 0.745541 |
| `tap1_broken3` | 43 | 0.036585 | 0.010976 | 0.697674 | 0.209302 | 8.786600 | 1.564737 |
| `tap1_hole0` | 87 | 0.046341 | 0.024390 | 0.436782 | 0.229885 | 9.627562 | 1.450728 |

这个结果修正了前面对 `tap1` 的直觉判断：geometry 右图视觉上更红，但按 top-k GT 命中、GT 覆盖和 GT-neighborhood enrichment 看，PASDF 在 3/3 个样本上都优于 geometry。也就是说，`tap1` 的主要问题不是 PASDF 完全找不到 GT 局部区域，而是 GT 稀疏、score 绝对幅度低、object score 聚合后仍然不够高。geometry 可以保留为辅助可视化，但当前不支持把 geometry 作为主局部解释信号。

`cap3` 的结果如下：

| sample | label | PASDF object | residual topk mean | PASDF/residual overlap | residual bbox ratio | residual pair ratio |
|---|---:|---:|---:|---:|---:|---:|
| `cap3_positive9` | 0 | 0.109517 | 0.073342 | 0.986585 | 0.459868 | 0.127015 |
| `cap3_positive7` | 0 | 0.096982 | 0.054389 | 0.989024 | 0.497670 | 0.131435 |
| `cap3_positive10` | 0 | 0.064902 | 0.020964 | 0.903659 | 0.999944 | 0.235032 |
| `cap3_hole0` | 1 | 0.006392 | 0.003005 | 0.269512 | 0.996477 | 0.356347 |
| `cap3_hole1` | 1 | 0.010446 | 0.003518 | 0.326829 | 0.998097 | 0.361764 |
| `cap3_broken2` | 1 | 0.012887 | 0.003962 | 0.440244 | 0.999043 | 0.373308 |
| `cap3_broken3` | 1 | 0.028583 | 0.009030 | 0.635366 | 0.992880 | 0.343603 |

`cap3_positive9/7/10` 的 PASDF/residual top-k overlap 分别为 `0.986585`、`0.989024`、`0.903659`，远高于多数 anomaly 对照。这是很强的证据：这些 positive false positive 的 PASDF 高分点和 template residual 高分点几乎是同一批点。`cap3_positive9/7` 的 residual bbox ratio 约 `0.46/0.50`，pair ratio 约 `0.13`，说明 high residual 更局部集中；这与人工看到的帽檐/鸭舌区域错位一致。

## 9. 当前结论修正

P5 时我们曾计划把 `tap1` 推进到 PASDF + geometry 小范围 fusion prototype。P6 的负结果说明这条路需要收窄：

- `tap1` 的 geometry residual 在视觉上有提示，但 top-k region 指标没有优于 PASDF。
- `tap1` 的 geometry residual 暂时不能作为 additive object score，因为 positive-aware 排序失败。
- 后续不继续调 alpha，也不扩大 naive additive fusion 到更多类别。
- 下一步不再沿 geometry 主线推进；应回到 PASDF 的 object score 校准、top-k 聚合口径和 GT 稀疏样本解释。

`cap3` 的结论也更清楚：它不是 fusion 主线样本，而是 registration/template robustness 样本。下一步应该定量分析 high residual 点是否局部集中、是否与 PASDF 高分区域重叠，以及这些高 residual 区域是否对应人工看到的帽檐/鸭舌局部错位。

## 10. 这些结果代表什么

### 10.1 对 PASDF 的含义

PASDF 在当前数据上不是简单的“完全失败”或“完全可用”。

它在 object-level 上能给出一些排序信号，但点级定位和类别稳定性存在差异：

- `cap3`：正常样本高分，false-positive 风险高。
- `tap1`：真实缺陷分数偏低，局部响应弱。
- `helmet1`：前面阶段记录显示 GT/background 差距小，更像点级定位困难样本。

### 10.2 对 geometry residual 的含义

geometry distance residual 不是最终答案，但它是有用的诊断工具。

在 `tap1_broken2/broken3/hole0` 上，它给出的 GT/background 分离方向是对的，但 top-k region 指标没有优于 PASDF。因此它可以保留为辅助可视化和排查工具，暂时不能作为主局部解释信号，也不能直接作为 additive object score，因为：

- distance residual 可能也会放大 registration/template mismatch。
- geometry object score 的尺度和 PASDF 不同，需要校准。
- 对不同类别，template shape 差异会影响 residual 的可比性。
- 本轮 alpha sweep 已经显示 positive object score 会被同步抬高。

### 10.3 对原计划的含义

原计划应该继续，但不能跳过人工判读。

更准确的路线是：

1. P5 继续完成 targeted case study 的人工解释。
2. P6 先做小范围诊断，不直接扩 40 类。
3. 把类别分成不同失败模式：
   - `cap3`：registration/template/false-positive 优先。
   - `tap1`：PASDF 局部排序有信号，但 object score 聚合和校准偏弱。
   - `helmet1`：点级定位失败解释优先。

## 11. 下一步建议

我建议下一步按这个顺序做：

1. `cap3` 继续做 registration/template robustness：优先解释 positive false positive，并考虑多模板、局部对齐或模板选择策略。
2. `tap1` 暂停 geometry 主线，转向 PASDF object score 校准：分析 top-k ratio、score 幅度、类别内 positive/anomaly 排序和 GT 稀疏对 object score 的影响。
3. `helmet1` 按既有 SOP 进入点级定位失败解释，检查是否与 `tap1` 属于同一类“局部排序有信号但 object score 弱”的问题。

我不建议现在直接做 40 类 full hybrid。理由是现在的证据明确不支持 additive fusion，也不支持 geometry 作为 `tap1` 主局部解释信号。

## 12. 需要你人工确认的事项

前一轮需要确认的问题已经完成：

1. `cap3_positive9/7/10` 的红蓝 overlay 存在明显错位和局部分布差异，但没有明显尺度问题。
2. `tap1_broken2/broken3/hole0` 的右侧 geometry 图相比左侧 PASDF 有更强高分区域，且可见 GT 黑边附近更接近高分区域。

因此下一步进入 P6 后续小范围实验：

- `cap3`：继续做 registration/template robustness。
- `tap1`：转向 PASDF object score 校准与 GT 稀疏样本解释。

暂时不做 GT-preserving sampling。虽然该功能会提升可视化可信度，但当前人工判断已经足够支持进入小范围 quantitative experiment。

## 13. 本轮代码与验证

本轮 commit：

```text
ac208ad feat(analysis): add p5 targeted case study visualizations
fbc29ba docs(report): add p5 targeted case study report
ffa71a5 feat(analysis): add p6 targeted diagnostics prototype
97e05c6 feat(analysis): add p6 alpha sweep gating
```

新增或修改的核心文件：

- `docs/document/tech_arche/P5_targeted_pasdf_score_visualization.md`
- `src/pcdad/analysis/pasdf_case_study.py`
- `src/pcdad/viz/pointcloud.py`
- `scripts/visualize_pasdf_scores.py`
- `tests/test_pasdf_case_study.py`
- `tests/test_visualize.py`
- `tests/test_visualize_pasdf_scores.py`
- `docs/document/stage_record/2026-06-13_p5_targeted_case_study.md`
- `docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv`
- `docs/document/tech_arche/P6_targeted_diagnostics_and_fusion_plan.md`
- `docs/document/tech_arche/P6_alpha_sweep_positive_gating_plan.md`
- `src/pcdad/analysis/targeted_p6.py`
- `scripts/run_p6_targeted_diagnostics.py`
- `tests/test_targeted_p6.py`
- `tests/test_targeted_p6_alpha_sweep.py`
- `tests/test_run_p6_targeted_diagnostics.py`
- `tests/test_run_p6_alpha_sweep_cli.py`
- `tests/test_targeted_p6_region_explanation.py`
- `tests/test_run_p6_region_explanation_cli.py`
- `docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.md`
- `docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.csv`
- `docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.md`
- `docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.csv`
- `docs/document/tech_arche/P6_region_explanation_and_cap3_residual_plan.md`
- `docs/document/stage_record/2026-06-13_p6_region_explanation_summary.md`
- `docs/document/stage_record/2026-06-13_p6_region_explanation_summary.csv`

验证结果：

```text
PYTHONPATH=src pytest -q: 97 passed
ruff check src scripts tests: passed
black --check src scripts tests: passed
mypy src/pcdad: passed
pre-commit run --all-files: passed
```
