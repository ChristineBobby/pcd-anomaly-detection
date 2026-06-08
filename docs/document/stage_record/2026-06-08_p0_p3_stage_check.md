# 阶段记录：P0-P3 状态检查（2026-06-08）

## 目录

- [1. 记录范围](#1-记录范围)
- [2. 总体结论](#2-总体结论)
- [3. 仓库与运行环境](#3-仓库与运行环境)
- [4. P0-P2 前置阶段状态](#4-p0-p2-前置阶段状态)
- [5. P3 PASDF 复现状态](#5-p3-pasdf-复现状态)
- [6. 代码质量与验证证据](#6-代码质量与验证证据)
- [7. 当前风险与未闭合事项](#7-当前风险与未闭合事项)
- [8. 下一阶段建议](#8-下一阶段建议)

---

## 1. 记录范围

本文件记录截至 2026-06-08 的阶段性检查结果，覆盖：

- P0 项目启动与仓库初始化。
- P1 Docker/Conda/PASDF 环境配置。
- P2 Anomaly-ShapeNet 数据准备、统计、DataLoader 与可视化 smoke。
- P3 PASDF 官方权重在 Anomaly-ShapeNet 40 类协议上的复现结果。

本记录只总结阶段状态和证据，不替代各阶段执行手册。详细过程仍以以下文件为准：

- `docs/document/P1_environment_setup_execution.md`
- `docs/document/P2_data_preparation_execution.md`
- `docs/document/P3_pasdf_reproduction_execution.md`
- `docs/document/SOP_engineering_workflow.md`

---

## 2. 总体结论

当前主线结论：P3 PASDF 官方权重复现已经达到预期，可以进入 P4/P5 的几何增强与失败分析阶段。

关键证据：

- Anomaly-ShapeNet 固定 40 类协议已跑满。
- 全量评估结果包含 40 类。
- mean object AUROC 为 `0.900214149779`，即 `90.0214%`。
- 相比研究计划和 SOP 中的 PASDF 论文目标 O-AUROC `90.0%`，差值为 `+0.0214` 个百分点。
- mean pixel AUROC 为 `0.896009030694`，可作为后续点级增强 baseline。

需要严格区分：

- 实验复现指标已经达标。
- 部分实验原始产物目前是本机存在但未进入 git，例如 `experiments/E1_pasdf_baseline/` 和 `experiments/data_stats.md`。
- P3 文档已经把关键命令、配置路径、日志路径、结果摘要和完整 40 类结果表写入版本库。

---

## 3. 仓库与运行环境

### 3.1 Git 状态

阶段检查时的仓库状态：

```text
branch: main
remote: origin/main
status: ahead 1
latest_commit: 56d0cab feat(pasdf): add official evaluation adapter
```

说明：

- 当前有 1 个本地提交尚未推送到远程。
- 数据、权重、实验输出按项目约定不直接提交。
- Git 操作应在宿主机终端执行，不在 Docker 容器内执行。

### 3.2 Docker 环境

当前使用容器：

```text
container_id: 2114d157b2cf
container_name: boring_goldstine
image: continuumio/miniconda3:latest
repo_mount: /workspace/code_folder/area1/Anomaly
conda_env: pasdf
python: Python 3.10.20
python_path: /workspace/.conda/envs/pasdf/bin/python
```

运行约定：

- 训练、评估、测试、依赖验证在 Docker 容器内进行。
- git pull、git commit、git push 在宿主机终端进行。
- 大型 PyTorch 包下载优先考虑关闭代理并使用清华镜像源。

---

## 4. P0-P2 前置阶段状态

### 4.1 P0 项目启动

P0 已完成的内容：

- GitHub 仓库已建立：`https://github.com/ChristineBobby/pcd-anomaly-detection.git`
- 项目基础目录、配置、测试框架、文档目录已建立。
- `docs/document/SERVER_AGENT_KICKOFF.md` 作为会话启动提示词保留。
- 当前 repo 已可进行容器内测试与本机 git 管理。

当前状态判断：

```text
P0 status: closed
```

### 4.2 P1 环境配置

P1 已完成的内容：

- Docker 容器中创建并使用 `pasdf` conda 环境。
- PASDF 官方依赖链已打通。
- Open3D、PyTorch3D、CUDA smoke、PyTorch3D chamfer smoke 等关键项此前已验证。
- 环境配置冲突、代理、镜像源、Google Drive 下载注意事项已写入 `P1_environment_setup_execution.md`。

当前状态判断：

```text
P1 status: closed
```

### 4.3 P2 数据准备

P2 已完成的内容：

- Anomaly-ShapeNet-v2 数据集已解压并整理。
- 原始数据统计已产出到 `experiments/data_stats.md`。
- 结论：当前课程包是高密度点云版本，原始点数范围为 `17422-157824`，高于公开描述中的 8K-30K。
- 已生成 PASDF 评估使用的固定 `16384` 点目录。
- DataLoader 已实现并通过单测。
- 已抽样生成点云、法向、GT 可视化 smoke SVG。

固定 16384 点目录复核：

```text
path: data/Anomaly-ShapeNet-v2/dataset/16384
classes: 40
pcd_files: 1472
point_count: all 16384
manifest: data/Anomaly-ShapeNet-v2/dataset/16384/preprocess_manifest.json
```

当前状态判断：

```text
P2 status: closed
```

注意：

- `experiments/data_stats.md` 和 `experiments/p2_smoke/` 目前被 `.gitignore` 忽略，是本机产物。
- P2 执行记录已在 `docs/document/P2_data_preparation_execution.md` 中保留。

---

## 5. P3 PASDF 复现状态

### 5.1 代码框架

P3 新增代码遵循“本项目适配层 + 第三方官方入口”的设计：

```text
src/pcdad/models/pasdf_adapter.py
scripts/evaluate.py
tests/test_pasdf_adapter.py
tests/test_evaluate.py
docs/document/P3_pasdf_reproduction_execution.md
```

设计原则：

- 不修改 `third_party/PASDF` 源码。
- 通过本项目 adapter 生成官方 `Test/AD_test.py` 可读的 YAML。
- `scripts/evaluate.py` 保持薄 CLI，只负责参数解析、路径解析、配置生成、官方命令执行和结果摘要。
- 单测不依赖 GPU、权重或 PASDF import，主要覆盖配置生成、类别校验、命令生成、CSV 解析和 dry-run 行为。

### 5.2 官方资产

PASDF 官方资产当前状态：

```text
third_party/PASDF commit: fea90dbce1998ef7bda266e388c34a6079c1bc5e
template_dirs: 40
template_obj_files: 40
weights.pt files: 40
runs_sdf size: about 62M
ShapeNetAD template assets size: about 148M
```

下载注意事项：

- `gdown --folder` 下载 `results/ShapeNetAD` 时会在 optimizer state 文件处失败。
- PASDF evaluation 不需要 optimizer state。
- 实际采用单文件 ID 批量下载各类 `weights.pt`。
- 单文件下载需要 `gdown --no-cookies`。

### 5.3 Smoke Evaluation

Smoke 类别：

```text
class: ashtray0
```

结果：

```csv
class,pixel_auc,object_auc
ashtray0,0.9184445496911406,1.0
```

输出路径：

```text
experiments/E1_pasdf_baseline/smoke_ashtray0/pasdf_test_ShapeNetAD.yaml
experiments/E1_pasdf_baseline/smoke_ashtray0/run.log
experiments/E1_pasdf_baseline/smoke_ashtray0/evaluation_results.csv
```

判断：

```text
P3 smoke status: passed
```

### 5.4 Full 40-Class Evaluation

全量命令：

```bash
PYTHONPATH=src CUDA_VISIBLE_DEVICES=0 python scripts/evaluate.py \
  --config configs/experiment/E1_pasdf_baseline.yaml \
  --output-dir experiments/E1_pasdf_baseline/full_40cls
```

输出路径：

```text
experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml
experiments/E1_pasdf_baseline/full_40cls/run.log
experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv
```

结果摘要：

```text
classes: 40
mean_pixel_auc: 0.896009030694
mean_object_auc: 0.900214149779
paper_object_target: 90.0%
object_delta_pp: +0.0214
min_pixel: helmet1 = 0.6227453698428423, object = 0.9571428571428571
min_object: cap3 = 0.5508771929824561, pixel = 0.8469283758563578
```

低分样本：

```text
object_auc < 0.8:
cap3, cap4, cap5, helmet2, microphone0, shelf0, tap1

pixel_auc < 0.85:
bowl2, cap3, headset1, helmet0, helmet1, helmet2, vase1
```

日志检查：

```text
Traceback: 0
runtime error keywords: 0
nan/inf numeric issue: 0
Open3D "Too few correspondences" warnings: 53
```

说明：

- 日志中的 `inf` 命中来自 printed config 单词，不是数值异常。
- Open3D correspondence warning 是真实风险信号，后续应优先结合低分类别分析 registration 质量。

当前状态判断：

```text
P3 full status: passed
P3 metric DoD: met
```

---

## 6. 代码质量与验证证据

阶段检查时，在 Docker 容器 `boring_goldstine` 的 `pasdf` 环境中重新执行了质量门禁。

命令与结果：

```text
ruff check .
result: All checks passed!

black --check .
result: 23 files would be left unchanged.

mypy src/pcdad
result: Success: no issues found in 12 source files

PYTHONPATH=src pytest -q
result: 28 passed in 1.90s

pre-commit run --all-files
result: all configured hooks passed
```

判断：

```text
code_quality_status: passed
unit_test_status: passed
pre_commit_status: passed
```

---

## 7. 当前风险与未闭合事项

### 7.1 原始实验产物未入库

当前以下路径被 `.gitignore` 忽略：

```text
experiments/E1_pasdf_baseline/
experiments/data_stats.md
experiments/p2_smoke/
```

影响：

- 不影响本机复现实验结论。
- 不影响 P3 文档中的结果摘要和完整 40 类表。
- 但若严格执行 SOP 中“结果表入库”的要求，需要后续决定是否对白名单结果 CSV、压缩日志摘要或 stage record 附件开放 git 跟踪。

建议：

- 保持大体量日志和可视化图仍然不入库。
- 可以考虑新增 `experiments/records/` 或 `docs/document/stage_record/artifacts/`，只提交轻量 CSV、指标摘要和日志摘要。

### 7.2 PASDF 官方评估口径与通用数据配置命名容易混淆

现状：

- `configs/data/anomaly_shapenet.yaml` 中有通用字段 `normalize: unit_sphere`。
- PASDF 官方评估生成 YAML 使用 `normalize: false`。
- 固定 16384 点数据 manifest 中记录 `normalize: none`。

判断：

- 当前 P3 结果没有因此出错。
- PASDF 评估使用的是官方口径 `normalize: false`。
- 但配置层容易让后续读者误解。

建议：

- P4 开始前，把 PASDF 专用数据口径显式写入 `experiment.pasdf` 或单独配置文件。
- 在配置注释或文档中区分“通用 DataLoader normalization”和“PASDF official evaluation normalization”。

### 7.3 低分类别和 Open3D warning 需要进入失败分析

优先类别：

```text
cap3, cap4, cap5, helmet1, helmet2, tap1, shelf0, microphone0
```

优先问题：

- registration 是否失败或不稳定。
- voxel size 是否需要 per-class 调整。
- template matching 是否选错 canonical template。
- 异常类型是否集中在 crack/hole/sink 等局部几何变化。
- 点级低分但对象级高分的类别，例如 `helmet1`，需要区分定位失败和检测成功。

---

## 8. 下一阶段建议

建议 P4 从“失败分析 + 评估资产固化”开始，而不是马上叠加复杂增强模块。

优先任务：

1. 固化轻量结果记录机制：决定哪些 CSV、summary、log excerpt 可以进入 git。
2. 为 P3 低分类别生成 per-sample 分数、异常类型分组和可视化热力图。
3. 统计 Open3D correspondence warning 对应的类别和样本。
4. 做 voxel size 小网格扫描，至少覆盖 `cap3/cap4/cap5/helmet2/tap1`。
5. 再进入几何残差增强：法向残差、多尺度曲率残差、多尺度 top-k 与局部一致性。

阶段进入判断：

```text
ready_for_p4: yes
blocking_issue: none
recommended_first_p4_topic: PASDF failure analysis and artifact tracking policy
```
