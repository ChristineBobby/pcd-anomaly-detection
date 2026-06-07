# 3D 点云缺陷检测项目 · 生产级工程 SOP

文档定位：本文件是《3d_point_cloud_defect_detection_research_plan.md》的**可执行落地手册**。Plan 回答"做什么/为什么"，本 SOP 回答"怎么做、按什么规范做"。
适用对象：5 人团队，远程 Linux 服务器（4×RTX 4090 48G），本地 Windows 仅开发/文档。
约束等级：**生产级**。所有代码、提交、实验都按下述规范执行，不走"能跑就行"的捷径。

---

<!-- TOC START -->
## 目录

- [0. 总览：从零到答辩的 7 个阶段](#0-总览从零到答辩的-7-个阶段)
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
- [6. 代码工作流规范（贯穿全程，强制）](#6-代码工作流规范贯穿全程强制)
  - [6.1 分支模型（轻量 GitHub Flow）](#61-分支模型轻量-github-flow)
  - [6.2 提交规范（Conventional Commits）](#62-提交规范conventional-commits)
  - [6.3 Pull Request 规范](#63-pull-request-规范)
  - [6.4 .gitignore 要点](#64-gitignore-要点)
  - [6.5 实验可复现铁律](#65-实验可复现铁律)
- [7. 代码质量：模块化、规范性、简洁性审查](#7-代码质量模块化规范性简洁性审查)
  - [7.1 模块化要求](#71-模块化要求)
  - [7.2 规范性（自动化，非人肉）](#72-规范性自动化非人肉)
  - [7.3 简洁性检查（每次 PR 自检 + Review 把关）](#73-简洁性检查每次-pr-自检--review-把关)
  - [7.4 测试要求](#74-测试要求)
- [8. P4-P6 阶段要点（简表）](#8-p4-p6-阶段要点简表)
- [9. 团队协作日常](#9-团队协作日常)
- [10. 快速命令速查（Makefile 封装）](#10-快速命令速查makefile-封装)
- [附：第 1 天 checklist（照做即可启动）](#附第-1-天-checklist照做即可启动)
<!-- TOC END -->

## 0. 总览：从零到答辩的 7 个阶段

| 阶段 | 名称 | 核心产出 | 对应 Plan 排期 |
|---|---|---|---|
| P0 | 仓库与协作基建 | GitHub 仓库 + CI + 规范文件 | 第 1 天 |
| P1 | 环境搭建 | 可复现的 conda 环境 + 依赖锁 | 第 1-2 天 |
| P2 | 数据准备 | 标准化数据集 + 统计报告 + DataLoader | 第 1-4 天 |
| P3 | PASDF 复现 | 官方权重评估复现 SOTA | 第 3-10 天 |
| P4 | 几何增强开发 | 法向/曲率/聚合模块 + 单测 | 第 11-17 天 |
| P5 | 实验与消融 | 全量结果表 + 可视化 | 第 11-23 天 |
| P6 | 交付归档 | 报告/PPT/demo + release tag | 第 24-30 天 |

每个阶段都有**入口条件（Entry）/ 操作步骤（Steps）/ 验收标准（DoD, Definition of Done）**三段式。未达 DoD 不进入下一阶段。

---

## 1. Codebase 目录架构

仓库名建议：`pcd-anomaly-detection`。采用 `src-layout`（可 pip 安装的包），把第三方 repo 作为受控依赖，而非把我们的代码塞进它们的目录。

```
pcd-anomaly-detection/
├── README.md                  # 项目简介、快速开始、结果表
├── pyproject.toml             # 包元数据 + 依赖 + 工具配置(ruff/black/pytest)
├── environment.yml            # conda 环境(锁定版本)
├── requirements-lock.txt      # pip freeze 锁文件(精确复现)
├── .gitignore                 # 见 §6.4
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
- 结果表、命令、配置、日志全部入库（结果表进 git，权重/日志进服务器+LFS）。

---

## 6. 代码工作流规范（贯穿全程，强制）

### 6.1 分支模型（轻量 GitHub Flow）
- `main`：始终可运行、CI 绿。受保护。
- 功能分支：`feat/<scope>-<desc>`、`fix/<...>`、`exp/<expid>-<...>`、`docs/<...>`。
- 一切改动经 PR 合入 `main`；**至少 1 人 review + CI 通过**才可 merge；用 squash merge 保持历史干净。

### 6.2 Docker 与 Git 操作边界
- Docker 容器用于环境隔离、依赖安装、训练、评估、测试与 lint，避免污染宿主机 Python/CUDA 环境。
- 代码仓库仍以宿主机工作目录为准；容器通过挂载访问同一目录，不在容器内另 clone 一份仓库。
- **push/pull/fetch 等需要 GitHub 凭据的操作优先在宿主机终端执行**，不要在 Docker 容器内处理 GitHub 登录或 token。宿主机终端已配置凭据时，直接运行 `git push -u origin main` 或后续分支 push。
- 容器内可以执行只依赖本地仓库状态的 Git 命令，例如 `git status`、`git diff`、`git log`，用于调试和记录实验 git hash。

### 6.3 提交规范（Conventional Commits）
- 格式：`<type>(<scope>): <subject>`，type ∈ `feat|fix|refactor|test|docs|chore|exp`。
- 例：`feat(geometry): add multi-scale curvature residual`。
- 主题用祈使句、≤50 字符；正文说明 why。提交粒度小而自洽，一个提交只做一件事。

### 6.4 Pull Request 规范
- 用 PR 模板：变更动机、做法、测试方式、影响范围、关联 Issue/实验号、自检清单。
- PR 必须：通过 CI（lint+test）、附必要截图/指标、勾选自检清单。
- Review 关注：正确性 > 可读性 > 复用 > 简洁。Reviewer 至少留一条实质意见或明确 Approve。

### 6.5 .gitignore 要点
- 忽略：`data/`、`experiments/`、`*.pth/*.pt`(除受控)、`__pycache__`、`.ipynb_checkpoints`、`wandb/`、本地 `.env`。
- 永不提交：数据集、大权重、含绝对路径的本地配置、密钥。

### 6.6 实验可复现铁律
- 每个实验 = 一个 `configs/experiment/*.yaml` + 一次运行目录 `experiments/{expid}_{date}_{githash}/`。
- 运行前固定随机种子（`utils/seed.py` 统一设置 numpy/torch/random + `cudnn.deterministic`）。
- 运行目录必存：完整 config 快照、git commit hash、环境锁文件、stdout 日志、指标 csv、关键可视化。
- 实验追踪用 TensorBoard 或 SwanLab/W&B（任选其一并统一）。
- 结果表只记录"自跑值"，文献值单列且标"论文报告"，**严禁混列**（呼应 plan 风险表）。

---

## 7. 代码质量：模块化、规范性、简洁性审查

### 7.1 模块化要求
- **单一职责**：一个函数只做一件事；一个模块聚焦一个关注点（几何/评分/指标分离）。
- **依赖方向**：`scripts → src/pcdad → (utils/geometry/...)`，禁止反向依赖与循环 import。
- **第三方隔离**：所有对 PASDF/PO3AD 的调用收敛到 `models/*_adapter.py`，上层只依赖我们的接口，便于替换 backbone。
- **配置驱动**：新增能力优先通过 config 开关，而非复制代码分支。
- 函数建议 ≤50 行、文件 ≤400 行、圈复杂度可控；超限即拆分。

### 7.2 规范性（自动化，非人肉）
- **格式化**：`black`（行宽 100）。**Lint**：`ruff`（含 isort 规则）。**类型**：关键接口加 type hints，`mypy` 对 `src/pcdad` 做基础检查。
- 全部通过 `pre-commit` 在提交时自动执行：black、ruff、ruff-format、trailing-whitespace、end-of-file、check-yaml、检测大文件、清空 notebook 输出（nbstripout）。
- 命名：模块/函数/变量 `snake_case`，类 `PascalCase`，常量 `UPPER_SNAKE`；名字表意，禁止 `a/tmp/data2` 这类无意义命名。
- 文档：公共函数/类写 docstring（Google 风格：Args/Returns/Raises）。

### 7.3 简洁性检查（每次 PR 自检 + Review 把关）
- 删除死代码、注释掉的旧代码、调试 print（用 logging）。
- 不过早抽象，也不复制粘贴：第 2 次出现就抽函数，第 3 次出现必抽。
- 优先用成熟库（open3d 做配准/法向、scikit-learn 做 AUROC），不重复造轮子。
- 复杂逻辑写成"读起来像散文"：好命名 + 早返回 + 减嵌套，胜过长注释。
- 每个 PR 问三句：这段能更短吗？能复用已有的吗？这个抽象现在真的需要吗？

### 7.4 测试要求
- `src/pcdad` 核心算子（geometry/scoring/metrics）必须有单测，覆盖正常+边界（空点云、单点、全异常）。
- 指标实现用小型合成数据对拍 sklearn，确保数值正确。
- CI 在每个 PR 跑 `pytest`；测试失败禁止 merge。
- 测试要快（核心单测秒级），不依赖真实数据集（用 fixture 造小样本）。

---

## 8. P4-P6 阶段要点（简表）

| 阶段 | 关键步骤 | DoD |
|---|---|---|
| P4 几何增强 | 在 `geometry/`+`scoring/` 实现法向残差、多尺度曲率残差、top-k+一致性聚合；每个模块配单测；config 开关化 | 模块单测通过；能在 1 类上产出增强后 heatmap |
| P5 实验消融 | 跑 A0-A6（含关闭 PAM 对照）；3-5 类验证趋势→扩 40 类；Real3D-AD 2-4 类泛化 | 全量结果表+消融图+失败案例齐全且可复现 |
| P6 交付归档 | 报告/PPT/demo(含 SDF 修复)；README 填结果表；打 release tag | 他人按 README 能复现核心结果；tag 冻结 |

---

## 9. 团队协作日常

- **每日站会同步**（异步亦可，写在看板）：昨日完成 / 今日计划 / 阻塞项。
- 实验状态进 GitHub Projects 看板，与实验号一一对应。
- 阻塞 >半天必须在群里 escalate，不要独自硬扛。
- 代码归属：人人可读全仓，但模块有 owner（见 plan §9 分工 A-E）。
- 每周一次集成检查：`main` 能否一键复现至少一个核心实验。

---

## 10. 快速命令速查（Makefile 封装）

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
