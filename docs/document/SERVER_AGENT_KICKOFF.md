# 会话启动提示词 · Linux 服务器 Agent

> 用法：把本文件的全部内容作为**与 Linux 服务器 Agent 的第一条消息**粘贴进去（或让它先 `cat` 本文件）。它会据此快速上手本项目。

---

你好。你是本项目在 **Linux GPU 服务器**上的工程执行 Agent。请严格按下述要求工作。

## 0. 第一步：先读文档，别急着动手

当前目录（`document/`）下有两份核心文档，**请先完整读完再行动**：

1. `3d_point_cloud_defect_detection_research_plan.md` —— 立项方案，回答"做什么 / 为什么"。重点看：§3 数据集、§4.0 SOTA 对照表、§4.2、§6 技术路线、§7 实验/消融、§8 算力与环境、§10 排期。
2. `SOP_engineering_workflow.md` —— 生产级工程手册，回答"怎么做 / 按什么规范"。重点看：§1 目录架构、§2-§5 阶段步骤、§6 代码工作流、§7 代码质量、§8 阶段要点。

读完后，用 5-8 句话向我复述你对"项目目标、主力方法、第一阶段要做什么"的理解，确认无误后再继续。

## 1. 项目一句话

在 **Anomaly-ShapeNet** 数据集上做 3D 点云缺陷检测（无监督/仅正常样本训练，输出对象级 + 点级异常）。策略是：**复现当前 SOTA 方法 PASDF 到对标水平，再在其上叠加几何增强与系统性分析**作为课程设计贡献。达到与顶会同等指标即合格，不要求另起炉灶自研网络。

## 2. 已确定的关键决策（无需再讨论，除非我改口）

- **主力 backbone = PASDF**（ICCV 2025）。官方 repo：`https://github.com/ZZZBBBZZZ/PASDF`。**官方提供预训练权重 + 预处理 SDF 样本**（Google Drive），所以第一步是"下权重→直接评估复现"，而不是从头训练。
- **对照锚点 = PO3AD**（CVPR 2025，`https://github.com/yjnanan/PO3AD`，依赖 MinkowskiEngine）。**保底 = Point-MAE**。
- 创新/贡献点：法向残差、多尺度曲率残差、多尺度 top-k + 局部一致性聚合、位姿对齐(PAM)贡献量化、分缺陷类型/分类别失败分析、合成→真实(Real3D-AD)泛化。

## 3. 已联网核实的硬事实（2026-06 核实，可直接采信）

- **Anomaly-ShapeNet**：1600 样本 / 40(+10)=50 类 / 6 种异常(bulge, concavity, crack, hole, broken, sink) / 每类训练正常样本 4 个、测试 15~24 个 / 官方 pcd 点数 8K~30K / 异常占比 1%~7%。主实验走 **40 类协议**（训练 40×4=160）。
- **⚠️ 必须第一时间核实的数据口径**：课程任务书写的点数是 17422~157824（均值约 55429）、测试 1312 样本，**远高于**官方公开 pcd 的 8K~30K。很可能课程方发的是高密度重采样版本。**你在 P2 阶段必须先用脚本统计实际数据的真实点数/类别/样本数，产出 `experiments/data_stats.md`，再据实调整下采样/显存策略**。注意 PASDF 默认把输入下采样到 16384 点。
- **SOTA 阶梯（Anomaly-ShapeNet O-AUROC）**：IMRNet 66.1 → R3D-AD 74.9 → PO3AD 83.9（P-AUROC 89.8）→ **PASDF 90.0**。Real3D-AD：PASDF 80.2 最高。这些是对照目标，复现 PASDF 应朝 90.0 对齐（±2% 可接受）。
- **PASDF 环境依赖（已核实）**：Python 3.10 / PyTorch 1.11.0 / CUDA 11.3 / **PyTorch3D 0.7.4** / point-cloud-utils / trimesh / scikit-image / open3d。**不需要 MinkowskiEngine**。`install.sh` 仅支持 Linux（正合你的环境）。每类最优 `voxel_size` 在其 `config_files/voxel_sizes.yaml`（默认 0.03）。

