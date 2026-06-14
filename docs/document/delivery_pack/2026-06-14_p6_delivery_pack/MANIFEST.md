# 文件清单

## 目录

- [1. Markdown 文件](#1-markdown-文件)
- [2. 图片资产](#2-图片资产)
- [3. CSV 资产](#3-csv-资产)
- [4. 压缩包](#4-压缩包)

## 1. Markdown 文件

| 文件 | 用途 |
|---|---|
| `README.md` | 交付包入口和阅读顺序 |
| `01_project_report.md` | 完整项目报告 |
| `02_experiment_and_failure_analysis.md` | 实验结果与失败模式分析 |
| `03_reproduction_and_evidence.md` | 复现命令与证据清单 |
| `04_visual_gallery.md` | 图册 |
| `MANIFEST.md` | 文件清单 |

## 2. 图片资产

| 本包路径 | 原始来源 | 用途 |
|---|---|---|
| `assets/01_data/ashtray0_gt_normals.svg` | `experiments/p2_smoke/anomaly_shapenet_ashtray0_gt_normals.svg` | Anomaly-ShapeNet 数据 smoke：ashtray0 点云、法向与 GT |
| `assets/02_p4_geometry/a4_cap3_bending0.svg` | `experiments/P4_geometry_smoke/config_svgs/A4_pasdf_geom_full/cap3_cap3_bending0.svg` | P4 A4 几何 smoke：cap3 bending anomaly |
| `assets/02_p4_geometry/a4_cap3_positive0.svg` | `experiments/P4_geometry_smoke/config_svgs/A4_pasdf_geom_full/cap3_cap3_positive0.svg` | P4 A4 几何 smoke：cap3 positive control |
| `assets/03_cap3_overlay/cap3_positive9_template_overlay.svg` | `experiments/P5_case_study/template_overlay/cap3/cap3_positive9_template_overlay.svg` | cap3_positive9 sample/template overlay |
| `assets/03_cap3_overlay/cap3_positive7_template_overlay.svg` | `experiments/P5_case_study/template_overlay/cap3/cap3_positive7_template_overlay.svg` | cap3_positive7 sample/template overlay |
| `assets/03_cap3_overlay/cap3_positive10_template_overlay.svg` | `experiments/P5_case_study/template_overlay/cap3/cap3_positive10_template_overlay.svg` | cap3_positive10 sample/template overlay |
| `assets/04_pasdf_heatmap/cap3_positive9_pasdf_score.svg` | `experiments/P5_case_study/pasdf_scores/cap3/cap3_positive9_pasdf_score.svg` | cap3_positive9 PASDF heatmap |
| `assets/05_tap1_comparison/tap1_broken2_pasdf_vs_geometry.svg` | `experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken2_pasdf_vs_geometry.svg` | tap1_broken2 PASDF vs geometry |
| `assets/05_tap1_comparison/tap1_broken3_pasdf_vs_geometry.svg` | `experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken3_pasdf_vs_geometry.svg` | tap1_broken3 PASDF vs geometry |
| `assets/05_tap1_comparison/tap1_hole0_pasdf_vs_geometry.svg` | `experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_hole0_pasdf_vs_geometry.svg` | tap1_hole0 PASDF vs geometry |
| `assets/06_helmet1/helmet1_concavity4_pasdf_score.svg` | `experiments/P5_case_study/pasdf_scores/helmet1/helmet1_concavity4_pasdf_score.svg` | helmet1_concavity4 PASDF heatmap |
| `assets/07_p6_hybrid/tap1_broken2_hybrid.svg` | `experiments/P6_alpha_sweep/tap1_hybrid_scores/tap1/tap1_broken2_hybrid.svg` | P6 tap1_broken2 hybrid score |
| `assets/07_p6_hybrid/tap1_positive0_hybrid.svg` | `experiments/P6_alpha_sweep/tap1_hybrid_scores/tap1/tap1_positive0_hybrid.svg` | P6 tap1_positive0 hybrid score |

## 3. CSV 资产

| 本包路径 | 原始来源 |
|---|---|
| `assets/csv/p3_pasdf_40cls_evaluation_results.csv` | `experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv` |
| `assets/csv/p6_delivery_evidence_index.csv` | `docs/document/stage_record/2026-06-14_p6_delivery_evidence_index.csv` |
| `assets/csv/p6_failure_mode_closure.csv` | `docs/document/stage_record/2026-06-14_p6_failure_mode_closure.csv` |

## 4. 压缩包

| 文件 | 用途 |
|---|---|
| `../2026-06-14_p6_delivery_pack.zip` | 可直接转发的完整交付包压缩文件 |
