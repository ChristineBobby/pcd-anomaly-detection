# P5 PASDF Targeted Case Study

## 记录范围

- 样本数：13
- 类别数：3

## 样本明细

| 类别 | 样本 | Label | PASDF Object | GT 点数 | GT 内均值 | 背景均值 | PASDF SVG | Overlay | PASDF-vs-geometry | Geometry Object |
|---|---|---:|---:|---:|---:|---:|---|---|---|---:|
| cap3 | `cap3_positive9` | 0 | 0.109517 | 0 | NA | 0.004619 | `experiments/P5_case_study/pasdf_scores/cap3/cap3_positive9_pasdf_score.svg` | `experiments/P5_case_study/template_overlay/cap3/cap3_positive9_template_overlay.svg` | NA | NA |
| cap3 | `cap3_positive7` | 0 | 0.096982 | 0 | NA | 0.003096 | `experiments/P5_case_study/pasdf_scores/cap3/cap3_positive7_pasdf_score.svg` | `experiments/P5_case_study/template_overlay/cap3/cap3_positive7_template_overlay.svg` | NA | NA |
| cap3 | `cap3_positive10` | 0 | 0.064902 | 0 | NA | 0.001150 | `experiments/P5_case_study/pasdf_scores/cap3/cap3_positive10_pasdf_score.svg` | `experiments/P5_case_study/template_overlay/cap3/cap3_positive10_template_overlay.svg` | NA | NA |
| cap3 | `cap3_hole0` | 1 | 0.006392 | 100 | 0.000711 | 0.000257 | `experiments/P5_case_study/pasdf_scores/cap3/cap3_hole0_pasdf_score.svg` | NA | NA | NA |
| cap3 | `cap3_hole1` | 1 | 0.010446 | 148 | 0.000392 | 0.000345 | `experiments/P5_case_study/pasdf_scores/cap3/cap3_hole1_pasdf_score.svg` | NA | NA | NA |
| cap3 | `cap3_broken2` | 1 | 0.012887 | 42 | 0.001386 | 0.000365 | `experiments/P5_case_study/pasdf_scores/cap3/cap3_broken2_pasdf_score.svg` | NA | NA | NA |
| cap3 | `cap3_broken3` | 1 | 0.028583 | 44 | 0.001887 | 0.002546 | `experiments/P5_case_study/pasdf_scores/cap3/cap3_broken3_pasdf_score.svg` | NA | NA | NA |
| helmet1 | `helmet1_concavity2` | 1 | 0.018686 | 761 | 0.006295 | 0.006202 | `experiments/P5_case_study/pasdf_scores/helmet1/helmet1_concavity2_pasdf_score.svg` | NA | NA | NA |
| helmet1 | `helmet1_concavity4` | 1 | 0.018856 | 546 | 0.006366 | 0.005964 | `experiments/P5_case_study/pasdf_scores/helmet1/helmet1_concavity4_pasdf_score.svg` | NA | NA | NA |
| helmet1 | `helmet1_concavity3` | 1 | 0.022866 | 399 | 0.006518 | 0.005588 | `experiments/P5_case_study/pasdf_scores/helmet1/helmet1_concavity3_pasdf_score.svg` | NA | NA | NA |
| tap1 | `tap1_broken2` | 1 | 0.001698 | 26 | 0.000261 | 0.000041 | `experiments/P5_case_study/pasdf_scores/tap1/tap1_broken2_pasdf_score.svg` | NA | `experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken2_pasdf_vs_geometry.svg` | 0.936926 |
| tap1 | `tap1_broken3` | 1 | 0.002379 | 43 | 0.000286 | 0.000040 | `experiments/P5_case_study/pasdf_scores/tap1/tap1_broken3_pasdf_score.svg` | NA | `experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken3_pasdf_vs_geometry.svg` | 0.931026 |
| tap1 | `tap1_hole0` | 1 | 0.001395 | 87 | 0.000266 | 0.000109 | `experiments/P5_case_study/pasdf_scores/tap1/tap1_hole0_pasdf_score.svg` | NA | `experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_hole0_pasdf_vs_geometry.svg` | 0.934251 |

## 初步解读

- `cap3_positive9` 是 positive 样本，Object Score 为 `0.109517`；若 SVG 中高分区域集中，应优先检查配准或模板差异。
  template overlay：`experiments/P5_case_study/template_overlay/cap3/cap3_positive9_template_overlay.svg`，用于人工确认 sample/template registration 是否存在系统偏差。
