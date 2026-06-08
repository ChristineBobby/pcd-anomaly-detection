# 3D 点云缺陷检测项目 · 生产级工程 SOP

文档定位：本文件是《3d_point_cloud_defect_detection_research_plan.md》的**可执行落地手册**。Plan 回答"做什么/为什么"，本 SOP 回答"怎么做、按什么规范做"。
适用对象：5 人团队，远程 Linux 服务器（4×RTX 4090 48G），本地 Windows 仅开发/文档。
约束等级：**生产级**。所有代码、提交、实验都按下述规范执行，不走"能跑就行"的捷径。

---

<!-- TOC START -->
## 目录

- [0. 总览：从零到答辩的 7 个阶段](#0-总览从零到答辩的-7-个阶段)
  - [外部依据核验](#外部依据核验)
- [1. Codebase 目录架构](#1-codebase-目录架构)
- [2. P0 — 仓库与协作基建（第 1 天，由 E 负责）](#2-p0--仓库与协作基建第-1-天由-e-负责)
  - [Entry](#entry)
  - [Steps](#steps)
  - [DoD](#dod)
- [3. P1 — 环境搭建（第 1-2 天，由 C 负责）](#3-p1--环境搭建第-1-2-天由-c-负责)
  - [Entry](#entry-1)
  - [Steps（PASDF 主力环境）](#stepspasdf-主力环境)
  - [DoD](#dod-1)
- [4. P2 — 数据准备（第 1-4 天，由 B 负责）](#4-p2--数据准备第-1-4-天由-b-负责)
  - [Entry](#entry-2)
  - [Steps](#steps-1)
  - [DoD](#dod-2)
- [5. P3 — PASDF 复现（第 3-10 天，由 C 负责）](#5-p3--pasdf-复现第-3-10-天由-c-负责)
  - [Entry](#entry-3)
  - [Steps](#steps-2)
  - [DoD](#dod-3)
- [6. P4 — 失败分析与几何增强开发（第 11-17 天，由 D 主责，B/C/E 协作）](#6-p4--失败分析与几何增强开发第-11-17-天由-d-主责bce-协作)
  - [Entry](#entry-4)
  - [Steps](#steps-3)
  - [DoD](#dod-4)
  - [进度快于预期时的扩展门](#进度快于预期时的扩展门)
- [7. P5 — 实验消融与跨数据集验证（第 11-23 天，由 D/C 主责，B/E 协作）](#7-p5--实验消融与跨数据集验证第-11-23-天由-dc-主责be-协作)
  - [Entry](#entry-5)
  - [Steps](#steps-4)
  - [DoD](#dod-5)
  - [进度快于预期时的扩展门](#进度快于预期时的扩展门-1)
- [8. P6 — 交付归档与答辩冻结（第 24-30 天，由 A/E 主责，全员协作）](#8-p6--交付归档与答辩冻结第-24-30-天由-ae-主责全员协作)
  - [Entry](#entry-6)
  - [Steps](#steps-5)
  - [DoD](#dod-6)
  - [进度快于预期时的扩展门](#进度快于预期时的扩展门-2)
- [9. 代码工作流规范（贯穿全程，强制）](#9-代码工作流规范贯穿全程强制)
  - [9.1 分支模型（轻量 GitHub Flow）](#91-分支模型轻量-github-flow)
  - [9.2 Docker 与 Git 操作边界](#92-docker-与-git-操作边界)
  - [9.3 提交规范（Conventional Commits）](#93-提交规范conventional-commits)
  - [9.4 Pull Request 规范](#94-pull-request-规范)
  - [9.5 .gitignore 要点](#95-gitignore-要点)
  - [9.6 实验可复现铁律](#96-实验可复现铁律)
- [10. 代码质量：模块化、规范性、简洁性审查](#10-代码质量模块化规范性简洁性审查)
  - [10.1 模块化要求](#101-模块化要求)
  - [10.2 规范性（自动化，非人肉）](#102-规范性自动化非人肉)
  - [10.3 简洁性检查（每次 PR 自检 + Review 把关）](#103-简洁性检查每次-pr-自检--review-把关)
  - [10.4 测试要求](#104-测试要求)
- [11. 团队协作日常](#11-团队协作日常)
- [12. 快速命令速查（Makefile 封装）](#12-快速命令速查makefile-封装)
- [附：第 1 天 checklist（照做即可启动）](#附第-1-天-checklist照做即可启动)
<!-- TOC END -->

## 0. 总览：从零到答辩的 7 个阶段

| 阶段 | 名称 | 核心产出 | 对应 Plan 排期 |
|---|---|---|---|
| P0 | 仓库与协作基建 | GitHub 仓库 + CI + 规范文件 | 第 1 天 |
| P1 | 环境搭建 | 可复现的 conda 环境 + 依赖锁 | 第 1-2 天 |
| P2 | 数据准备 | 标准化数据集 + 统计报告 + DataLoader | 第 1-4 天 |
| P3 | PASDF 复现 | 官方权重评估复现 SOTA | 第 3-10 天 |
| P4 | 失败分析与几何增强开发 | 失败诊断 + 法向/曲率/聚合模块 + 单测 | 第 11-17 天 |
| P5 | 实验消融与跨数据集验证 | A1-A6 结果表 + 可视化 + Real3D-AD 抽样 | 第 11-23 天 |
| P6 | 交付归档与答辩冻结 | 报告/PPT/demo + README + release tag | 第 24-30 天 |

每个阶段都有**入口条件（Entry）/ 操作步骤（Steps）/ 验收标准（DoD, Definition of Done）**三段式。未达 DoD 不进入下一阶段。

### 外部依据核验

本 SOP 的 P4-P6 扩展按 2026-06-08 核验的一手资料和本项目实测记录制定。外部资料只作为阶段设计依据，具体命令、路径和指标以本仓库执行记录为准。

- PASDF：Position-Aware Signed Distance Fields，官方论文与仓库说明其核心是 pose alignment、continuous SDF、repair、官方权重和预处理 SDF 资产；用于 P3/P4 的 baseline、registration 诊断和 SDF 残差扩展。
- PO3AD：CVPR 2025 官方论文与仓库，预测点偏移并使用法向引导伪异常；用于 P4/P5 的强判别式对照和法向残差设计参考。
- Anomaly-ShapeNet：CVPR 2024 官方论文/benchmark；用于 P2/P3/P5 的 40 类主协议、对象级与点级指标口径。
- Real3D-AD：NeurIPS 2023 数据集与官方仓库；用于 P5/P6 的真实点云泛化验证。
- CASL 与 MiniShift/Simple3D：曲率提示、高分辨率和微小缺陷相关论文；用于 P4/P5 的多尺度曲率、采样敏感性和压力测试设计。
- PointAD：零样本 3D 点云异常检测仓库；只作为进度富余时的定性扩展，不进入最低交付门槛。

核验入口：

- PASDF paper: `https://arxiv.org/abs/2505.24431`
- PASDF code: `https://github.com/ZZZBBBZZZ/PASDF`
- PO3AD paper: `https://openaccess.thecvf.com/content/CVPR2025/html/Ye_PO3AD_Predicting_Point_Offsets_toward_Better_3D_Point_Cloud_Anomaly_CVPR_2025_paper.html`
- PO3AD code: `https://github.com/yjnanan/PO3AD`
- Anomaly-ShapeNet paper: `https://openaccess.thecvf.com/content/CVPR2024/html/Li_Towards_Scalable_3D_Anomaly_Detection_and_Localization_A_Benchmark_via_CVPR_2024_paper.html`
- Real3D-AD code: `https://github.com/M-3LAB/Real3D-AD`
- CASL paper: `https://arxiv.org/abs/2511.12909`
- MiniShift/Simple3D paper: `https://arxiv.org/abs/2507.07435`
- PointAD code: `https://github.com/zqhang/PointAD`

---

## 1. Codebase 目录架构

仓库名建议：`pcd-anomaly-detection`。采用 `src-layout`（可 pip 安装的包），把第三方 repo 作为受控依赖，而非把我们的代码塞进它们的目录。

```
pcd-anomaly-detection/
├── README.md                  # 项目简介、快速开始、结果表
├── pyproject.toml             # 包元数据 + 依赖 + 工具配置(ruff/black/pytest)
├── environment.yml            # conda 环境(锁定版本)
├── requirements-lock.txt      # pip freeze 锁文件(精确复现)
├── .gitignore                 # 见 §9.5
├── .gitattributes             # LFS 规则(大文件)
├── .pre-commit-config.yaml    # 提交前自动检查
├── LICENSE
├── Makefile                   # 常用命令封装(make setup/test/lint/train)
│
├── .github/
│   ├── workflows/ci.yml       # CI: lint + 单测
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/
│
├── configs/                   # 所有实验配置(YAML), 唯一可信来源
│   ├── base.yaml              # 公共默认值
│   ├── data/                  # 数据集配置(anomaly_shapenet.yaml, real3d.yaml)
│   ├── model/                 # 模型/方法配置(pasdf.yaml, po3ad.yaml)
│   └── experiment/            # 完整实验配置(组合 data+model+ablation)
│       ├── E1_pasdf_baseline.yaml
│       ├── A2_pasdf_normal.yaml
│       └── ...
│
├── src/pcdad/                 # 我们的代码包(import pcdad)
│   ├── __init__.py
│   ├── data/                  # 数据加载与预处理
│   │   ├── dataset.py         # AnomalyShapeNet / Real3D Dataset 类
│   │   ├── preprocess.py      # 归一化/采样/法向估计
│   │   └── transforms.py
│   ├── geometry/              # 几何算子(本项目核心贡献)
│   │   ├── normals.py         # 法向估计与法向残差
│   │   ├── curvature.py       # 多尺度曲率
│   │   └── alignment.py       # 位姿对齐封装(调用 open3d RANSAC+ICP)
│   ├── scoring/               # 异常评分
│   │   ├── sdf_residual.py    # PASDF SDF 残差
│   │   ├── geometric.py       # 法向/曲率残差打分
│   │   └── aggregate.py       # 多尺度 top-k + 局部一致性
│   ├── models/                # 模型适配层(包装第三方 backbone)
│   │   └── pasdf_adapter.py
│   ├── metrics/               # 指标(O-AUROC/P-AUROC/AUPR/PRO)
│   │   └── auroc.py
│   ├── viz/                   # 可视化(heatmap/GT overlay/mesh)
│   │   └── heatmap.py
│   └── utils/                 # 通用工具(日志/随机种子/IO/计时)
│       ├── seed.py
│       ├── logging.py
│       └── io.py
│
├── scripts/                   # 命令行入口(薄封装, 只调 src/)
│   ├── prepare_data.py        # 数据标准化 + 统计报告
│   ├── train.py               # 训练入口
│   ├── evaluate.py            # 评估入口
│   └── visualize.py           # 批量出图
│
├── third_party/               # 第三方 repo(git submodule, 不改其内部)
│   ├── PASDF/                 # submodule -> ZZZBBBZZZ/PASDF
│   └── PO3AD/                 # submodule -> yjnanan/PO3AD
│
├── tests/                     # 单元测试(pytest), 镜像 src 结构
│   ├── test_geometry.py
│   ├── test_scoring.py
│   └── test_metrics.py
│
├── notebooks/                 # 探索性分析(不进生产流程, 提交前清输出)
│   └── 01_data_eda.ipynb
│
├── docs/                      # 文档(本 SOP、plan、方法图)
│
├── experiments/               # 实验产物(git-ignored, 仅留结构说明)
│   └── README.md              # 说明命名规范: {expid}_{date}_{shorthash}/
│
└── data/                      # 数据(git-ignored, 用 LFS 或软链到服务器)
    └── README.md              # 说明数据放置方式与下载链接
```

**架构原则：**
- `src/pcdad/` 是唯一的逻辑实现处；`scripts/` 只做参数解析 + 调用，不写业务逻辑。
- 第三方 repo 用 **git submodule** 钉死 commit，**绝不直接改其源码**；需要改动通过 `models/*_adapter.py` 适配层包装，或在 fork 上以 patch 管理。
- 配置与代码分离：超参只在 `configs/`，代码里不出现魔法数字。
- 数据、checkpoint、日志全部 git-ignored，靠配置 + 锁文件 + 链接复现。

---

## 2. P0 — 仓库与协作基建（第 1 天，由 E 负责）

### Entry
- 已有一个团队 GitHub 组织或共享仓库权限。

### Steps
1. 创建私有仓库 `pcd-anomaly-detection`，初始化 `main` 分支并设为**保护分支**（禁止直接 push，必须 PR + 1 人 review + CI 通过）。
2. 放入基建文件：`pyproject.toml`、`.gitignore`、`.pre-commit-config.yaml`、`Makefile`、`LICENSE`、PR/Issue 模板、`.github/workflows/ci.yml`。
3. 启用 **Git LFS**，`.gitattributes` 跟踪 `*.pth *.pt *.npy *.ply *.pcd` 等（注意：大数据集仍走服务器软链，不进 LFS，只有必须版本化的小权重/样例进 LFS）。
4. 配置 GitHub Projects 看板（列：Backlog / Doing / Review / Done），把 Plan 的实验编号 E0-E7、消融 A0-A6 建成 Issue。
5. 全员克隆并 `make setup` 验证基建可用。

### DoD
- 任意成员能 clone → `make setup` → `make test` 全绿。
- `main` 受保护，PR 模板与 CI 生效（提一个空 PR 验证 CI 触发）。

---

## 3. P1 — 环境搭建（第 1-2 天，由 C 负责）

### Entry
- Linux 服务器 SSH 可用，CUDA 驱动就绪（`nvidia-smi` 正常）。

### Steps（PASDF 主力环境）
1. 严格按官方依赖建环境（已核实）：
   ```bash
   conda create -n pasdf python=3.10 -y
   conda activate pasdf
   # PyTorch 1.11.0 + CUDA 11.3
   conda install pytorch==1.11.0 torchvision==0.12.0 cudatoolkit=11.3 -c pytorch -y
   conda install pytorch3d==0.7.4 -c pytorch3d -y
   # 其余: point-cloud-utils, trimesh, scikit-image, open3d, tensorboard ...
   ```
2. 用 git submodule 拉 PASDF，按其 `install.sh` / `environment_linux.yaml` 补齐，跑通 `Test/AD_test.py --config ...` 的 import。
3. 导出锁文件：`conda env export > environment.yml` 与 `pip freeze > requirements-lock.txt`，提交入库。
4. PO3AD 单独建 `po3ad` 环境（py3.8 / torch1.9 / cu11.1 + MinkowskiEngine）；MinkowskiEngine 装不上则记录失败日志，转用论文报告值，**不阻塞主力**。

### DoD
- `conda activate pasdf && python -c "import torch, pytorch3d, open3d"` 无报错。
- 锁文件入库；另一名成员能据此在第二台机器重建同一环境。

---

## 4. P2 — 数据准备（第 1-4 天，由 B 负责）

### Entry
- P1 环境可用。

### Steps
1. 下载 Anomaly-ShapeNet（HF / 百度网盘 `case`）与 PASDF 官方预处理 SDF 样本 + 权重（Google Drive，用 local-web-fetch 或在服务器 `gdown`）。
2. **核实数据真实情况**（关键，对应 plan §3.1 待定项）：运行 `scripts/prepare_data.py --stat`，统计每类样本数、点数分布(min/mean/max)、异常占比，产出 `experiments/data_stats.md`。比对课程任务书的 17422~157824 点是否成立，确定是否为高密度版。
3. 标准化为统一目录与坐标：归一化到单位球/[-1,1]，记录归一化参数；按 PASDF 要求准备 16384 点版本，同时保留原始点数版本用于压力分析。
4. 实现 `src/pcdad/data/dataset.py`：返回 `(points, normals, gt_point_labels, meta)`；写 `tests/test_dataset.py` 验证形状/类型/标签范围。
5. 固化官方评估协议（40 类划分、指标脚本来源），写入 `configs/data/anomaly_shapenet.yaml`。

### DoD
- `data_stats.md` 产出，点数口径有结论。
- DataLoader 单测通过；随机抽 1 类可视化点云+法向+GT 正常。

---

## 5. P3 — PASDF 复现（第 3-10 天，由 C 负责）

### Entry
- P1、P2 完成。

### Steps
1. **先评估、不训练**：下载官方权重 + 预处理 SDF，按 README 跳过 Step1/2，直接 `Test/AD_test.py` 跑 1-2 类，确认能复现接近论文值。
2. 用我们的 `src/pcdad/metrics/` 重新计算 O-AUROC/P-AUROC，与官方脚本对齐（误差 <0.5% 视为口径一致），**记录指标口径来源**。
3. 扩展到 40 类，产出基线结果表 `experiments/E1_pasdf_baseline/results.csv`。
4. 逐类对照论文表，标注差异类别并分析原因（voxel_size、对齐失败等）。
5. （可选）跑通官方训练流程 Step1/2，验证可重训。

### DoD
- 40 类 PASDF 复现 mean O-AUROC 与论文(90.0)差距可解释（一般 ±2%）。
- 结果表、命令、配置、日志路径和关键结论全部可追溯：轻量 summary/CSV 进入 git 或 `docs/document/stage_record/`，大日志、权重、数据和可视化原图保留服务器路径与 hash，不直接进入 git。

---

## 6. P4 — 失败分析与几何增强开发（第 11-17 天，由 D 主责，B/C/E 协作）

P4 的目标不是盲目叠模块，而是先解释 PASDF 在哪些类、哪些异常类型、哪些配准场景下失败，再以最小可测接口加入法向、曲率和聚合增强。依据来自 Plan §6.3-§6.5、P3 stage record，以及当前学术资料：

- PASDF 论文和官方仓库强调 pose alignment、continuous SDF、repair、`voxel_size` 与 registration 精度；官方 README 说明有预处理 SDF 和权重时可跳过训练直接评估。
- PO3AD 论文指出点偏移预测和法向引导伪异常能让模型关注伪异常点，是法向残差/伪异常扩展的主要参考。
- CASL 论文指出曲率本身就是强异常信号，多尺度曲率提示对 3D AD 有价值。
- MiniShift/Simple3D 论文强调高分辨率、微小缺陷和多尺度局部聚合，支撑后续压力测试和高密度点云策略。

### Entry
- P3 完成，且有 40 类 PASDF baseline 结果。
- 当前 P3 baseline 的低分类别、日志 warning、生成 YAML、运行命令已记录。
- `src/pcdad/models/pasdf_adapter.py` 与 `scripts/evaluate.py` 可稳定生成 PASDF 官方评估配置并解析结果。
- P2 固定 16,384 点数据 manifest 可读，原始高密度数据仍保留。

### Steps
1. **固化 P3 轻量 artifact 策略**：
   - 新增或更新 `docs/document/stage_record/` 下的结果记录。
   - 明确哪些进入 git：结果摘要、轻量 CSV、配置快照、日志 excerpt、低分类别列表。
   - 明确哪些不进入 git：数据集、权重、完整 run.log、大图、mesh、大量 per-sample 输出。
2. **建立失败分析入口**：
   - 新增 `scripts/analyze_pasdf_failures.py` 或等价 notebook-free 脚本，只调 `src/pcdad/`。
   - 输入：`experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv`、PASDF `run.log`、数据 manifest。
   - 输出：per-class summary、Open3D warning 统计、低分候选类别、后续可视化任务列表。
3. **优先分析 P3 低分类别**：
   - object AUROC 低于 0.8 的类别：`cap3`、`cap4`、`cap5`、`helmet2`、`microphone0`、`shelf0`、`tap1`。
   - pixel AUROC 低于 0.85 的类别：`bowl2`、`cap3`、`headset1`、`helmet0`、`helmet1`、`helmet2`、`vase1`。
   - 特别区分 `helmet1` 这类“点级低、对象级高”的定位失败，与 `cap3` 这类“对象级也低”的检测失败。
4. **配准质量诊断**：
   - 从 PASDF 日志中提取 Open3D “Too few correspondences” warning 的类别和样本上下文。
   - 对低分类别生成对齐前后 overlay 图、Chamfer/nearest-neighbor 距离摘要、template 匹配摘要。
   - 做 `voxel_size` 小网格扫描，至少覆盖 `0.02, 0.03, 0.04, 0.05`，优先跑 `cap3/cap4/cap5/helmet2/tap1`。
5. **实现几何算子模块**：
   - `src/pcdad/geometry/normals.py`：kNN/PCA 法向估计、法向方向一致性处理、法向夹角残差。
   - `src/pcdad/geometry/curvature.py`：多尺度 PCA 曲率，默认 k=`16,32,64`。
   - `src/pcdad/scoring/aggregate.py`：top-k pooling、percentile pooling、局部一致性平滑。
   - `src/pcdad/scoring/geometric.py`：把 SDF 残差、法向残差、曲率残差组合成点级分数。
6. **TDD 覆盖核心算子**：
   - 法向：平面点云法向稳定、单点/空点云报错清晰。
   - 曲率：平面曲率接近 0，球面/弯曲面曲率高于平面，k 大于点数时行为明确。
   - 聚合：top-k 比例、空输入、全相等分数、异常点比例极低时结果可解释。
7. **配置开关化**：
   - 新增 `configs/experiment/A2_pasdf_normal.yaml`、`A3_pasdf_curvature.yaml`、`A4_pasdf_geom_full.yaml`。
   - 所有权重和 k 值写入 YAML，不在代码里硬编码。
   - 保持 A1 PASDF baseline 配置不变，新增增强配置只叠加差异项。
8. **1 类增强 smoke**：
   - 先在 `ashtray0` 或一个低分类别上生成增强 heatmap。
   - 输出 GT overlay、top-k 对象分数、点级分数直方图。
   - 记录增强前后指标是否一致可复算，即使指标无提升也要保留失败解释。

### DoD
- P3 低分类别和 Open3D warning 有结构化分析记录。
- `geometry/` 与 `scoring/` 新增模块有单测，`ruff/black/mypy/pytest/pre-commit` 通过。
- A2/A3/A4 配置可 dry-run，至少 1 类能产出增强 heatmap 和指标摘要。
- 所有新增实验都能通过 `configs/experiment/*.yaml` 复现；没有魔法数字散落在脚本中。
- 若增强没有带来提升，必须产出负结果解释：配准失败、SDF 已足够强、曲率对该类不敏感、采样损失或分数融合不合理。

### 进度快于预期时的扩展门
- 打通 PO3AD 环境和官方 checkpoint 评估，作为 A0 强判别式对照；若 MinkowskiEngine 阻塞超过半天，只记录失败日志并转用论文报告值。
- 尝试从 PASDF 中导出 per-sample 点级 score，避免只依赖官方 CSV 做类别级分析。
- 对原始高密度点云做 16,384 / 32,768 / 65,536 采样点数压力测试，记录细小缺陷是否被下采样抹掉。

---

## 7. P5 — 实验消融与跨数据集验证（第 11-23 天，由 D/C 主责，B/E 协作）

P5 的目标是把 P4 的模块和分析转化为可信实验矩阵。执行顺序必须是“代表类别小跑 → 固定超参 → 40 类全量 → 跨数据集抽样”，避免直接在 40 类上反复试参导致结果不可解释。

### Entry
- P4 至少完成 A2/A3/A4 的 1 类 smoke。
- A1 PASDF baseline 的 40 类结果可复算。
- 代表类别选择、超参数候选、输出目录命名已写入 stage record 或实验计划。

### Steps
1. **锁定实验矩阵**：
   - A1：PASDF baseline（已完成，作为固定对照）。
   - A2：PASDF + 法向残差。
   - A3：PASDF + 法向残差 + 多尺度曲率残差。
   - A4：PASDF + 法向残差 + 曲率残差 + top-k/局部一致性聚合。
   - A5：关闭或弱化 PAM 的消融，用于量化位姿对齐贡献。
   - A6：A4 在 Real3D-AD 选定类别上的泛化验证。
2. **选择代表类别小跑**：
   - 必选低分类别：`cap3`、`helmet2`、`tap1`。
   - 必选高分稳定类别：`ashtray0` 或 `bottle0`。
   - 必选点级低但对象级高类别：`helmet1` 或 `vase1`。
   - 小跑阶段只允许比较 2-3 组超参，选定后冻结。
3. **统一指标口径**：
   - 对象级：O-AUROC、O-AUPR，按类别 mean。
   - 点级：P-AUROC、P-AUPR，必要时补 PRO 或官方点级口径。
   - 文献值单独列为 “reported”，自跑值列为 “ours”；禁止混列。
   - 若官方脚本和本项目 `src/pcdad/metrics/` 有差异，记录差异和误差。
4. **扩展到 Anomaly-ShapeNet 40 类**：
   - 先跑 A2/A3/A4 全量，输出 `results.csv`、`summary.json`、`run.log`。
   - 每个实验输出 per-class 表、mean 表、低分类别表。
   - 记录每类耗时、显存峰值、输入点数。
5. **执行 A5 位姿对齐消融**：
   - 若 PASDF 官方代码不支持直接关闭 PAM，则通过配置、patch adapter 或替代对齐质量分组实现弱化对照。
   - 必须明确 A5 是“严格关闭 PAM”还是“对齐质量分组分析”，不能混用。
6. **Real3D-AD 抽样验证**：
   - 优先选 2-4 类，覆盖不同点数、透明/非透明、复杂几何。
   - 推荐首批：`airplane`、`car`、`duck`、`shell` 或按下载完成情况调整。
   - 使用 voxel downsample/FPS，记录原始点数、采样点数、推理时间和显存。
7. **可视化与失败案例**：
   - 每个主配置至少输出 3 个成功案例和 3 个失败案例。
   - 必须包含 heatmap、GT overlay、分数直方图、对齐前后 overlay。
   - 失败原因按类别、异常类型、配准、采样、曲率/法向混淆、shape prior 过强分类。
8. **结果归档**：
   - 轻量结果表进入 git 或 `docs/document/stage_record/`。
   - 大型日志、图片、mesh 保留服务器路径、文件大小、hash、生成命令。
   - 每次实验写入 `experiments/{expid}_{date}_{githash}/README.md` 或等价记录。

### DoD
- A1-A4 至少完成 Anomaly-ShapeNet 40 类结果；A5 有明确的对齐贡献分析或阻塞记录。
- 至少 2 个 Real3D-AD 类别完成推理和可视化，若下载或环境阻塞，必须有失败日志和替代分析。
- 消融表、per-class 表、失败案例图、速度/显存表齐全。
- 能回答三个研究问题：增强是否有收益、收益来自哪些类别/异常类型、失败主要来自配准/采样/几何混淆还是底座限制。

### 进度快于预期时的扩展门
- 完成 PO3AD A0 自跑对照，至少覆盖 Anomaly-ShapeNet 3-5 个代表类别；若稳定，再扩 40 类。
- MiniShift 或 MVTec 3D-AD 子集压力测试：只要求定性或小表，不纳入最低交付。
- 增加零样本定性对照：PointAD 或点云-图像/语言方法，只做可视化比较，不作为主指标。
- 对高密度原始点云做采样敏感性曲线：16k、32k、65k 与耗时/指标关系。

---

## 8. P6 — 交付归档与答辩冻结（第 24-30 天，由 A/E 主责，全员协作）

P6 的目标是把研究和工程结果冻结成可答辩、可复查、可复现的交付物。P6 不再引入影响主结论的新方法；只允许补文档、补图、补表、修复复现脚本和修正明显错误。

### Entry
- P5 主实验矩阵已完成，或有明确记录说明哪些扩展项因时间/环境被降级。
- 最终采用的主表、消融表、失败案例和可视化清单已确定。
- `main` 分支没有未解释的红灯测试或未提交关键代码。

### Steps
1. **冻结结果表**：
   - `README.md` 写入核心结果摘要、运行环境、复现入口。
   - `docs/document/stage_record/` 写入最终实验记录：A1-A6 状态、指标表、失败案例索引、服务器 artifact 路径。
   - 文献报告值和自跑值分列。
2. **整理报告结构**：
   - 背景与任务定义：Anomaly-ShapeNet、Real3D-AD、点级/对象级指标。
   - 方法：PASDF baseline、PAM 质量分析、法向/曲率/聚合增强。
   - 实验：A1-A6、Real3D-AD、速度/显存、失败分析。
   - 讨论：高密度点云、采样损失、配准失败、真实泛化、局限和未来工作。
3. **制作 PPT 与 demo**：
   - 必须包含一页方法图、一页实验矩阵、一页主结果表、一页消融、一页失败案例。
   - demo 优先展示点级 heatmap、GT overlay、SDF repair mesh 或对齐前后可视化。
   - 所有图必须能追溯到生成命令和输入 artifact。
4. **复现脚本审查**：
   - 从干净 shell 执行 README 的最小复现路径。
   - 验证 `make lint`、`make test`、关键 `scripts/evaluate.py --dry-run`。
   - 记录 Docker 容器、conda env、PASDF submodule commit、数据目录和权重目录。
5. **仓库清理**：
   - 删除临时 debug 文件、空目录、无用 notebook 输出、误提交缓存。
   - 确认 `.gitignore` 没有挡住应入库的轻量结果，也没有放进大文件。
   - 确认 `git status --ignored --short` 中大文件均为预期忽略。
6. **冻结 release**：
   - 打 tag：`v0.1-pasdf-baseline` 或 `v1.0-course-delivery`，按实际交付状态命名。
   - release notes 写清楚可复现范围、已知限制、未入库 artifact 路径。
   - 若不适合公开数据/权重，README 明确下载和本地放置方式。

### DoD
- 他人按 README 能在同类 Docker/conda 环境中跑通最小评估或 dry-run。
- 报告、PPT、结果表、失败案例图、复现实验命令齐全且互相一致。
- `main` 分支质量门通过；最终 tag 或 commit hash 被写入报告。
- 所有不可入库 artifact 都有服务器路径、大小、hash 或生成命令。

### 进度快于预期时的扩展门
- 增加一个可交互或批处理 demo：输入类别和样本 ID，输出 heatmap、GT overlay、对象分数和主要失败诊断。
- 补充 Real3D-AD 更多类别或 MiniShift/MVTec 子集，作为附录而非主结论。
- 增加一页“工业部署讨论”：采样密度、实时性、内存、配准失败回退、传感器边界。

---

## 9. 代码工作流规范（贯穿全程，强制）

### 9.1 分支模型（轻量 GitHub Flow）
- `main`：始终可运行、CI 绿。受保护。
- 功能分支：`feat/<scope>-<desc>`、`fix/<...>`、`exp/<expid>-<...>`、`docs/<...>`。
- 一切改动经 PR 合入 `main`；**至少 1 人 review + CI 通过**才可 merge；用 squash merge 保持历史干净。

### 9.2 Docker 与 Git 操作边界
- Docker 容器用于环境隔离、依赖安装、训练、评估、测试与 lint，避免污染宿主机 Python/CUDA 环境。
- 代码仓库仍以宿主机工作目录为准；容器通过挂载访问同一目录，不在容器内另 clone 一份仓库。
- **push/pull/fetch 等需要 GitHub 凭据的操作优先在宿主机终端执行**，不要在 Docker 容器内处理 GitHub 登录或 token。宿主机终端已配置凭据时，直接运行 `git push -u origin main` 或后续分支 push。
- 容器内可以执行只依赖本地仓库状态的 Git 命令，例如 `git status`、`git diff`、`git log`，用于调试和记录实验 git hash。

### 9.3 提交规范（Conventional Commits）
- 格式：`<type>(<scope>): <subject>`，type ∈ `feat|fix|refactor|test|docs|chore|exp`。
- 例：`feat(geometry): add multi-scale curvature residual`。
- 主题用祈使句、≤50 字符；正文说明 why。提交粒度小而自洽，一个提交只做一件事。

### 9.4 Pull Request 规范
- 用 PR 模板：变更动机、做法、测试方式、影响范围、关联 Issue/实验号、自检清单。
- PR 必须：通过 CI（lint+test）、附必要截图/指标、勾选自检清单。
- Review 关注：正确性 > 可读性 > 复用 > 简洁。Reviewer 至少留一条实质意见或明确 Approve。

### 9.5 .gitignore 要点
- 忽略：`data/`、`experiments/`、`*.pth/*.pt`(除受控)、`__pycache__`、`.ipynb_checkpoints`、`wandb/`、本地 `.env`。
- 永不提交：数据集、大权重、含绝对路径的本地配置、密钥。

### 9.6 实验可复现铁律
- 每个实验 = 一个 `configs/experiment/*.yaml` + 一次运行目录 `experiments/{expid}_{date}_{githash}/`。
- 运行前固定随机种子（`utils/seed.py` 统一设置 numpy/torch/random + `cudnn.deterministic`）。
- 运行目录必存：完整 config 快照、git commit hash、环境锁文件、stdout 日志、指标 csv、关键可视化。
- 实验追踪用 TensorBoard 或 SwanLab/W&B（任选其一并统一）。
- 结果表只记录"自跑值"，文献值单列且标"论文报告"，**严禁混列**（呼应 plan 风险表）。

---

## 10. 代码质量：模块化、规范性、简洁性审查

### 10.1 模块化要求
- **单一职责**：一个函数只做一件事；一个模块聚焦一个关注点（几何/评分/指标分离）。
- **依赖方向**：`scripts → src/pcdad → (utils/geometry/...)`，禁止反向依赖与循环 import。
- **第三方隔离**：所有对 PASDF/PO3AD 的调用收敛到 `models/*_adapter.py`，上层只依赖我们的接口，便于替换 backbone。
- **配置驱动**：新增能力优先通过 config 开关，而非复制代码分支。
- 函数建议 ≤50 行、文件 ≤400 行、圈复杂度可控；超限即拆分。

### 10.2 规范性（自动化，非人肉）
- **格式化**：`black`（行宽 100）。**Lint**：`ruff`（含 isort 规则）。**类型**：关键接口加 type hints，`mypy` 对 `src/pcdad` 做基础检查。
- 全部通过 `pre-commit` 在提交时自动执行：black、ruff、ruff-format、trailing-whitespace、end-of-file、check-yaml、检测大文件、清空 notebook 输出（nbstripout）。
- 命名：模块/函数/变量 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE`；名字表意，禁止 `a/tmp/data2` 这类无意义命名。
- 文档：公共函数/类写 docstring（Google 风格：Args/Returns/Raises）。

### 10.3 简洁性检查（每次 PR 自检 + Review 把关）
- 删除死代码、注释掉的旧代码、调试 print（用 logging）。
- 不过早抽象，也不复制粘贴：第 2 次出现就抽函数，第 3 次出现必抽。
- 优先用成熟库（open3d 做配准/法向、scikit-learn 做 AUROC），不重复造轮子。
- 复杂逻辑写成"读起来像散文"：好命名 + 早返回 + 减嵌套，胜过长注释。
- 每个 PR 问三句：这段能更短吗？能复用已有的吗？这个抽象现在真的需要吗？

### 10.4 测试要求
- `src/pcdad` 核心算子（geometry/scoring/metrics）必须有单测，覆盖正常+边界（空点云、单点、全异常）。
- 指标实现用小型合成数据对拍 sklearn，确保数值正确。
- CI 在每个 PR 跑 `pytest`；测试失败禁止 merge。
- 测试要快（核心单测秒级），不依赖真实数据集（用 fixture 造小样本）。

---

## 11. 团队协作日常

- **每日站会同步**（异步亦可，写在看板）：昨日完成 / 今日计划 / 阻塞项。
- 实验状态进 GitHub Projects 看板，与实验号一一对应。
- 阻塞 >半天必须在群里 escalate，不要独自硬扛。
- 代码归属：人人可读全仓，但模块有 owner（见 plan §9 分工 A-E）。
- 每周一次集成检查：`main` 能否一键复现至少一个核心实验。

---

## 12. 快速命令速查（Makefile 封装）

```bash
make setup     # 建环境 + 装 pre-commit + 拉 submodule
make lint      # ruff + black --check + mypy
make format    # black + ruff --fix
make test      # pytest
make data      # python scripts/prepare_data.py --stat
make eval CFG=configs/experiment/E1_pasdf_baseline.yaml
make train CFG=configs/experiment/A2_pasdf_normal.yaml
```

---

## 附：第 1 天 checklist（照做即可启动）

- [ ] E：建 GitHub 仓库 + 保护 main + 基建文件 + CI + 看板
- [ ] C：服务器建 `pasdf` 环境，导出锁文件
- [ ] B：启动数据下载（数据集 + PASDF 权重/SDF 样本）
- [ ] B：跑 `prepare_data.py --stat`，核实点数口径
- [ ] D：法向/曲率/距离小脚本 + 可视化
- [ ] A：核心论文引用表 + 报告骨架
- [ ] 全员：clone → `make setup` → `make test` 绿
