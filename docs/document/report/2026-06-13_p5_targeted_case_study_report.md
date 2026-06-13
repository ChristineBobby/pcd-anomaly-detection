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
- [8. 这些结果代表什么](#8-这些结果代表什么)
- [9. 下一步建议](#9-下一步建议)
- [10. 需要你人工确认的事项](#10-需要你人工确认的事项)
- [11. 本轮代码与验证](#11-本轮代码与验证)

## 1. 本报告要回答的问题

P5 前一轮 PASDF score export 告诉我们两个现象：

1. `cap3` 的正常样本被 PASDF 打了很高的 object score，尤其是 `cap3_positive9/7/10`。
2. `tap1_broken2/broken3/hole0` 的 PASDF object score 很低，但这些样本确实有局部缺陷。

所以本轮不是继续盲目扩实验，而是做 targeted case study：

- 对 `cap3_positive9/7/10` 生成 sample/template overlay，检查 false positive 是否来自 registration 或 template mismatch。
- 对 `tap1_broken2/broken3/hole0` 生成 PASDF score 与 geometry distance score 的并排图，检查几何 residual 是否能补充 PASDF 的弱响应。

核心问题是：原计划是否继续？我的判断是继续，但需要先把 P5 的人工判读做完，再进入 P6 的小范围融合实验，暂时不要直接扩成 40 类大规模融合。

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

如果 PASDF 左图对 GT 区域响应弱，而 geometry 右图在 GT 区域更集中，那么说明几何 residual 可以作为后续 hybrid score 的候选补充信号。

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

PASDF 左图中 GT 区域确实比背景高，但整体分数很低。geometry 右图的 GT 区域相对背景也更高，说明 broken2 的形变或缺损能被距离残差捕捉。这个样本支持做小范围 PASDF + geometry fusion。

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

### 7.2 tap1：geometry residual 值得进入小范围融合

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

用户确认暂时不做 GT-preserving sampling，因此下一步不把可视化采样作为主线。我们保留现有图用于定性判断，把精力转向小范围 quantitative fusion。

对 `tap1` 的下一步更合理：

- 保持 PASDF point score。
- 加入 distance-only geometry point score。
- 做轻量融合：`hybrid = zscore(PASDF) + alpha * zscore(geometry)` 或 robust min-max 后加权。
- 只在 `tap1_broken2/broken3/hole0` 与少量 positive 对照上跑，不扩 40 类。
- 观察 object score 排序和 GT/background 分离是否改善。

### 7.3 对计划的修正

原计划继续，但分成两条小线：

1. `cap3`：registration/template mismatch 定量诊断。
2. `tap1`：PASDF + geometry 小范围 fusion prototype。

这比直接做全量 A4/A5 更严谨，因为当前证据显示不同类别的失败模式不同：

- `cap3` 是“正常样本因对齐/模板差异被打高分”。
- `tap1` 是“真实缺陷 PASDF 响应弱，但 geometry residual 有补充信号”。

## 8. 这些结果代表什么

### 8.1 对 PASDF 的含义

PASDF 在当前数据上不是简单的“完全失败”或“完全可用”。

它在 object-level 上能给出一些排序信号，但点级定位和类别稳定性存在差异：

- `cap3`：正常样本高分，false-positive 风险高。
- `tap1`：真实缺陷分数偏低，局部响应弱。
- `helmet1`：前面阶段记录显示 GT/background 差距小，更像点级定位困难样本。

### 8.2 对 geometry residual 的含义

geometry distance residual 不是最终答案，但它是有用的诊断工具。

在 `tap1_broken2/broken3/hole0` 上，它给出的 GT/background 分离方向是对的，所以可以进入小范围 hybrid score 实验。但它不能直接全量上线，因为：

- distance residual 可能也会放大 registration/template mismatch。
- geometry object score 的尺度和 PASDF 不同，需要校准。
- 对不同类别，template shape 差异会影响 residual 的可比性。

### 8.3 对原计划的含义

原计划应该继续，但不能跳过人工判读。

更准确的路线是：

1. P5 继续完成 targeted case study 的人工解释。
2. P6 先做小范围 hybrid score，不直接扩 40 类。
3. 把类别分成不同失败模式：
   - `cap3`：registration/template/false-positive 优先。
   - `tap1`：PASDF 弱响应 + geometry fusion 优先。
   - `helmet1`：点级定位失败解释优先。

## 9. 下一步建议

我建议下一步按这个顺序做：

1. 将 `cap3` 从 fusion 主线中暂时拆出，先做 registration/template mismatch 定量诊断。
2. 将 `tap1_broken2/broken3/hole0` 作为 fusion prototype 的第一批样本。
3. 为 fusion prototype 加入 positive 对照样本，避免只在 anomaly 上看起来变好。
4. 输出新的 P6 stage record：记录 cap3 residual 诊断、tap1 fusion 前后 object score 与 GT/background 分离。
5. 根据小范围结果决定是否进入更大的代表类别实验。

我不建议现在直接做 40 类 full hybrid。理由是现在的证据支持“小范围有效”，还没有支持“全类别稳健”。

## 10. 需要你人工确认的事项

前一轮需要确认的问题已经完成：

1. `cap3_positive9/7/10` 的红蓝 overlay 存在明显错位和局部分布差异，但没有明显尺度问题。
2. `tap1_broken2/broken3/hole0` 的右侧 geometry 图相比左侧 PASDF 有更强高分区域，且可见 GT 黑边附近更接近高分区域。

因此下一步进入 P6 小范围实验：

- `cap3`：先做 registration/template 诊断增强。
- `tap1`：先做 PASDF + geometry score fusion prototype。

暂时不做 GT-preserving sampling。虽然该功能会提升可视化可信度，但当前人工判断已经足够支持进入小范围 quantitative experiment。

## 11. 本轮代码与验证

本轮 commit：

```text
ac208ad feat(analysis): add p5 targeted case study visualizations
fbc29ba docs(report): add p5 targeted case study report
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

验证结果：

```text
PYTHONPATH=src pytest -q: 83 passed
ruff check src scripts tests: passed
black --check src scripts tests: passed
mypy src/pcdad: passed
pre-commit run --all-files: passed
```
