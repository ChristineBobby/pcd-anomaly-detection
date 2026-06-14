# P7-A 多模板与配准置信度阶段记录

撰写日期：2026-06-14

文档定位：本文件记录 P7-A 的实现、实验结果与阶段判断。它承接 `docs/document/tech_arche/P7_A_template_bank_and_registration_confidence_plan.md`、`docs/document/SOP_P7_innovation_workflow.md` 和 P6 failure closure。

<!-- TOC START -->
## 目录

- [1. 阶段目标](#1-阶段目标)
- [2. 本轮实现](#2-本轮实现)
- [3. 实验设置](#3-实验设置)
- [4. 总体结果](#4-总体结果)
- [5. cap3 重点样本](#5-cap3-重点样本)
- [6. 结果解释](#6-结果解释)
- [7. 阶段结论](#7-阶段结论)
- [8. 下一步建议](#8-下一步建议)
- [9. 复现命令与产物](#9-复现命令与产物)
<!-- TOC END -->

## 1. 阶段目标

P7-A 的目标不是直接训练新模型，而是先回答一个工程和研究判断问题：

> `cap3_positive9/7/10` 的 PASDF false positive 能否通过 normal template bank 与 registration confidence 得到解释或缓解？

P6 已经把 `cap3` 收口为 registration/template false positive。本阶段在 P5 per-point PASDF score 的基础上，对 `cap3/tap1/helmet1/ashtray0` 四类计算 train PCD 多模板 residual、template assignment、top-1/top-2 margin、assignment entropy、PASDF/residual top-k overlap 和 registration confidence。

## 2. 本轮实现

新增和更新的主要代码：

- `src/pcdad/prototypes/template_bank.py`：定义 `TemplatePrototype`、`TemplateAssignment`，实现多模板 residual 排序、overlap、entropy 和 confidence 特征。
- `src/pcdad/prototypes/registration_confidence.py`：把 residual、entropy、overlap、局部集中度转成 `registration_confidence` 与 `risk_reason`。
- `scripts/run_p7_multitemplate.py`：新增 P7-A CLI，支持 `pasdf_obj` 与 `train_pcd` 两种模板模式。
- `tests/test_template_bank.py`、`tests/test_registration_confidence.py`、`tests/test_run_p7_multitemplate_cli.py`：覆盖排序、overlap、confidence、CLI 输出和 `train_pcd` 多模板读取。

关键补充：

- `pasdf_obj` 保持 P3/P5/P6 的 PASDF 官方 OBJ 单模板口径。
- `train_pcd` 使用 `data/Anomaly-ShapeNet-v2/dataset/16384/<class>/train/*.pcd`，每类 4 个 normal templates，是本阶段真多模板实验口径。
- `per_sample_scores.csv` 已直接输出 `top2_nn_topk_mean`、`top1_top2_margin`、`top1_top2_relative_margin`，不需要后处理脚本再反算。

## 3. 实验设置

输入：

```text
score_root: experiments/P5_pasdf_scores/representative
template_root: data/Anomaly-ShapeNet-v2/dataset/16384
template_mode: train_pcd
classes:
  - cap3
  - tap1
  - helmet1
  - ashtray0
top_ratio: 0.01
```

样本与模板规模：

| 类别 | P5 score 样本数 | train PCD templates | top-1 template |
|---|---:|---:|---|
| `cap3` | 34 | 4 | `cap3_template0` for all samples |
| `tap1` | 33 | 4 | `tap1_template3` for all samples |
| `helmet1` | 29 | 4 | `helmet1_template0` for all samples |
| `ashtray0` | 29 | 4 | `ashtray0_template2` for all samples |

输出：

```text
experiments/P7_A_multitemplate/four_class_train_pcd/
  README.md
  config.yaml
  failure_toplist.csv
  git_hash.txt
  per_sample_scores.csv
  template_assignments.csv
```

## 4. 总体结果

本轮共输出：

- `template_assignments.csv`：500 条 assignment，等于 125 个样本乘以 4 个模板。
- `per_sample_scores.csv`：125 条 top-1 per-sample 记录。
- risk 分布：122 个 `moderate_registration_risk`，3 个 `template_mismatch_risk`。

按 class 和 label 聚合如下：

| 类别 | label | n | mean PASDF object | mean top-1 residual | mean top1-top2 margin | mean entropy | mean overlap | mean confidence | max PASDF object |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `ashtray0` | 0 | 15 | 0.004438 | 0.215932 | 0.080969 | 0.661740 | 0.004065 | 0.421359 | 0.005049 |
| `ashtray0` | 1 | 14 | 0.056610 | 0.218710 | 0.080156 | 0.662892 | 0.029617 | 0.414408 | 0.081680 |
| `cap3` | 0 | 15 | 0.032340 | 0.262006 | 0.035786 | 0.639229 | 0.067886 | 0.399334 | 0.109517 |
| `cap3` | 1 | 19 | 0.029329 | 0.261857 | 0.039744 | 0.610973 | 0.000000 | 0.415485 | 0.074786 |
| `helmet1` | 0 | 15 | 0.019209 | 0.125091 | 0.047511 | 0.649726 | 0.000813 | 0.499932 | 0.026289 |
| `helmet1` | 1 | 14 | 0.025223 | 0.126672 | 0.045847 | 0.654253 | 0.047474 | 0.485751 | 0.032876 |
| `tap1` | 0 | 15 | 0.002928 | 0.197046 | 0.240588 | 0.581758 | 0.102032 | 0.411358 | 0.003705 |
| `tap1` | 1 | 18 | 0.023089 | 0.196133 | 0.241052 | 0.581802 | 0.039295 | 0.427487 | 0.065518 |

## 5. cap3 重点样本

`cap3_positive9/7/10` 仍然是 positive control 中最需要解释的 false positive。多模板 top-1 全部选择 `cap3_template0`，说明当前 template bank 没有自动切换到一个能明显缓解错配的模板。

| 样本 | label | top-1 template | PASDF object | top-1 residual | top-2 residual | margin | relative margin | entropy | overlap | confidence | risk |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `cap3_positive9` | 0 | `cap3_template0` | 0.109517 | 0.275955 | 0.280282 | 0.004327 | 0.015680 | 0.778389 | 0.634146 | 0.270470 | `template_mismatch_risk` |
| `cap3_positive7` | 0 | `cap3_template0` | 0.096982 | 0.262592 | 0.284323 | 0.021731 | 0.082756 | 0.736778 | 0.384146 | 0.344184 | `template_mismatch_risk` |
| `cap3_positive10` | 0 | `cap3_template0` | 0.064902 | 0.256855 | 0.281676 | 0.024821 | 0.096634 | 0.728594 | 0.000000 | 0.388208 | `moderate_registration_risk` |
| `cap3_hole0` | 1 | `cap3_template0` | 0.006392 | 0.262193 | 0.300502 | 0.038309 | 0.146110 | 0.609677 | 0.000000 | 0.415500 | `moderate_registration_risk` |
| `cap3_hole1` | 1 | `cap3_template0` | 0.010446 | 0.264764 | 0.300251 | 0.035487 | 0.134033 | 0.614375 | 0.000000 | 0.412941 | `moderate_registration_risk` |
| `cap3_broken2` | 1 | `cap3_template0` | 0.012887 | 0.263262 | 0.303421 | 0.040159 | 0.152544 | 0.601091 | 0.000000 | 0.417046 | `moderate_registration_risk` |
| `cap3_broken3` | 1 | `cap3_template0` | 0.028583 | 0.258799 | 0.307432 | 0.048633 | 0.187918 | 0.582274 | 0.000000 | 0.424631 | `moderate_registration_risk` |

最高风险样本：

| 类别 | 样本 | label | PASDF object | top-1 residual | margin | entropy | overlap | confidence | risk |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `cap3` | `cap3_positive9` | 0 | 0.109517 | 0.275955 | 0.004327 | 0.778389 | 0.634146 | 0.270470 | `template_mismatch_risk` |
| `ashtray0` | `ashtray0_bulge1` | 1 | 0.065764 | 0.254615 | 0.043202 | 0.710953 | 0.353659 | 0.307984 | `template_mismatch_risk` |
| `cap3` | `cap3_positive7` | 0 | 0.096982 | 0.262592 | 0.021731 | 0.736778 | 0.384146 | 0.344184 | `template_mismatch_risk` |

## 6. 结果解释

第一，P7-A 完成了真多模板 I/O 与诊断闭环，但没有解决 `cap3` false positive。四个类虽然每类都有 4 个 train PCD templates，但 top-1 template 在每个类内部完全固定。这说明当前 nearest-template residual 更像是在选择一个类内代表模板，而不是针对每个 sample 的姿态或结构差异进行有效匹配。

第二，`cap3_positive9` 的信号仍然非常明确：PASDF object score 最高，top-1/top-2 relative margin 只有 0.015680，assignment entropy 达到 0.778389，PASDF top-k 与 residual top-k overlap 为 0.634146，registration confidence 只有 0.270470。这个样本不是被多模板消掉了，而是被多模板诊断为高不确定、高错配风险的 false positive。

第三，`cap3_positive7` 也被标成 `template_mismatch_risk`，但 `cap3_positive10` 只落在 `moderate_registration_risk`。原因是 `positive10` 的 residual overlap 为 0，说明它的 PASDF 高分区域不再和 train PCD residual top-k 强重叠。它仍有高 entropy 和低 margin，但不能简单归因为同一种 high PASDF/high residual overlap。

第四，`cap3` 的 anomaly controls 在 top-1 residual 上与 positives 非常接近，甚至均值几乎相同：positive mean top-1 residual 为 0.262006，anomaly mean top-1 residual 为 0.261857。这说明单靠 template residual 不能作为 anomaly score，否则会继续混淆 positive control 与真实 anomaly。

第五，`tap1` 的 top1-top2 margin 明显更大，均值约 0.24，说明它的 template selection 比 `cap3` 稳定。但 `tap1` 的 PASDF object score 对 positive 和 anomaly 的区分仍主要来自 PASDF 本身，而不是 template residual。它仍应按 P6 的 soft object boundary 路线进入 positive-aware calibration 或训练型局部判别。

## 7. 阶段结论

P7-A 的最低目标已经完成：

- 已建立可复用 prototype-bank 模块。
- 已支持 `pasdf_obj` 与 `train_pcd` 两种模板源。
- 已对 `cap3/tap1/helmet1/ashtray0` 输出多模板 assignment、registration confidence、top-1/top-2 margin 和 risk toplist。
- 已给出 `cap3_positive9/7/10` 与 anomaly controls 的数值对照。

但 P7-A 的理想目标没有达到：

- train PCD 多模板没有显著压低 `cap3_positive9/7/10`。
- top-1 template 在类内固定，说明当前策略缺少 explicit registration 或更强的局部 shape encoding。
- template residual 与 anomaly label 的分离度不足，不能直接作为 object score。

因此，本阶段结论是：

> P7-A 可作为 registration/template mismatch diagnostic feature source，但不能作为独立修复方法。下一步不应继续无约束增加模板数量，而应进入 P7-B positive-aware calibration，并同步规划 P7-C discriminative SDF / pseudo anomaly 训练型模块。

## 8. 下一步建议

优先进入 P7-B：

- 输入使用 `experiments/P7_A_multitemplate/four_class_train_pcd/per_sample_scores.csv`。
- 特征包括 PASDF object score、top-1 residual、top1-top2 margin、assignment entropy、residual overlap、registration confidence。
- 评价必须 positive-aware，至少报告 `max positive - min anomaly` boundary margin，不能只看 AUROC。
- 需要明确标注 calibration 是否使用测试标签。若使用四类测试标签，只能作为 diagnostic upper-bound 或 smoke，不作为严格泛化 claim。

并行准备 P7-C：

- `cap3` 需要 explicit registration 或 registration-invariant feature。
- `helmet1` 和 `tap1` 更适合做 pseudo anomaly + discriminative SDF smoke，因为它们的主要问题分别是点级定位弱和 soft boundary。
- 8 张 4090 应优先用于 P7-C/P8 训练型实验，而不是继续 CPU 最近邻诊断。

## 9. 复现命令与产物

复现命令：

```bash
docker exec 0613 bash -lc 'cd /workspace/code_folder/area1/Anomaly && PYTHONPATH=src /workspace/.conda/envs/pasdf/bin/python scripts/run_p7_multitemplate.py --score-root experiments/P5_pasdf_scores/representative --template-root data/Anomaly-ShapeNet-v2/dataset/16384 --template-mode train_pcd --classes cap3 tap1 helmet1 ashtray0 --output-dir experiments/P7_A_multitemplate/four_class_train_pcd --top-ratio 0.01'
```

实验目录：

```text
experiments/P7_A_multitemplate/four_class_train_pcd/
```

阶段 CSV：

```text
docs/document/stage_record/2026-06-14_p7_a_multitemplate_registration_summary.csv
```

本次未提交状态下运行时记录的 git hash：

```text
69708552bf53d80d21765e774992bc2319e07965
```