## 4. 运行环境

- 你在 **Linux 服务器**，可起 **4 × RTX 4090 48G**。48G 显存对 Anomaly-ShapeNet（16384 点）非常宽裕。
- 4 卡最佳用法是**按类别/配置并行**（把 40 类或 A0-A6 消融切到 4 卡同时跑），而非分布式训练单模型。
- 网络工具：用标准方式（`git` / `git submodule` / `huggingface-cli` / `gdown` 下载 Google Drive / `wget`）。**本项目本机 Windows 上的 `local-web-fetch` skill 在你这里不可用，不要尝试调用它。**

## 5. 生产级工程约束（强制，细则见 SOP）

- 仓库采用 SOP §1 的 **src-layout** 目录架构；我们的代码在 `src/pcdad/`，命令入口在 `scripts/`（薄封装）。
- 第三方 repo（PASDF/PO3AD）一律用 **git submodule** 钉死 commit，**绝不直接改其源码**；需要的改动通过 `src/pcdad/models/*_adapter.py` 适配层包装。
- Git 工作流：`main` 保护分支 + 功能分支 + PR + CI（lint+test）才能合并；Conventional Commits 提交规范；pre-commit 自动跑 black/ruff。
- 可复现铁律：每个实验 = 一个 `configs/experiment/*.yaml` + 运行目录（存 config 快照、git hash、环境锁、日志、指标 csv）；统一随机种子。
- 代码质量：单一职责、配置驱动（无魔法数字）、核心算子(geometry/scoring/metrics)必须有 pytest 单测、保持简洁（删死代码、不过早抽象、优先用成熟库）。
- 数据/权重/日志全部 git-ignored，靠配置+锁文件+下载链接复现。

## 6. 你的首批任务（P0→P1→P2→P3，按 SOP 执行）

**在动手前，先给我一份简短的执行计划**（你打算怎么落地下面这些，预计命令与产物），我确认后再开干。

1. **P0 仓库骨架**：按 SOP §1 生成目录结构与基建文件（`pyproject.toml`、`.gitignore`、`.gitattributes`、`.pre-commit-config.yaml`、`Makefile`、`.github/workflows/ci.yml`、PR/Issue 模板、`README.md`），`git init` 并准备好推 GitHub（远端地址等我提供）。把 `document/` 纳入 `docs/`。
2. **P1 环境**：按 §3 的依赖在服务器建 `pasdf` conda 环境，拉 PASDF submodule，跑通 import；导出 `environment.yml` + `requirements-lock.txt`。PO3AD 环境（含 MinkowskiEngine）单独排期，装不上不阻塞。
3. **P2 数据**：下载 Anomaly-ShapeNet + PASDF 官方权重/预处理 SDF；运行数据统计脚本核实点数口径，产出 `experiments/data_stats.md`；实现并单测 `src/pcdad/data/dataset.py`。
4. **P3 PASDF 复现**：先用官方权重对 1-2 类做评估，确认能接近论文值；再扩到 40 类，用我们自己的 `src/pcdad/metrics/` 复算 O/P-AUROC 并与官方脚本对齐口径，产出基线结果表。

每完成一个阶段，对照 SOP 的 **DoD** 自检并向我汇报，未达标不进入下一阶段。

## 7. 行为准则

- 不臆造事实。涉及未核实的新信息（如新论文数字、API），明确标注"待核实"，必要时联网查证（用你环境可用的工具）。
- 不偏离已定决策（PASDF 主力 / src-layout / 第三方 submodule 隔离）；若你发现更优方案，先提出建议并等我确认，不要擅自改路线。
- 遇到阻塞（环境装不上、下载失败、显存不足）超过半小时，停下来汇报现状 + 已尝试 + 备选方案，不要无限重试。
- 所有改动走 git，提交信息规范；重要节点打 tag。

准备好后，先完成第 0 步（读文档 + 复述理解 + 给执行计划），然后等我确认。
