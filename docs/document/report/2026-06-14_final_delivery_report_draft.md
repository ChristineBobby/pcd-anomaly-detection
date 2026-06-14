# 最终报告草稿

## 目录

- [1. 摘要](#1-摘要)
- [2. 方法与实验主线](#2-方法与实验主线)
- [3. 关键结果](#3-关键结果)
- [4. 失败模式分析](#4-失败模式分析)
- [5. 局限与后续工作](#5-局限与后续工作)

## 1. 摘要

本项目以 Anomaly-ShapeNet 40 类协议为主基准，复现 PASDF 官方权重并完成几何增强、targeted case study 和 P6 failure-mode closure。当前自跑 PASDF mean object AUROC 为 `0.900214149779`，达到论文级锚点。

## 2. 方法与实验主线

- P3：PASDF 官方权重评估，固定 40 类 baseline。
- P4：法向、曲率、距离 residual smoke，用负结果关闭 naive geometry enhancement。
- P5：导出 per-point PASDF score，人工和定量分析代表类别。
- P6：positive-aware alpha sweep、region explanation、top-k calibration 与 failure-mode closure。

## 3. 关键结果

| Evidence ID | 结论 |
|---|---|
| `p3_pasdf_baseline_40cls` | mean object AUROC=0.900214149779；mean pixel AUROC=0.896009030694。 |
| `p4_geometry_negative_closure` | normal/curvature 加权主要放大尺度，未稳定拉开 anomaly 与 positive。 |
| `p5_pasdf_score_export` | ashtray0/cap3/helmet1/tap1 可用于 targeted heatmap 与 GT 对照。 |
| `p5_targeted_case_study` | cap3 更像 registration/template mismatch；tap1 geometry residual 可做局部解释但不等于最终融合方案。 |
| `p6_targeted_diagnostics` | cap3 positive 的 NN top5 residual 明显高；tap1 hybrid 必须受 positive 约束。 |
| `p6_alpha_sweep_positive_gating` | 没有 alpha 同时满足 anomaly 分离提升和 positive-aware object 排序约束。 |
| `p6_region_explanation` | geometry 对 tap1 的 GT-neighborhood enrichment 没有稳定优于 PASDF。 |
| `p6_pasdf_calibration` | cap3 和 helmet1 未通过 object 排序；tap1 只有 soft pass，没有 strict pass。 |
| `p6_failure_mode_closure` | cap3=registration/template false positive；tap1=soft object boundary；helmet1=point-level localization weakness。 |

## 4. 失败模式分析

- `cap3`：normal positive 样本与 template 在局部帽檐/鸭舌结构上不重合，导致 template residual 与 PASDF top-k 高分重叠。
- `tap1`：PASDF 对 GT 局部有信号，但 object score 幅度低；geometry residual 可作为诊断解释，不支持 additive fusion 进入主表。
- `helmet1`：mean anomaly 可高于 positive 均值，但最高 positive 仍压住边界，点级定位需要热力图/GT overlay 人工复查。

## 5. 局限与后续工作

- 当前交付不包含 Real3D-AD 全量验证和 MiniShift 压力测试。
- 当前几何增强为诊断工具，不作为最终性能提升 claim。
- 后续更值得投入的是 template selection、registration robustness 和更强的 positive-aware calibration，而不是继续调 naive additive fusion。
