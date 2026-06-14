# 项目技术报告

## 目录

- [1. 项目背景](#1-项目背景)
- [2. 任务与数据](#2-任务与数据)
- [3. 方法路线](#3-方法路线)
- [4. 阶段进展](#4-阶段进展)
- [5. 核心结果](#5-核心结果)
- [6. 关键图示](#6-关键图示)
- [7. 结论与定位](#7-结论与定位)

## 1. 项目背景

本项目研究无监督 3D 点云异常检测。任务目标是在只使用正常样本或极少标注条件下，判断一个 3D 点云物体是否异常，并在点级别定位异常区域。相比 2D 图像，点云异常更关注几何结构、局部凹凸、断裂、孔洞、配准误差和采样密度变化。

项目主线不是重新从零训练一个弱 baseline，而是先复现当前强方法 PASDF，再围绕其失败模式做系统性分析。这样能保证结论建立在强基线之上，避免把低质量复现误当成方法创新。

## 2. 任务与数据

- 主数据集：Anomaly-ShapeNet。
- 协议：官方 40 类协议。
- 输入：每个样本固定为 `16384` 点的点云。
- 输出：对象级异常分数和点级异常 heatmap。
- 主要指标：object AUROC、pixel AUROC。

P2 数据准备阶段已经完成高密度课程包统计、固定点数版本生成、DataLoader 和点云/法向/GT 可视化 smoke。

![P2 数据 smoke](assets/01_data/ashtray0_gt_normals.svg)

## 3. 方法路线

项目采用 PASDF 作为主 backbone。PASDF 的核心思想是：先把测试点云对齐到 canonical template，再用连续 SDF 学习正常形状表面，推理时以点到正常零水平面的偏离作为点级异常分数，并通过 top-k 聚合得到对象级分数。

在 PASDF baseline 之上，我们尝试了三类扩展或诊断：

1. P4：法向、曲率、距离 residual 的 naive geometry enhancement。
2. P5：导出 PASDF per-point score，做 representative case study。
3. P6：positive-aware alpha sweep、region explanation、top-k calibration 和 failure-mode closure。

## 4. 阶段进展

| 阶段 | 状态 | 主要产物 | 结论 |
|---|---|---|---|
| P0-P2 | 已完成 | 仓库、环境、数据、DataLoader、数据统计 | 可稳定进入 PASDF 复现 |
| P3 | 已完成 | 40 类 PASDF baseline | object AUROC 达到论文级锚点 |
| P4 | 已完成 | A2/A3/A4 geometry smoke | naive geometry 不扩主表 |
| P5 | 已完成 | representative PASDF score export 与图文报告 | cap3/tap1 failure mode 分化明显 |
| P6 | 已完成 | calibration、alpha sweep、failure closure、evidence pack | 进入最终报告/PPT/demo 打包 |

## 5. 核心结果

| 方法 | 协议 | mean object AUROC | mean pixel AUROC | 说明 |
|---|---|---:|---:|---|
| PASDF official weights | Anomaly-ShapeNet 40 类 | `0.900214149779` | `0.896009030694` | P3 baseline，作为后续所有分析锚点 |

这个 object AUROC 与计划中的 PASDF 论文目标 `90.0%` 基本一致，说明主线复现已经达标。

## 6. 关键图示

### 6.1 P4 几何增强负结果

下图展示 A4 几何增强在 `cap3` anomaly 与 positive control 上的对照。几何分数能产生局部响应，但 positive control 也容易被抬高，因此不适合作为未经约束的对象级增强。

![A4 cap3 bending anomaly](assets/02_p4_geometry/a4_cap3_bending0.svg)

![A4 cap3 positive control](assets/02_p4_geometry/a4_cap3_positive0.svg)

### 6.2 P5/P6 cap3 false positive

`cap3_positive9/7/10` 都是正常样本，但 PASDF object score 偏高。sample/template overlay 显示局部结构不重合，结合 residual overlap 统计，该类更适合解释为 registration/template mismatch。

![cap3 positive9 overlay](assets/03_cap3_overlay/cap3_positive9_template_overlay.svg)

![cap3 positive9 PASDF heatmap](assets/04_pasdf_heatmap/cap3_positive9_pasdf_score.svg)

### 6.3 P5/P6 tap1 soft boundary

`tap1_broken2/broken3/hole0` 的 PASDF 对 GT 区域有信号，但 object score 幅度低。geometry residual 视觉上更明显，不过 P6 region metrics 表明 PASDF top-k 更贴近 GT，因此不支持直接恢复 additive fusion。

![tap1 broken2 comparison](assets/05_tap1_comparison/tap1_broken2_pasdf_vs_geometry.svg)

![tap1 positive hybrid counterexample](assets/07_p6_hybrid/tap1_positive0_hybrid.svg)

## 7. 结论与定位

当前项目可以作为一个完整、可复查的课程设计交付：

- 强 baseline 已复现到位。
- 几何增强没有强行包装成正结果，而是按实验事实收口为负结果。
- P5/P6 对代表失败类给出了可视化、定量和后续方向。
- 最终报告应强调：项目贡献是强基线复现、失败模式分析、正负结果闭环和工程可复现，而不是声称一个未经验证的新 SOTA 方法。
