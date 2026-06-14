# 图册

## 目录

- [1. 数据与预处理](#1-数据与预处理)
- [2. P4 几何 smoke](#2-p4-几何-smoke)
- [3. cap3 template mismatch](#3-cap3-template-mismatch)
- [4. tap1 PASDF vs geometry](#4-tap1-pasdf-vs-geometry)
- [5. helmet1 与 P6 hybrid](#5-helmet1-与-p6-hybrid)

## 1. 数据与预处理

### Anomaly-ShapeNet 数据 smoke：ashtray0 点云、法向与 GT

![Anomaly-ShapeNet 数据 smoke：ashtray0 点云、法向与 GT](assets/01_data/ashtray0_gt_normals.svg)

P2 数据准备阶段的可视化 smoke。该图用于说明数据加载、法向估计和 GT 点级标签读取链路已经打通。


## 2. P4 几何 smoke

### P4 A4 几何 smoke：cap3 bending anomaly

![P4 A4 几何 smoke：cap3 bending anomaly](assets/02_p4_geometry/a4_cap3_bending0.svg)

A4 加大 normal/curvature 权重后，异常样本 object score 并没有稳定压过 positive control，说明 naive geometry 不适合直接扩 40 类主表。

### P4 A4 几何 smoke：cap3 positive control

![P4 A4 几何 smoke：cap3 positive control](assets/02_p4_geometry/a4_cap3_positive0.svg)

positive control 在几何残差下同样容易被抬高，是 P4 收口为负结果的主要证据之一。


## 3. cap3 template mismatch

### cap3_positive9 sample/template overlay

![cap3_positive9 sample/template overlay](assets/03_cap3_overlay/cap3_positive9_template_overlay.svg)

红点为 registered sample，蓝点为 template。该正常样本 object score 高，overlay 显示局部结构与 template 不重合，支持 template mismatch 解释。

### cap3_positive7 sample/template overlay

![cap3_positive7 sample/template overlay](assets/03_cap3_overlay/cap3_positive7_template_overlay.svg)

cap3_positive7 与 positive9 一样表现出局部错位，说明 cap3 false positive 不是单个孤例。

### cap3_positive10 sample/template overlay

![cap3_positive10 sample/template overlay](assets/03_cap3_overlay/cap3_positive10_template_overlay.svg)

cap3_positive10 的 mean score 低但 object score 高，说明少量 top-k 高分点足以拉高对象级分数。

### cap3_positive9 PASDF heatmap

![cap3_positive9 PASDF heatmap](assets/04_pasdf_heatmap/cap3_positive9_pasdf_score.svg)

正常样本的局部 PASDF 高分区域是 cap3 false positive 的直接可视化证据。


## 4. tap1 PASDF vs geometry

### tap1_broken2 PASDF vs geometry

![tap1_broken2 PASDF vs geometry](assets/05_tap1_comparison/tap1_broken2_pasdf_vs_geometry.svg)

左侧 PASDF 分数较低但 GT 内均值高于背景；右侧 geometry residual 视觉上更红，但后续 P6 region metrics 显示 PASDF top-k 更贴近 GT。

### tap1_broken3 PASDF vs geometry

![tap1_broken3 PASDF vs geometry](assets/05_tap1_comparison/tap1_broken3_pasdf_vs_geometry.svg)

tap1 broken 类样本重复出现 PASDF 低幅度响应和 geometry 高视觉响应，触发了后续 positive-aware 诊断。

### tap1_hole0 PASDF vs geometry

![tap1_hole0 PASDF vs geometry](assets/05_tap1_comparison/tap1_hole0_pasdf_vs_geometry.svg)

hole0 说明 geometry residual 对局部孔洞也有视觉响应，但不能直接等价为对象级提升。


## 5. helmet1 与 P6 hybrid

### helmet1_concavity4 PASDF heatmap

![helmet1_concavity4 PASDF heatmap](assets/06_helmet1/helmet1_concavity4_pasdf_score.svg)

helmet1 是点级定位弱和 positive boundary 混淆代表类；该图用于最终报告中的人工复查入口。

### P6 tap1_broken2 hybrid score

![P6 tap1_broken2 hybrid score](assets/07_p6_hybrid/tap1_broken2_hybrid.svg)

hybrid 提升了 anomaly 样本局部分离，但 positive-aware alpha sweep 发现 positive object score 同步升高。

### P6 tap1_positive0 hybrid score

![P6 tap1_positive0 hybrid score](assets/07_p6_hybrid/tap1_positive0_hybrid.svg)

positive0 的 hybrid object score 被抬高，是拒绝 naive additive fusion 的关键反例。