- `cap3_positive7` 是 positive 样本，Object Score 为 `0.096982`；若 SVG 中高分区域集中，应优先检查配准或模板差异。
  template overlay：`experiments/P5_case_study/template_overlay/cap3/cap3_positive7_template_overlay.svg`，用于人工确认 sample/template registration 是否存在系统偏差。
- `cap3_positive10` 是 positive 样本，Object Score 为 `0.064902`；若 SVG 中高分区域集中，应优先检查配准或模板差异。
  template overlay：`experiments/P5_case_study/template_overlay/cap3/cap3_positive10_template_overlay.svg`，用于人工确认 sample/template registration 是否存在系统偏差。
- `cap3_hole0` 的 GT 内均值为 `0.000711`，背景均值为 `0.000257`。
- `cap3_hole1` 的 GT 内均值为 `0.000392`，背景均值为 `0.000345`。
- `cap3_broken2` 的 GT 内均值为 `0.001386`，背景均值为 `0.000365`。
- `cap3_broken3` 的 GT 内均值 `0.001887` 不高于背景 `0.002546`，属于点级定位失败优先样本。
- `helmet1_concavity2` 的 GT 内均值为 `0.006295`，背景均值为 `0.006202`。
- `helmet1_concavity4` 的 GT 内均值为 `0.006366`，背景均值为 `0.005964`。
- `helmet1_concavity3` 的 GT 内均值为 `0.006518`，背景均值为 `0.005588`。
- `tap1_broken2` 的 GT 内均值为 `0.000261`，背景均值为 `0.000041`。
  PASDF-vs-geometry：`experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken2_pasdf_vs_geometry.svg`；Geometry Object Score=`0.936926`，GT 内 geometry 均值=`0.579868`，背景 geometry 均值=`0.477918`。
- `tap1_broken3` 的 GT 内均值为 `0.000286`，背景均值为 `0.000040`。
  PASDF-vs-geometry：`experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken3_pasdf_vs_geometry.svg`；Geometry Object Score=`0.931026`，GT 内 geometry 均值=`0.579859`，背景 geometry 均值=`0.476939`。
- `tap1_hole0` 的 GT 内均值为 `0.000266`，背景均值为 `0.000109`。
  PASDF-vs-geometry：`experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_hole0_pasdf_vs_geometry.svg`；Geometry Object Score=`0.934251`，GT 内 geometry 均值=`0.643122`，背景 geometry 均值=`0.523051`。

## 执行与验证

本轮执行命令：

```bash
PYTHONPATH=src python scripts/visualize_pasdf_scores.py \
  --score-root experiments/P5_pasdf_scores/representative \
  --samples \
    cap3_positive9 cap3_positive7 cap3_positive10 \
    cap3_hole0 cap3_hole1 cap3_broken2 cap3_broken3 \
    helmet1_concavity2 helmet1_concavity4 helmet1_concavity3 \
    tap1_broken2 tap1_broken3 tap1_hole0 \
  --template-overlay-samples cap3_positive9 cap3_positive7 cap3_positive10 \
  --geometry-comparison-samples tap1_broken2 tap1_broken3 tap1_hole0 \
  --template-root third_party/PASDF/data/ShapeNetAD \
  --output-dir experiments/P5_case_study \
  --summary-md docs/document/stage_record/2026-06-13_p5_targeted_case_study.md \
  --summary-csv docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv \
  --max-points 4096
```

产物检查：

- PASDF heatmap：13 个，覆盖本轮默认 targeted sample。
- `cap3_positive9/7/10`：均生成 `template_overlay` SVG。
- `tap1_broken2/broken3/hole0`：均生成 `pasdf_vs_geometry` SVG。
- `experiments/P5_case_study/` 仍被 `.gitignore` 排除，只保留 Markdown/CSV 摘要进入版本管理。

质量门：

- `PYTHONPATH=src pytest -q`：83 passed。
- `ruff check src scripts tests`：passed。
- `black --check src scripts tests`：passed。
- `mypy src/pcdad`：passed。
- `pre-commit run --all-files`：passed。

## 阶段结论与下一步

- `cap3_positive9/7/10` 的 object score 仍显著高于同类 anomaly 样本，应优先人工查看 overlay，判断 false positive 是否来自 registration/template 系统偏差，而不是点级异常响应。
- `tap1_broken2/broken3/hole0` 的 PASDF GT 内均值高于背景，但绝对分数很低；distance-only geometry 对三例均给出更高的 GT 内均值，说明几何 residual 可作为后续 hybrid score 的候选补充信号。
- 下一步建议进入 P5 的人工判读与规则固化：先审阅 6 张核心 SVG，再决定是否把 cap3 overlay 结论和 tap1 geometry residual 融合策略写入后续 A5/A6 实验设计。
