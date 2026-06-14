# 3D 点云异常检测交付包

## 目录

- [1. 这个文件夹是什么](#1-这个文件夹是什么)
- [2. 推荐阅读顺序](#2-推荐阅读顺序)
- [3. 最核心结论](#3-最核心结论)
- [4. 文件结构](#4-文件结构)
- [5. 转发注意事项](#5-转发注意事项)

## 1. 这个文件夹是什么

这是一个可直接转发给课程组、组员或评审者的阶段交付包。它把当前仓库中的核心文档、实验结论、关键图片和复现命令整理到同一个目录中，并把所有图片复制到本目录的 `assets/` 下，Markdown 中只使用相对路径。

- 当前 commit：`8328ef8`
- 当前 tag：`v0.1-p6-delivery`
- 主基准：Anomaly-ShapeNet 40 类协议
- 主方法：PASDF 官方权重复现 + P4-P6 failure analysis
- 关键结论：PASDF baseline 达到论文级 object AUROC；naive geometry fusion 不进入主表。

## 2. 推荐阅读顺序

1. `01_project_report.md`：完整项目报告，适合快速理解全局。
2. `02_experiment_and_failure_analysis.md`：实验结果、图像判读和失败模式。
3. `03_reproduction_and_evidence.md`：复现命令、证据路径和质量门。
4. `04_visual_gallery.md`：所有图片集中图册。
5. `MANIFEST.md`：文件清单、来源和用途。

## 3. 最核心结论

- P3 PASDF 40 类复现：mean object AUROC=`0.900214149779`，mean pixel AUROC=`0.896009030694`。
- P4 A2/A3/A4 naive geometry enhancement：作为负结果收口，不扩 40 类。
- P5/P6 `cap3`：normal positive 样本被打高分，主要证据指向 registration/template mismatch。
- P5/P6 `tap1`：PASDF 有局部信号但 object boundary 偏软；geometry 只能作为诊断解释，不能直接 additive fusion。
- P6 `helmet1`：点级定位弱和 positive boundary 混淆，需要作为最终报告中的局限案例。

## 4. 文件结构

```text
2026-06-14_p6_delivery_pack/
├── README.md
├── 01_project_report.md
├── 02_experiment_and_failure_analysis.md
├── 03_reproduction_and_evidence.md
├── 04_visual_gallery.md
├── MANIFEST.md
├── assets/
│   ├── 01_data/
│   ├── 02_p4_geometry/
│   ├── 03_cap3_overlay/
│   ├── 04_pasdf_heatmap/
│   ├── 05_tap1_comparison/
│   ├── 06_helmet1/
│   ├── 07_p6_hybrid/
│   └── csv/
└── scripts/
    └── build_delivery_pack.py
```

## 5. 转发注意事项

- 转发时请整个文件夹一起发送，不要只发单个 Markdown，否则图片相对路径会失效。
- 如果需要直接发压缩包，可以使用同级目录下的 `2026-06-14_p6_delivery_pack.zip`。
- 本包不包含原始数据、模型权重、NPZ 点级分数或完整实验日志。
- 大型实验产物仍保留在服务器 `experiments/` 和 `data/` 目录中，本包只复制轻量 SVG/CSV。
