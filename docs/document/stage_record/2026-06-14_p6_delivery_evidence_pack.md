# P6 交付证据包

## 目录

- [1. 交付范围](#1-交付范围)
- [2. 核心结论](#2-核心结论)
- [3. 证据索引](#3-证据索引)
- [4. SOP 对照](#4-sop-对照)
- [5. 下一步建议](#5-下一步建议)

## 1. 交付范围

- 证据生成基准 commit：`e4dbc77`。
- 最终交付状态以发布时的 `git log -1` 或 `v0.1-p6-delivery` tag 为准。
- 本证据包覆盖 P3 baseline、P4 几何负结果、P5 targeted case study、P6 诊断与 failure-mode closure。
- `experiments/` 下的大型产物不进入 git；本文件只记录路径、命令和结论。

## 2. 核心结论

- P3 PASDF 40 类复现达标：mean object AUROC=`0.900214149779`，mean pixel AUROC=`0.896009030694`。
- P4 naive geometry enhancement 不进入主表；A2/A3/A4 smoke 没有稳定区分 anomaly 与 positive control。
- P6 positive-aware alpha sweep 拒绝恢复 additive geometry fusion。
- `cap3` 收口为 registration/template false positive；`tap1` 收口为 PASDF soft object boundary；`helmet1` 收口为点级定位弱和 positive boundary 混淆。

## 3. 证据索引

| 阶段 | 证据 ID | 结论声明 | 当前结论 | 入库记录状态 | 实验产物状态 |
|---|---|---|---|---|---|
| P3 | `p3_pasdf_baseline_40cls` | PASDF 官方权重在 Anomaly-ShapeNet 40 类协议上复现达标。 | mean object AUROC=0.900214149779；mean pixel AUROC=0.896009030694。 | tracked_ready | artifact_ready |
| P4 | `p4_geometry_negative_closure` | A2/A3/A4 naive geometry smoke 已完成并收口为负结果。 | normal/curvature 加权主要放大尺度，未稳定拉开 anomaly 与 positive。 | tracked_ready | artifact_ready |
| P5 | `p5_pasdf_score_export` | 代表类别 PASDF per-point score 已导出。 | ashtray0/cap3/helmet1/tap1 可用于 targeted heatmap 与 GT 对照。 | tracked_ready | artifact_ready |
| P5 | `p5_targeted_case_study` | cap3 overlay 与 tap1 PASDF-vs-geometry case study 已完成。 | cap3 更像 registration/template mismatch；tap1 geometry residual 可做局部解释但不等于最终融合方案。 | tracked_ready | artifact_ready |
| P6 | `p6_targeted_diagnostics` | cap3/tap1 targeted diagnostics 已生成。 | cap3 positive 的 NN top5 residual 明显高；tap1 hybrid 必须受 positive 约束。 | tracked_ready | artifact_ready |
| P6 | `p6_alpha_sweep_positive_gating` | tap1 positive-aware alpha sweep 已完成。 | 没有 alpha 同时满足 anomaly 分离提升和 positive-aware object 排序约束。 | tracked_ready | artifact_ready |
| P6 | `p6_region_explanation` | tap1 region explanation 与 cap3 residual overlap 已完成。 | geometry 对 tap1 的 GT-neighborhood enrichment 没有稳定优于 PASDF。 | tracked_ready | artifact_ready |
| P6 | `p6_pasdf_calibration` | PASDF top-k calibration 已覆盖 cap3/tap1/helmet1。 | cap3 和 helmet1 未通过 object 排序；tap1 只有 soft pass，没有 strict pass。 | tracked_ready | artifact_ready |
| P6 | `p6_failure_mode_closure` | cap3/tap1/helmet1 failure mode 已收口。 | cap3=registration/template false positive；tap1=soft object boundary；helmet1=point-level localization weakness。 | tracked_ready | artifact_ready |

## 4. SOP 对照

| 阶段 | 阶段记录 | 结果 CSV | 实验产物路径 | 生成命令 |
|---|---|---|---|---|
| P3 | `docs/document/stage_record/2026-06-08_p0_p3_stage_check.md` | `experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv` | NA | `PYTHONPATH=src CUDA_VISIBLE_DEVICES=0 python scripts/evaluate.py --config configs/experiment/E1_pasdf_baseline.yaml --output-dir experiments/E1_pasdf_baseline/full_40cls` |
| P4 | `docs/document/stage_record/2026-06-09_p4_geometry_closure.md` | `docs/document/stage_record/2026-06-09_a4_pasdf_geom_full_geometry_smoke_summary.csv` | `experiments/P4_geometry_smoke/config_svgs` | `PYTHONPATH=src python scripts/run_geometry_smoke.py --config configs/experiment/A4_pasdf_geom_full.yaml` |
| P5 | `docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md` | `docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.csv` | `experiments/P5_pasdf_scores/representative` | `PYTHONPATH=src python scripts/export_pasdf_scores.py --config experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml --pasdf-root third_party/PASDF --classes cap3 helmet1 tap1 ashtray0 --output-dir experiments/P5_pasdf_scores/representative --summary-md docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md --summary-csv docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.csv --save-point-scores` |
| P5 | `docs/document/stage_record/2026-06-13_p5_targeted_case_study.md` | `docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv` | `experiments/P5_case_study/template_overlay/cap3`<br>`experiments/P5_case_study/pasdf_vs_geometry/tap1` | `PYTHONPATH=src python scripts/visualize_pasdf_scores.py --score-root experiments/P5_pasdf_scores/representative --template-root third_party/PASDF/data/ShapeNetAD --output-dir experiments/P5_case_study --summary-md docs/document/stage_record/2026-06-13_p5_targeted_case_study.md --summary-csv docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv` |
| P6 | `docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.md` | `docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.csv` | `experiments/P6_targeted_diagnostics` | `PYTHONPATH=src python scripts/run_p6_targeted_diagnostics.py` |
| P6 | `docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.md` | `docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.csv` | `experiments/P6_alpha_sweep` | `PYTHONPATH=src python scripts/run_p6_targeted_diagnostics.py --score-root experiments/P5_pasdf_scores/representative --template-root third_party/PASDF/data/ShapeNetAD --cap3-samples cap3_positive9 cap3_positive7 cap3_positive10 cap3_hole0 cap3_hole1 cap3_broken2 cap3_broken3 --tap1-samples tap1_broken2 tap1_broken3 tap1_hole0 --tap1-positive-samples tap1_positive0 tap1_positive1 tap1_positive2 tap1_positive3 tap1_positive4 --alpha-grid 0.0 0.1 0.25 0.5 0.75 1.0 --output-dir experiments/P6_alpha_sweep --summary-md docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.md --summary-csv docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.csv --alpha-sweep-csv experiments/P6_alpha_sweep/tap1_alpha_sweep_records.csv --max-points 4096` |
| P6 | `docs/document/stage_record/2026-06-13_p6_region_explanation_summary.md` | `docs/document/stage_record/2026-06-13_p6_region_explanation_summary.csv` | `experiments/P6_region_explanation` | `PYTHONPATH=src python scripts/run_p6_targeted_diagnostics.py --score-root experiments/P5_pasdf_scores/representative --template-root third_party/PASDF/data/ShapeNetAD --cap3-samples cap3_positive9 cap3_positive7 cap3_positive10 cap3_hole0 cap3_hole1 cap3_broken2 cap3_broken3 --tap1-samples tap1_broken2 tap1_broken3 tap1_hole0 --run-region-explanation --region-output-dir experiments/P6_region_explanation --region-summary-md docs/document/stage_record/2026-06-13_p6_region_explanation_summary.md --region-summary-csv docs/document/stage_record/2026-06-13_p6_region_explanation_summary.csv --top-ratio 0.05 --neighbor-radius-ratio 0.02` |
| P6 | `docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.md` | `docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.csv` | `experiments/P6_pasdf_calibration/topk_calibration_records.csv` | `PYTHONPATH=src python scripts/run_p6_pasdf_calibration.py` |
| P6 | `docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md` | `docs/document/stage_record/2026-06-14_p6_failure_mode_closure.csv` | `experiments/P6_failure_mode_closure/failure_mode_closure_records.csv` | `PYTHONPATH=src python scripts/run_p6_failure_mode_closure.py` |

## 5. 下一步建议

- 进入最终报告/PPT/demo 打包阶段，优先复用本证据包中的 claim 与 artifact path。
- 不继续扩大 naive geometry fusion；若时间允许，只把 cap3 template robustness 和 helmet1 heatmap/GT overlay 作为附录级补充。
- 发布前从干净 shell 核对 README 最小复现命令，并记录最终 commit 或 tag。
