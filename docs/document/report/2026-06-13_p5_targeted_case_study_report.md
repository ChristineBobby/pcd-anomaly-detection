# P5 Targeted Case Study 技术报告

日期：2026-06-13

## 目录

- [1. 本报告要回答的问题](#1-本报告要回答的问题)
- [2. 你要看的图在哪里](#2-你要看的图在哪里)
- [3. 本轮我们做了什么](#3-本轮我们做了什么)
- [4. 图应该怎么看](#4-图应该怎么看)
- [5. cap3 positive false positive 分析](#5-cap3-positive-false-positive-分析)
- [6. tap1 PASDF vs geometry 分析](#6-tap1-pasdf-vs-geometry-分析)
- [7. 这些结果代表什么](#7-这些结果代表什么)
- [8. 下一步建议](#8-下一步建议)
- [9. 需要你人工确认的事项](#9-需要你人工确认的事项)
- [10. 本轮代码与验证](#10-本轮代码与验证)

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

因此 `cap3` 不适合立刻拿来做简单阈值调参。它更适合作为 registration/template robustness 的重点诊断类别。

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

## 7. 这些结果代表什么

### 7.1 对 PASDF 的含义

PASDF 在当前数据上不是简单的“完全失败”或“完全可用”。

它在 object-level 上能给出一些排序信号，但点级定位和类别稳定性存在差异：

- `cap3`：正常样本高分，false-positive 风险高。
- `tap1`：真实缺陷分数偏低，局部响应弱。
- `helmet1`：前面阶段记录显示 GT/background 差距小，更像点级定位困难样本。

### 7.2 对 geometry residual 的含义

geometry distance residual 不是最终答案，但它是有用的诊断工具。

在 `tap1_broken2/broken3/hole0` 上，它给出的 GT/background 分离方向是对的，所以可以进入小范围 hybrid score 实验。但它不能直接全量上线，因为：

- distance residual 可能也会放大 registration/template mismatch。
- geometry object score 的尺度和 PASDF 不同，需要校准。
- 对不同类别，template shape 差异会影响 residual 的可比性。

### 7.3 对原计划的含义

原计划应该继续，但不能跳过人工判读。

更准确的路线是：

1. P5 继续完成 targeted case study 的人工解释。
2. P6 先做小范围 hybrid score，不直接扩 40 类。
3. 把类别分成不同失败模式：
   - `cap3`：registration/template/false-positive 优先。
   - `tap1`：PASDF 弱响应 + geometry fusion 优先。
   - `helmet1`：点级定位失败解释优先。

## 8. 下一步建议

我建议下一步按这个顺序做：

1. 你先人工查看本报告嵌入的 6 张图。
2. 对 `cap3_positive9/7/10`，判断红蓝点云是否明显错位。
3. 对 `tap1_broken2/broken3/hole0`，判断右侧 geometry 高分区域是否比左侧 PASDF 更贴近黑色 GT 点。
4. 如果第 2 点成立，P6 先做 registration/template robustness 方案。
5. 如果第 3 点成立，P6 同时做 `tap1` 小范围 PASDF + geometry fusion。

我不建议现在直接做 40 类 full hybrid。理由是现在的证据支持“小范围有效”，还没有支持“全类别稳健”。

## 9. 需要你人工确认的事项

请你重点回答这两个问题：

1. `cap3_positive9/7/10` 的红蓝 overlay 是否存在明显错位、尺度差异或局部模板不匹配？
2. `tap1_broken2/broken3/hole0` 的右侧 geometry 图是否比左侧 PASDF 更集中覆盖黑色 GT 点？

如果你的判断是“是”，下一步我们就进入 P6 小范围实验：

- `cap3`：先做 registration/template 诊断增强。
- `tap1`：先做 PASDF + geometry score fusion prototype。

如果你的判断是“否”，说明当前 2D 投影图不足以解释问题。下一步就应补多视角 SVG 或交互式点云查看，而不是急着改模型。

## 10. 本轮代码与验证

本轮 commit：

```text
ac208ad feat(analysis): add p5 targeted case study visualizations
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
