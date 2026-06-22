# P7-B 全 40 类 Positive-aware Calibration 阶段记录

撰写日期：2026-06-22

文档定位：本文件补充 `2026-06-22_p7_b_positive_calibration_summary.md`。之前四类实验只能视为 smoke test 和代表性 failure 检查；本文件记录基于 Anomaly-ShapeNet v2 全 40 类的 P5/P7-A/P7-B 结果，作为当前 P7-B 阶段的主结论依据。

<!-- TOC START -->
## 目录

- [1. 为什么补跑全类](#1-为什么补跑全类)
- [2. 实验输入与产物](#2-实验输入与产物)
- [3. 完整性核查](#3-完整性核查)
- [4. 全类总体结果](#4-全类总体结果)
- [5. 主要失败类别](#5-主要失败类别)
- [6. confidence gate 的真实作用](#6-confidence-gate-的真实作用)
- [7. 对 P7-B 结论的修正](#7-对-p7-b-结论的修正)
- [8. 下一步](#8-下一步)
- [9. 复现命令](#9-复现命令)
<!-- TOC END -->

## 1. 为什么补跑全类

P7-B 最初只跑了 `cap3`、`tap1`、`helmet1`、`ashtray0` 四类。这个选择适合快速验证代码和观察代表性 bad case，但不适合作为阶段结论。原因很简单：当我们要判断一个 calibration 方案是否值得进入 P7-C/P8，必须看全类覆盖，尤其要看它是否会破坏原本表现好的类别。

四类限制的真实原因不是数据集不完整，也不是 P7-B 只能跑四类，而是当时 P5 per-point PASDF score export 只导出了四类 `.npz`。因此本轮先补了全 40 类 P5 score，再用同一套 P7-A/P7-B 代码重跑全类。

## 2. 实验输入与产物

P5 全类 PASDF score：

```text
experiments/P5_pasdf_scores/full_40cls/
docs/document/stage_record/2026-06-22_p5_full40_pasdf_score_export_summary.md
docs/document/stage_record/2026-06-22_p5_full40_pasdf_score_export_summary.csv
```

P7-A 全类 multi-template registration：

```text
experiments/P7_A_multitemplate/full_40cls_train_pcd/
  per_sample_scores.csv
  template_assignments.csv
  failure_toplist.csv
  README.md
```

P7-B 全类 calibration：

```text
experiments/P7_B_calibration/full_40cls/
  calibration_records.csv
  metrics.csv
  boundary_margin.csv
  failure_toplist.csv
  README.md
```

本 stage record 摘要 CSV：

```text
docs/document/stage_record/2026-06-22_p7_b_full40_calibration_summary.csv
```

## 3. 完整性核查

全类数据覆盖正常：

| 项目 | 数值 |
|---|---:|
| 数据集类别数 | 40 |
| P5 score 类别数 | 40 |
| P5/P7-A 样本数 | 1312 |
| Positive 样本数 | 600 |
| 异常样本数 | 712 |
| P7-A `per_sample_scores.csv` 行数 | 1313 含表头 |
| P7-A `template_assignments.csv` 行数 | 5249 含表头 |
| P7-B `metrics.csv` 行数 | 361 含表头 |
| P7-B `calibration_records.csv` 行数 | 11809 含表头 |

这说明本轮不是四类抽样，也不是半截结果。P7-B 的每个主方法都覆盖 40 类。

## 4. 全类总体结果

`boundary_margin = min_anomaly_score - max_positive_score`，越大越好；只有严格大于 0 才算 object-level strict pass。

| 方法 | split | 类别数 | mean AUROC | mean AUPR | strict pass | mean margin | median margin |
|---|---|---:|---:|---:|---:|---:|---:|
| `pasdf_raw` | `none` | 40 | 0.894797 | 0.908544 | 12 | -0.022879 | -0.001892 |
| `confidence_gate` | `none` | 40 | 0.895756 | 0.911860 | 12 | -0.008504 | -0.000830 |
| `template_residual` | `none` | 40 | 0.488424 | 0.585162 | 0 | -0.009668 | -0.005094 |
| `isotonic_pasdf` | `diagnostic_oracle` | 40 | 0.903498 | 0.900821 | 12 | -0.029632 | 0.000000 |
| `isotonic_gated` | `diagnostic_oracle` | 40 | 0.903332 | 0.901459 | 12 | -0.009546 | 0.000000 |
| `logistic_l2` | `diagnostic_oracle` | 40 | 0.897364 | 0.911203 | 12 | -0.031206 | -0.003679 |
| `isotonic_pasdf` | leave-one-class-out 汇总 | 40 | 0.887173 | 0.886438 | 12 | -0.048715 | 0.000000 |
| `isotonic_gated` | leave-one-class-out 汇总 | 40 | 0.883498 | 0.883292 | 12 | -0.031891 | 0.000000 |
| `logistic_l2` | leave-one-class-out 汇总 | 40 | 0.889270 | 0.905384 | 9 | -0.035654 | -0.004355 |

直接结论：

- `confidence_gate` 是当前最稳的非训练后处理。它没有增加 strict-pass 类别数，但把 mean margin 从 `-0.022879` 推到 `-0.008504`。
- 单独使用 `template_residual` 不行，AUROC 只有 `0.488424`，说明注册残差不能直接替代 PASDF score。
- `diagnostic_oracle` 没有给出足够强的上限，strict pass 仍是 `12/40`。这比四类实验更清楚地说明：轻量校准不是主要突破口。
- leave-one-class-out 的 learned 方法没有稳定收益，`logistic_l2` strict pass 还降到 `9/40`。

## 5. 主要失败类别

PASDF raw 下 boundary margin 最差的 12 类如下：

| 类别 | AUROC | AUPR | margin | false positive top1 | top1 score |
|---|---:|---:|---:|---|---:|
| `cup0` | 0.933333 | 0.834412 | -0.170196 | `cup0_positive0` | 0.195732 |
| `cup1` | 0.752381 | 0.668998 | -0.152273 | `cup1_positive6` | 0.167000 |
| `bottle3` | 0.933333 | 0.871866 | -0.129307 | `bottle3_positive2` | 0.137458 |
| `cap4` | 0.610526 | 0.657947 | -0.104475 | `cap4_positive5` | 0.112650 |
| `cap3` | 0.768421 | 0.727606 | -0.097773 | `cap3_positive14` | 0.100715 |
| `cap0` | 0.807407 | 0.808690 | -0.079572 | `cap0_positive7` | 0.084981 |
| `helmet2` | 0.634783 | 0.697313 | -0.051417 | `helmet2_positive2` | 0.054208 |
| `helmet0` | 0.820290 | 0.828822 | -0.049787 | `helmet0_positive2` | 0.054423 |
| `bag0` | 0.890476 | 0.800928 | -0.040642 | `bag0_positive12` | 0.057969 |
| `eraser0` | 0.900000 | 0.852753 | -0.035827 | `eraser0_positive11` | 0.062634 |
| `shelf0` | 0.791304 | 0.839093 | -0.031911 | `shelf0_positive5` | 0.038621 |
| `headset1` | 0.733333 | 0.751069 | -0.025516 | `headset1_positive1` | 0.056258 |

这个列表比四类代表集更有价值。它说明最突出的 false positive 不只在 `cap3/tap1/helmet1`，`cup0/cup1/bottle3/cap4` 也很严重。后续 P7-C 不能只围绕 cap/tap/helmet 做样例，应至少把 cup 或 bottle 类加入训练型 smoke。

## 6. confidence gate 的真实作用

`confidence_gate` 的主要收益是压低高误报 normal 样本，而不是让更多类别 strict pass。

改善最大的类别：

| 类别 | margin 改变量 | AUROC 改变量 | raw margin | gated margin |
|---|---:|---:|---:|---:|
| `cup0` | 0.116143 | 0.000000 | -0.170196 | -0.054053 |
| `bottle3` | 0.091738 | 0.003175 | -0.129307 | -0.037569 |
| `cup1` | 0.085465 | 0.042857 | -0.152273 | -0.066808 |
| `cap3` | 0.065431 | -0.007017 | -0.097773 | -0.032342 |
| `cap4` | 0.064238 | -0.003508 | -0.104475 | -0.040237 |
| `cap0` | 0.045303 | 0.003704 | -0.079572 | -0.034269 |
| `helmet2` | 0.033052 | -0.005797 | -0.051417 | -0.018365 |
| `helmet0` | 0.030571 | -0.002899 | -0.049787 | -0.019216 |
| `eraser0` | 0.019792 | -0.009524 | -0.035827 | -0.016035 |
| `shelf0` | 0.019575 | 0.004348 | -0.031911 | -0.012336 |

退化主要发生在原本已经 strict pass 的类别：

| 类别 | margin 改变量 | AUROC 改变量 | raw margin | gated margin |
|---|---:|---:|---:|---:|
| `ashtray0` | -0.015317 | 0.000000 | 0.026510 | 0.011193 |
| `jar0` | -0.011127 | 0.000000 | 0.016041 | 0.004914 |
| `vase0` | -0.008939 | 0.000000 | 0.014393 | 0.005454 |
| `bottle1` | -0.007661 | 0.000000 | 0.013456 | 0.005795 |
| `vase5` | -0.006868 | 0.000000 | 0.011269 | 0.004401 |

这符合我们之前在四类里看到的现象：gate 能压 false positive，但也会压弱 anomaly 或压缩整体 score 动态范围。它可以作为诊断特征或保守后处理，不能作为核心创新点。

## 7. 对 P7-B 结论的修正

四类实验的结论方向没有错，但证据不足。本轮全类结果后，P7-B 结论应改成：

1. P7-B 已完成全类验证，不能再称为只跑四类。
2. 非训练 calibration 没有解决 object-level strict boundary，最好的主方法仍只有 `12/40` strict pass。
3. `confidence_gate` 有稳定的误报幅度压缩作用，尤其对 `cup0/cup1/bottle3/cap` 这类高 positive score 类别有效。
4. learned calibration 在全类 leave-one-class-out 下没有泛化优势，不能作为主方案。
5. 下一步应进入训练型方案，不要继续在 object-level 后处理上投入太多。

## 8. 下一步

建议进入 P7-C / P8 的训练型 smoke：

1. 写并冻结 `P7_C_pseudo_anomaly_discriminative_sdf_plan.md`，把本轮全类 failure list 纳入选类依据。
2. 训练 smoke 类别不要只选四类，建议至少覆盖：
   - `cup0` 或 `cup1`：当前最强 positive false positive。
   - `bottle3`：AUROC 高但 boundary margin 极差，适合验证 normal suppression。
   - `cap3` 或 `cap4`：与之前视觉 bad case 对齐。
   - `tap1`：保留点级定位对照。
   - `ashtray0`：control。
3. 模块方向应从 score calibration 转向 pseudo anomaly + discriminative SDF / point-level auxiliary head。
4. `confidence_gate` 保留为 baseline 和辅助特征，不作为论文式核心贡献。
5. 后续报告里把四类结果标为 smoke，把本文件作为 P7-B 主结果引用。

## 9. 复现命令

P5 全类 score 导出：

```bash
docker exec Anomaly bash -lc 'cd /workspace/code_folder/area1/Anomaly && PYTHONPATH=src /workspace/.conda/envs/pasdf/bin/python scripts/export_pasdf_scores.py --config experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml --pasdf-root third_party/PASDF --output-dir experiments/P5_pasdf_scores/full_40cls --summary-md docs/document/stage_record/2026-06-22_p5_full40_pasdf_score_export_summary.md --summary-csv docs/document/stage_record/2026-06-22_p5_full40_pasdf_score_export_summary.csv --save-point-scores'
```

P7-A 全类 multi-template：

```bash
docker exec Anomaly bash -lc 'cd /workspace/code_folder/area1/Anomaly && CLASSES=$(find experiments/P5_pasdf_scores/full_40cls -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort | tr "\n" " ") && PYTHONPATH=src /workspace/.conda/envs/pasdf/bin/python scripts/run_p7_multitemplate.py --score-root experiments/P5_pasdf_scores/full_40cls --template-root data/Anomaly-ShapeNet-v2/dataset/16384 --template-mode train_pcd --classes $CLASSES --output-dir experiments/P7_A_multitemplate/full_40cls_train_pcd --top-ratio 0.01'
```

P7-B 全类 calibration：

```bash
docker exec Anomaly bash -lc 'cd /workspace/code_folder/area1/Anomaly && CLASSES=$(find experiments/P5_pasdf_scores/full_40cls -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort | tr "\n" " ") && PYTHONPATH=src /workspace/.conda/envs/pasdf/bin/python scripts/train_p7_calibration.py --input-csv experiments/P7_A_multitemplate/full_40cls_train_pcd/per_sample_scores.csv --output-dir experiments/P7_B_calibration/full_40cls --classes $CLASSES'
```

运行环境备注：

- 容器：`Anomaly`
- conda env：`/workspace/.conda/envs/pasdf`
- 本轮为了让 Open3D/PASDF 在新容器内可 import，容器内补装了 `libgomp1`、`libgl1`、`libglib2.0-0`、`libxrender1`、`libxext6`。
