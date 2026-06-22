# P7-B Positive-aware Calibration 阶段记录

撰写日期：2026-06-22

文档定位：本文件记录 P7-B 的实现、四类实验结果和阶段判断。它承接 `docs/document/tech_arche/P7_B_positive_aware_calibration_plan.md`、P7-A multi-template 输出和 P6 failure closure。

<!-- TOC START -->
## 目录

- [1. 阶段目标](#1-阶段目标)
- [2. 本轮实现](#2-本轮实现)
- [3. 实验设置](#3-实验设置)
- [4. 总体结果](#4-总体结果)
- [5. cap3 重点样本](#5-cap3-重点样本)
- [6. 结果解释](#6-结果解释)
- [7. 阶段结论](#7-阶段结论)
- [8. 下一步](#8-下一步)
- [9. 复现命令与产物](#9-复现命令与产物)
<!-- TOC END -->

## 1. 阶段目标

P7-B 的目标是验证：在不训练 PASDF/SDF 主干的前提下，PASDF object score、P7-A template residual、assignment entropy、residual overlap 和 registration confidence 能否通过轻量 calibration 修复 positive false positive 与 object boundary。

本阶段特别关注：

- `cap3_positive9/7/10` 是否能被压低。
- `tap1` soft object boundary 是否能变成 strict pass。
- `helmet1` positive boundary confusion 是否缓解。
- `ashtray0` control 是否保持不退化。

## 2. 本轮实现

新增代码：

- `src/pcdad/calibration/__init__.py`
- `src/pcdad/calibration/positive_aware.py`
- `scripts/train_p7_calibration.py`
- `tests/test_positive_aware_calibration.py`
- `tests/test_train_p7_calibration_cli.py`

核心能力：

- 读取 P7-A `per_sample_scores.csv` 为统一 `CalibrationRecord`。
- 输出 positive-aware `boundary_margin = min_anomaly_score - max_positive_score`。
- 支持 `pasdf_raw`、`template_residual`、`confidence_gate`、`isotonic_pasdf`、`isotonic_gated`、`logistic_l2`。
- 支持 `diagnostic_oracle` 与 `leave_one_class_out` 两种 split。
- 输出 `calibration_records.csv`、`metrics.csv`、`boundary_margin.csv` 和 `failure_toplist.csv`。

## 3. 实验设置

输入：

```text
experiments/P7_A_multitemplate/four_class_train_pcd/per_sample_scores.csv
```

输出：

```text
experiments/P7_B_calibration/four_class/
  README.md
  boundary_margin.csv
  calibration_records.csv
  config.yaml
  failure_toplist.csv
  git_hash.txt
  metrics.csv
```

类别：

```text
cap3 tap1 helmet1 ashtray0
```

方法：

```text
pasdf_raw
template_residual
confidence_gate
isotonic_pasdf
isotonic_gated
logistic_l2
```

注意：`diagnostic_oracle` 使用四类 test label，只能解释 calibration 上限；`leave_one_class_out` 更接近跨类泛化，但样本量仍小，不能当作完整泛化证明。

## 4. 总体结果

选取主要方法结果如下。`boundary_margin` 越大越好，大于 0 才是 strict pass。

| 类别 | 方法 | split | AUROC | AUPR | boundary margin | strict | false positive top1 |
|---|---|---|---:|---:|---:|---|---|
| `cap3` | `pasdf_raw` | `none` | 0.575439 | 0.579692 | -0.103125 | False | `cap3_positive9` |
| `cap3` | `confidence_gate` | `none` | 0.575439 | 0.585245 | -0.030724 | False | `cap3_positive7` |
| `cap3` | `template_residual` | `none` | 0.571930 | 0.633048 | -0.018249 | False | `cap3_positive9` |
| `cap3` | `logistic_l2` | `diagnostic_oracle` | 0.722807 | 0.730090 | -0.009425 | False | `cap3_positive13` |
| `cap3` | `logistic_l2` | `leave_one_class_out:cap3` | 0.578947 | 0.581831 | -0.022344 | False | `cap3_positive9` |
| `tap1` | `pasdf_raw` | `none` | 0.770370 | 0.879436 | -0.002310 | False | `tap1_positive14` |
| `tap1` | `confidence_gate` | `none` | 0.777778 | 0.882106 | -0.000980 | False | `tap1_positive14` |
| `tap1` | `logistic_l2` | `leave_one_class_out:tap1` | 0.770370 | 0.880095 | -0.000711 | False | `tap1_positive7` |
| `tap1` | `isotonic_pasdf` | `diagnostic_oracle` | 0.870370 | 0.878472 | 0.000000 | False | `tap1_positive9` |
| `helmet1` | `pasdf_raw` | `none` | 0.885714 | 0.901623 | -0.007603 | False | `helmet1_positive6` |
| `helmet1` | `confidence_gate` | `none` | 0.866667 | 0.885363 | -0.003491 | False | `helmet1_positive6` |
| `helmet1` | `logistic_l2` | `diagnostic_oracle` | 0.700000 | 0.725784 | -0.048054 | False | `helmet1_positive6` |
| `ashtray0` | `pasdf_raw` | `none` | 1.000000 | 1.000000 | 0.025778 | True | `ashtray0_positive6` |
| `ashtray0` | `confidence_gate` | `none` | 1.000000 | 1.000000 | 0.010904 | True | `ashtray0_positive6` |
| `ashtray0` | `logistic_l2` | `leave_one_class_out:ashtray0` | 0.785714 | 0.885106 | -0.051516 | False | `ashtray0_positive10` |

## 5. cap3 重点样本

| 样本 | label | 方法 | split | PASDF | registration confidence | calibrated |
|---|---:|---|---|---:|---:|---:|
| `cap3_positive9` | 0 | `pasdf_raw` | `none` | 0.109517 | 0.270470 | 0.109517 |
| `cap3_positive9` | 0 | `confidence_gate` | `none` | 0.109517 | 0.270470 | 0.029621 |
| `cap3_positive9` | 0 | `logistic_l2` | `diagnostic_oracle` | 0.109517 | 0.270470 | 0.441390 |
| `cap3_positive9` | 0 | `logistic_l2` | `leave_one_class_out:cap3` | 0.109517 | 0.270470 | 0.517078 |
| `cap3_positive7` | 0 | `pasdf_raw` | `none` | 0.096982 | 0.344184 | 0.096982 |
| `cap3_positive7` | 0 | `confidence_gate` | `none` | 0.096982 | 0.344184 | 0.033380 |
| `cap3_hole0` | 1 | `pasdf_raw` | `none` | 0.006392 | 0.415500 | 0.006392 |
| `cap3_hole0` | 1 | `confidence_gate` | `none` | 0.006392 | 0.415500 | 0.002656 |
| `cap3_hole0` | 1 | `logistic_l2` | `diagnostic_oracle` | 0.006392 | 0.415500 | 0.502834 |
| `cap3_hole0` | 1 | `logistic_l2` | `leave_one_class_out:cap3` | 0.006392 | 0.415500 | 0.494734 |

## 6. 结果解释

第一，`confidence_gate` 是最稳的保守后处理。它把 `cap3` boundary margin 从 `-0.103125` 缩小到 `-0.030724`，把 `cap3_positive9` 从 `0.109517` 压到 `0.029621`。但它同时也压低弱 anomaly，例如 `cap3_hole0` 从 `0.006392` 压到 `0.002656`，所以不能形成 strict pass。

第二，`logistic_l2 diagnostic_oracle` 能把 `cap3` margin 推到 `-0.009425`，并将 false-positive top1 从 `cap3_positive9` 换成 `cap3_positive13`。这说明结构化特征确实有信息量。但 oracle 使用了同一批 test label，只能作为上限证据；在 `leave_one_class_out:cap3` 下 margin 回到 `-0.022344`，`cap3_positive9` 仍是 top false positive。

第三，`tap1` 只达到接近 strict 的 soft 状态。`isotonic_pasdf diagnostic_oracle` 的 margin 为 `0.000000`，不是严格大于 0；`leave_one_class_out` 仍为负。因此 P7-B 没有真正解决 `tap1` object boundary。

第四，`helmet1` 不适合当前 object-level calibration。`confidence_gate` 能缩小负 margin，但 `logistic_l2` 反而明显变差。这与 P6 判断一致：`helmet1` 更需要点级定位或训练型 discriminative SDF。

第五，`ashtray0` 是重要 control。PASDF raw 已 strict pass，confidence gate 仍 strict pass；但 learned logistic 在 leave-one-class-out 下破坏 control。这说明小样本 learned calibration 有过拟合/跨类不稳风险，不能作为 P7-B 正结果包装。

## 7. 阶段结论

P7-B 的工程目标已完成：

- calibration 模块和 CLI 已实现。
- 四类 P7-B 实验已跑通。
- 输出了同口径 records、metrics、boundary、failure toplist。
- 明确区分了 diagnostic oracle 和 leave-one-class-out。

但 P7-B 没有达到理想正结果：

- `cap3/tap1/helmet1` 都没有变成 strict pass。
- confidence gate 有保守收益，但会同步压低弱 anomaly。
- learned calibration 在 oracle 下有上限信号，在 leave-one-class-out 下不稳定。
- `ashtray0` control 显示 learned head 可能破坏原本已经好的类别。

因此本阶段结论是：

> P7-B 是有效的 non-training upper-bound 评估与负结果。它证明 registration confidence 可以压缩一部分 false positive 幅度，但 object-level 后处理不足以稳定修复主要 failure mode。下一步应进入 P7-C pseudo anomaly + discriminative SDF smoke。

## 8. 下一步

建议进入 P7-C：

1. 先写 `docs/document/tech_arche/P7_C_pseudo_anomaly_discriminative_sdf_plan.md`。
2. 从 `helmet1` 或 `tap1` 开始单类训练 smoke，`ashtray0` 作为 control。
3. 先实现 pseudo anomaly generation 的可视化和统计，再接训练。
4. 保留 P7-B 的 `confidence_gate` 作为 reporting feature，不把 learned calibration 作为主模块。
5. Real3D-AD 仍按计划放到 P9/P10，不插入 P7-C 起点。

## 9. 复现命令与产物

复现命令：

```bash
docker exec Anomaly bash -lc 'cd /workspace/code_folder/area1/Anomaly && PYTHONPATH=src /workspace/.conda/envs/pasdf/bin/python scripts/train_p7_calibration.py --input-csv experiments/P7_A_multitemplate/four_class_train_pcd/per_sample_scores.csv --output-dir experiments/P7_B_calibration/four_class --classes cap3 tap1 helmet1 ashtray0'
```

实验目录：

```text
experiments/P7_B_calibration/four_class/
```

阶段 CSV：

```text
docs/document/stage_record/2026-06-22_p7_b_positive_calibration_summary.csv
```

运行时记录的 git hash：

```text
045d560b044d817029a9a1a4e4900df702cb8a61
```
