# P7 创新路线调研与方案评估

撰写日期：2026-06-14

文档定位：在 P0-P6 已经完成 PASDF 复现、几何负结果和 bad case closure 后，重新评估项目创新性，并规划下一阶段真正可训练、可消融、可利用 8xRTX 4090 48G 的研究路线。

<!-- TOC START -->
## 目录

- [0. 会话延续建议](#0-会话延续建议)
- [1. 结论先行](#1-结论先行)
- [2. 当前项目真实状态](#2-当前项目真实状态)
- [3. 资料可靠性与交叉核验方法](#3-资料可靠性与交叉核验方法)
  - [3.1 本轮资料准入标准](#31-本轮资料准入标准)
  - [3.2 已交叉核验资料表](#32-已交叉核验资料表)
  - [3.3 证据等级说明](#33-证据等级说明)
- [4. 权威资料调研摘要](#4-权威资料调研摘要)
  - [4.1 数据集与评估协议](#41-数据集与评估协议)
  - [4.2 强基线与近期 SOTA 范式](#42-强基线与近期-sota-范式)
  - [4.3 可训练创新方向](#43-可训练创新方向)
  - [4.4 高分辨率与多模板方向](#44-高分辨率与多模板方向)
  - [4.5 多类别统一模型与通用表征方向](#45-多类别统一模型与通用表征方向)
- [5. 我们当前方案的创新性评估](#5-我们当前方案的创新性评估)
- [6. 候选创新路线评分](#6-候选创新路线评分)
- [7. 推荐主线：RA-MT-DSDF](#7-推荐主线ra-mt-dsdf)
  - [7.1 研究问题](#71-研究问题)
  - [7.2 方法总览](#72-方法总览)
  - [7.3 模块设计](#73-模块设计)
  - [7.4 损失函数与训练目标](#74-损失函数与训练目标)
  - [7.5 为什么这条路线有创新性](#75-为什么这条路线有创新性)
- [8. 推荐辅线](#8-推荐辅线)
  - [8.1 PO3AD 官方训练对照与 Norm-AS 迁移](#81-po3ad-官方训练对照与-norm-as-迁移)
  - [8.2 Reg2Inv/3DKeyAD 启发的配准表征对照](#82-reg2inv3dkeyad-启发的配准表征对照)
  - [8.3 高分辨率局部候选区域重评分](#83-高分辨率局部候选区域重评分)
  - [8.4 多类别 shared head 扩展](#84-多类别-shared-head-扩展)
- [9. 不建议作为近期主线的方向](#9-不建议作为近期主线的方向)
- [10. P7-P8 实验矩阵](#10-p7-p8-实验矩阵)
- [11. 8xRTX 4090 48G 算力使用计划](#11-8xrtx-4090-48g-算力使用计划)
- [12. 代码框架与接口建议](#12-代码框架与接口建议)
  - [12.1 目录结构](#121-目录结构)
  - [12.2 核心数据结构](#122-核心数据结构)
  - [12.3 CLI 与产物规范](#123-cli-与产物规范)
  - [12.4 测试策略](#124-测试策略)
- [13. 风险与止损条件](#13-风险与止损条件)
- [14. 迁移会话提示词](#14-迁移会话提示词)
- [15. References](#15-references)
<!-- TOC END -->

## 0. 会话延续建议

建议**继续在当前会话推进**。原因是当前会话已经保留了 P0-P6 的实验结论、失败样本、SOP 约束、Docker/Git 边界和用户偏好，直接继续能减少新 agent 重新理解项目的损耗。

同时，为防止后续上下文压缩或需要换 agent，本文件第 14 节提供了迁移会话提示词。也就是说：**当前继续工作，迁移提示词作为备份**。

## 1. 结论先行

当前 P0-P6 的工作已经是一个合格的“强基线复现 + 失败分析 + 工程证据包”，但如果目标是研究创新，仅停留在 PASDF 复现和 bad case 分析是不够的。

已完成工作的真实定位如下：

1. **P3 是强基线复现**：PASDF 官方权重在 Anomaly-ShapeNet 40 类协议上达到 mean object AUROC=`0.900214149779`，mean pixel AUROC=`0.896009030694`。
2. **P4 是有价值的负结果**：normal/curvature/distance 的 naive geometry fusion 没有稳定拉开 anomaly 与 positive control，因此不能包装成有效新方法。
3. **P5-P6 是 failure-mode closure**：`cap3/tap1/helmet1` 的诊断清楚，但仍属于分析型贡献，不是新的训练型模型。
4. **下一阶段必须进入可训练路线**：要有模块、loss、消融、GPU 训练和可复查指标，否则创新性不够。

推荐的下一阶段主线是：

> **RA-MT-DSDF：Registration-aware Multi-template Discriminative SDF**
>
> 中文描述：配准感知的多模板判别式 SDF 异常检测。

核心思想：保留 PASDF 的 pose-aware continuous SDF 强基线，但把我们实测发现的失败模式变成训练目标和模块设计：

- `cap3`：多模板 normal prototype bank + registration confidence，减少 template mismatch false positive。
- `tap1`：positive-aware calibration，避免把低幅度局部信号或 geometry residual 误推成对象级强异常。
- `helmet1`：pseudo anomaly / discriminative SDF，增强点级定位能力。

最低目标是先做 `cap3/tap1/helmet1/ashtray0` 四类 smoke，而不是直接 40 类全量训练。四类 smoke 只要满足以下任一结果，就足以进入 P8 扩展：

- `cap3_positive9/7/10` 的 false positive object score 被明显压低，且 anomaly 不被同步压低。
- `tap1` 的 anomaly/positive boundary margin 改善。
- `helmet1` pixel AUROC 或 weak-localization count 明显改善。
- 四类平均 object/pixel AUROC 不低于 PASDF baseline，且至少一个 failure class 有清楚正收益。

## 2. 当前项目真实状态

### 2.1 已完成

| 阶段 | 状态 | 关键产物 | 当前结论 |
|---|---|---|---|
| P0-P2 | 已完成 | 仓库、环境、数据统计、DataLoader、可视化 smoke | 可稳定运行 PASDF 评估 |
| P3 | 已完成 | `experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv` | PASDF 40 类复现达标 |
| P4 | 已完成 | A2/A3/A4 geometry smoke | naive geometry fusion 不扩主表 |
| P5 | 已完成 | PASDF score export、targeted case study | `cap3/tap1/helmet1` failure mode 明确 |
| P6 | 已完成 | alpha sweep、region explanation、calibration、failure closure、delivery pack | 当前交付包可信，但创新性不足 |

### 2.2 已有关键指标

| 指标 | 数值 | 来源 |
|---|---:|---|
| PASDF mean object AUROC | `0.900214149779` | `docs/document/stage_record/2026-06-08_p0_p3_stage_check.md` |
| PASDF mean pixel AUROC | `0.896009030694` | `docs/document/stage_record/2026-06-08_p0_p3_stage_check.md` |
| `cap3_positive9` object score | `0.109517` | `docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md` |
| `cap3_positive9` residual/PASDF overlap | `0.902439` | `docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md` |
| `tap1` best PASDF top-k 状态 | soft pass only | `docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.md` |
| `helmet1` weak-localization count | `3` at top-k `1%` | `docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.md` |

### 2.3 已被本项目实测否定的方向

以下方向不应继续作为主线：

- 直接把 distance、normal、curvature residual 手工加权相加后扩 40 类。
- 只调 top-k ratio 试图修复 `cap3` object boundary。
- 只因为 `tap1` geometry 图更红就恢复 additive geometry fusion。
- 只做更多 bad case 图，而不提出可训练模块。

## 3. 资料可靠性与交叉核验方法

### 3.1 本轮资料准入标准

本轮只使用以下资料作为正式依据：

- arXiv 官方页面。
- CVF/OpenAccess 官方论文页面或 PDF。
- OpenReview 官方页面。
- IJCAI/AAAI/ACM/ECVA 等官方会议或出版页面。
- 论文作者官方 GitHub 或项目页。
- 本仓库已入库 stage record 和实验结果。

不作为正式证据的资料：

- 博客、二手解读、排行榜搬运、营销页。
- 无法确认作者身份的非官方代码仓库。
- 未能找到论文页或官方代码交叉验证的单条消息。

### 3.2 已交叉核验资料表

| 方向 | 论文/项目 | 一手来源 | 代码/项目页 | 本文用途 | 证据等级 |
|---|---|---|---|---|---|
| SDF 强基线 | PASDF | arXiv:2505.24431 | `github.com/ZZZBBBZZZ/PASDF` | 当前 baseline 与主线改造对象 | A |
| 判别式 offset | PO3AD | CVF CVPR 2025 | `github.com/yjnanan/PO3AD` | 训练型强对照、Norm-AS 迁移 | A |
| 主基准 | Anomaly-ShapeNet / IMRNet | CVF CVPR 2024 | `github.com/Chopper-233/Anomaly-ShapeNet` | 主评估协议 | A |
| 真实高精度 | Real3D-AD / Reg3D-AD | OpenReview NeurIPS 2023 | `github.com/M-3LAB/Real3D-AD` | P8 真实场景泛化 | A |
| diffusion 重建 | R3D-AD | arXiv:2407.10862 / ECCV 2024 | `github.com/zhouzheyuan/r3d-ad` | 生成式备选，不作近期主线 | A- |
| 判别式 SDF | DLF-3AD | arXiv:2605.03437 | 暂不依赖代码 | 支撑 discriminative SDF 方向 | B+ |
| 配准表征 | Reg2Inv | arXiv:2510.16865 | `github.com/CHen-ZH-W/Reg2Inv` | 支撑 registration-aware 方向 | B+ |
| 高分辨率 | MiniShift / Simple3D | arXiv:2507.07435 / AAAI PDF | 需实施前再核代码成熟度 | 支撑 high-res local rescore | B+ |
| 多模板高分辨率 | 3DKeyAD | arXiv:2507.13110 | 未作为代码依赖 | 支撑 multi-prototype + clustering | B |
| 多类别统一 | MC3D-AD | IJCAI 2025 官方页 | `github.com/iCAN-SZU/MC3D-AD` | P8 shared-head 参考 | A |
| 语义解耦统一 | SeDiR | CVF CVPR 2026 | 项目页可查 | P8/P9 多类统一参考 | A |
| consistency 生成 | CM3D-AD | arXiv:2605.05372 / CVPRW 2026 | 需实施前再核代码 | 只作生成式低优先级参考 | B+ |
| 点云自监督 | Point-MAE | ECCV 2022 / ECVA PDF | `github.com/Pang-Yatian/Point-MAE` | 表征/重建辅线 | A |
| 点云自监督 | Point-BERT | CVPR 2022 / arXiv | `github.com/Julie-tang00/Point-BERT` | 表征/重建辅线 | A |
| 点云 backbone | Point Transformer V3 | CVF CVPR 2024 | `github.com/Pointcept/PointTransformerV3` | PO3AD/PTv3 训练参考 | A |
| neural field 表征 | 3DShape2VecSet | ACM TOG/SIGGRAPH 2023 | `github.com/1zb/3DShape2VecSet` | 长线 shape prior 参考 | A |

### 3.3 证据等级说明

- **A**：论文官方页 + 官方代码/项目页均可核验，适合作为实现或强论据。
- **A-**：论文和代码可核验，但与本仓库集成成本较高，适合作为对照或备选。
- **B+**：论文官方页可核验，代码成熟度或开放状态仍需实施前复查。
- **B**：论文官方页可核验，但当前不把代码可用性作为前提，只作为方法启发。

## 4. 权威资料调研摘要

### 4.1 数据集与评估协议

**Anomaly-ShapeNet / IMRNet, CVPR 2024**

Anomaly-ShapeNet 是当前项目主基准。CVF 官方页面说明其由 40 类、1600 个点云样本组成，并配套 IMRNet 自监督重建方法。论文报告 IMRNet 在 Anomaly-ShapeNet 上 I-AUC 为 `66.1%`，在 Real3D-AD 上 I-AUC 为 `72.5%`。本项目已经遵循 40 类协议跑通 PASDF，当前数据版本是课程包高密度点云，下采样到 `16384` 点后评估。

对我们的启发：

- 数据集每类正常训练样本少，容易过拟合单 template。
- 40 类协议仍是主表入口，P7 不能只停留在单样本可视化。
- 若做训练型模块，必须先四类 smoke，再扩 40 类。

**Real3D-AD / Reg3D-AD, NeurIPS 2023**

OpenReview 官方页面说明 Real3D-AD 包含 1254 个高分辨率真实 3D 样本，单样本从四万点到数百万点，并提供 360 度覆盖和高精度点云。它比 Anomaly-ShapeNet 更接近真实工业扫描。

对我们的启发：

- P7 主线仍应先在 Anomaly-ShapeNet 四类完成，但 P8 至少需要 Real3D-AD 子集验证。
- 真实高分辨率会放大配准、采样和局部微缺陷问题。

**MiniShift / Simple3D**

MiniShift/Simple3D 强调 50 万点级高分辨率点云和小于 1% 的微小缺陷。官方 arXiv 摘要报告 MiniShift 包含 2577 个点云样本，每个样本 500k 点，Simple3D 通过多尺度邻域描述子和局部特征聚合获得实时推理。

对我们的启发：

- 当前课程包原始点数最高到 157824，已经比公开 Anomaly-ShapeNet pcd 更高。
- 不应只在 16k 采样点上讨论定位质量，应规划从 16k top-k candidate 映射回高密度局部 patch 的 refinement。

### 4.2 强基线与近期 SOTA 范式

**PASDF**

PASDF 通过 pose-aware SDF 将异常定位和几何修复统一到连续隐式表面表示中。官方 arXiv 页面报告 Anomaly-ShapeNet object AUROC 为 `90.0%`，Real3D-AD object AUROC 为 `80.2%`。我们复现出的 mean object AUROC=`0.900214149779` 与该公开指标一致。

关键启发：

- PASDF 的优势来自 `pose alignment + continuous SDF`，不是简单点到点距离。
- 我们 P6 发现 `cap3` 高 false positive 与 template residual 高重叠，这说明 PASDF 的配准和 template 选择仍是可创新入口。

**PO3AD**

PO3AD 是 CVPR 2025 方法，提出预测 point offset，而不是让模型平均关注正常和伪异常区域。CVF 官方摘要说明它使用 normal-vector-guided pseudo anomaly generation，也就是 Norm-AS，并在 Anomaly-ShapeNet 和 Real3D-AD 上分别相对已有方法提升 AUC-ROC detection metric `9.0%` 和 `1.4%`。

关键启发：

- 伪异常生成的质量比单纯 reconstruction loss 更关键。
- 我们可以把 Norm-AS 从 offset prediction 迁移到 SDF margin training：正常表面点的 SDF 接近 0，伪异常点应被推离正常零水平面。

**R3D-AD**

R3D-AD 使用 diffusion reconstruction 和 Patch-Gen 伪异常策略。arXiv 摘要指出它通过 diffusion 过程遮蔽输入异常几何，并学习点级 displacement 来修正异常点，报告 Anomaly-ShapeNet image-level AUROC `74.9%`、Real3D-AD `73.4%`。

关键启发：

- 生成式修复能给点级 displacement 信号，但当前指标不优于 PASDF。
- 训练和调参成本较高，不适合替代 P7 主线，可作为 P8/P9 小子集探索。

### 4.3 可训练创新方向

**Discriminative SDF / DLF-3AD**

DLF-3AD 的 arXiv 摘要明确提出 learning a discriminative signed distance function，并包含 Noisy Points Generation、Multi-scale Level-of-detail Feature、Implicit Surface Discrimination 三个模块。它报告 Anomaly-ShapeNet object AUROC `92.1%`、point AUROC `92.4%`，Real3D-AD object AUROC `85.9%`、point AUROC `85.2%`。由于其实现可用性仍需在正式复现前单独核查，本项目应把它作为学术方向证据，而不是直接依赖其代码。

关键启发：

- 当前 PASDF 更像强 SDF residual baseline，缺少“异常点应被判别地推开”的训练目标。
- P7 的核心创新可以是把 PASDF 的连续 SDF 与 PO3AD/DLF-3AD 的 pseudo abnormal training 结合。

**Reg2Inv**

Reg2Inv 认为点云 registration 不只是几何预处理，还能作为 rotation-invariant feature learner。arXiv 摘要强调 registration failure 会造成 unreliable detection，并提出 joint alignment and representation learning。

关键启发：

- 我们的 `cap3` 结论与该方向高度吻合：配准质量不应只当作隐含步骤，而应输出 confidence/uncertainty 并参与 scoring。
- 可以把 registration confidence 设计成 RA-MT-DSDF 的显式中间变量。

### 4.4 高分辨率与多模板方向

**3DKeyAD**

3DKeyAD 提出 multi-prototype alignment + cluster-wise discrepancy，并用 keypoint-guided clustering 在高分辨率点云上定位异常。其摘要直接提到高分辨率点云的计算开销、空间错位敏感性和局部结构差异捕获困难。

关键启发：

- 多模板不是简单 ensemble，而是正常形态多 prototype 的必要建模。
- 对 `cap3` 这类帽檐、鸭舌形态差异明显的类，多 prototype 比单 template 更合理。
- 对高分辨率场景，应先候选区域，再局部 cluster/patch 重评分，而不是把全量点一次送入主模型。

### 4.5 多类别统一模型与通用表征方向

**MC3D-AD**

IJCAI 2025 官方页说明 MC3D-AD 针对多类别 3D anomaly detection，目标是避免每个类别都单独训练模型，使用 local/global geometry-aware 信息重建正常表示，并报告相对单类别 SOTA 的 object AUROC 改善。

**SeDiR**

CVPR 2026 官方页说明统一多类别模型容易受到 inter-category entanglement 影响，SeDiR 通过 coarse-to-fine global tokenization、category-conditioned contrastive learning 和 geometry-guided decoder 解决语义混叠问题。

关键启发：

- 单类 PASDF 复现虽然强，但不容易形成“统一方法”的创新叙事。
- P7 先做四类，P8 可以尝试 shared encoder + class/template token + SDF head。
- 多类别统一风险高，不应作为 P7 的第一个实现目标。

**Point-MAE / Point-BERT / Point Transformer V3 / 3DShape2VecSet**

这些工作不是 3D AD 专用方法，但提供强点云表征或 neural field 先验。Point-MAE/Point-BERT 适合做 masked reconstruction 或 feature memory baseline；PTv3 是 PO3AD 类判别式模型的强 backbone；3DShape2VecSet 适合长线 shape prior，但改造成点级 anomaly scorer 的工程风险较高。

## 5. 我们当前方案的创新性评估

| 项目部分 | 创新性 | 可靠性 | 当前定位 |
|---|---:|---:|---|
| PASDF 40 类复现 | 低 | 高 | 强基线锚点 |
| P4 normal/curvature/distance 模块 | 中 | 中 | 负结果与诊断工具 |
| P5 targeted case study | 中 | 高 | 失败分析贡献 |
| P6 calibration/failure closure | 中 | 高 | failure-mode evidence |
| Delivery pack | 工程中 | 高 | 可交付证据包 |
| RA-MT-DSDF | 高 | 待验证 | P7 主创新 |
| PO3AD 自跑与 Norm-AS 迁移 | 中高 | 中 | 强对照与伪异常训练参考 |
| High-res local rescore | 中高 | 中 | 工业部署扩展 |
| Multi-category shared head | 高 | 中低 | P8/P9 扩展 |

判断：如果不进入 P7，项目只能说“我们复现了强方法并做了严谨失败分析”。这在工程课设中可信，但在研究创新上不够。P7 必须补上训练型模块和明确消融。

## 6. 候选创新路线评分

评分范围 1-5，越高越好。风险越高表示越不确定。

| 路线 | 创新性 | 可行性 | 与现有代码契合 | 8x4090 利用 | 风险 | 结论 |
|---|---:|---:|---:|---:|---:|---|
| RA-MT-DSDF：多模板 + 配准置信度 + 判别 SDF + positive-aware calibration | 5 | 4 | 5 | 4 | 3 | **主推** |
| PO3AD 官方训练 + Norm-AS 迁移 | 4 | 3 | 3 | 5 | 3 | **强对照** |
| Reg2Inv/3DKeyAD 启发的 registration-aware feature/prototype | 4 | 4 | 4 | 4 | 3 | **并入主线** |
| High-res local patch rescore | 4 | 4 | 4 | 3 | 2 | **P8 推荐** |
| Multi-category shared encoder + class/template token | 5 | 3 | 3 | 5 | 4 | P8/P9 扩展 |
| DLF-3AD 风格 full discriminative SDF 重实现 | 5 | 2 | 3 | 5 | 4 | 不直接重做全文，抽取 loss 思路 |
| Diffusion/consistency model | 5 | 2 | 2 | 5 | 5 | 小子集探索，不作主线 |
| Point-MAE/Point-BERT feature memory baseline | 3 | 4 | 3 | 4 | 2 | 保底对照 |
| 3DShape2VecSet anomaly scorer | 5 | 2 | 2 | 5 | 5 | 长线研究，不作近期主线 |

## 7. 推荐主线：RA-MT-DSDF

RA-MT-DSDF 全称为 **Registration-aware Multi-template Discriminative SDF**。

### 7.1 研究问题

当前 PASDF 强，但我们已经观察到三类不同 failure mode：

- `cap3_positive9/7/10` 是正常样本，却有很高 object score；高分点与 template residual 高分点高度重叠。
- `tap1_broken2/broken3/hole0` 有局部点级信号，但 object boundary 偏软，geometry residual 又容易抬高 positive。
- `helmet1` 对象级不算完全失败，但点级定位弱。

因此 P7 的研究问题应写成：

> 能否通过多模板 normal prototype、显式 registration confidence、pseudo anomaly 判别训练和 positive-aware calibration，降低 template mismatch false positive，同时保留或增强 PASDF 的点级异常定位能力？

### 7.2 方法总览

输入：每类 4 个训练正常样本、测试点云、PASDF per-point score、必要时的模板点云/SDF 查询结果。

输出：

- `template_id`：当前样本最可信 normal template。
- `registration_confidence`：配准可信度。
- `template_uncertainty`：不同模板解释之间的分歧。
- `score_sdf`：PASDF 或新训练 SDF 的 per-point/object score。
- `score_calibrated`：positive-aware object score。
- `score_local_refined`：可选高分辨率局部重评分。

最小可实现路径分三步：

1. **P7-A：不训练的 multi-template scoring**。先验证多模板和 confidence 是否能压低 `cap3_positive9/7/10`。
2. **P7-B：轻量 calibration head**。基于 PASDF score、template residual、overlap、bbox ratio、registration confidence 训练小模型，先修 object boundary。
3. **P7-C：discriminative SDF pseudo anomaly training**。引入 Norm-AS/NPG 风格伪异常，让 SDF 学会 normal/pseudo abnormal margin。

### 7.3 模块设计

#### M1：Multi-template normal prototype bank

每类不再只依赖一个 `template0`，而是构建 K 个 normal prototype：

- K=1：PASDF 原始口径，对照组。
- K=2/4：从该类 4 个正常训练样本中选择多个模板。
- assignment：对测试样本分别做 coarse alignment/nearest-neighbor residual/chamfer proxy，选择 residual 最小或 confidence 最大的模板。
- soft assignment：保留多个模板分数，计算 uncertainty。

输出字段：

```text
class_name
sample_id
template_id
template_rank
chamfer_mean
nn_topk_mean
residual_overlap
assignment_entropy
registration_confidence
```

#### M2：Registration confidence / uncertainty

registration confidence 不应只看一个距离指标。建议组合：

- nearest-neighbor residual 的 mean/top-k/quantile。
- 高 PASDF 点与高 residual 点的 overlap。
- bbox coverage ratio。
- pairwise spread ratio。
- 多模板分数差距：`score_top1 - score_top2` 或 entropy。

解释：

- 若 `score_sdf` 高、`residual_overlap` 高、`assignment_entropy` 高，且样本 label 是 positive control，则更像 template mismatch。
- 若 `score_sdf` 高但 residual 与 GT 区域一致，则更像真实 anomaly。

#### M3：Discriminative SDF pseudo anomaly training

参考 PO3AD 的 Norm-AS 和 DLF-3AD 的 NPG/ISD 思路，SDF 不只拟合 normal surface，还要学习 normal/pseudo abnormal margin。

伪异常生成候选：

- 法向方向 outward/inward perturbation。
- 局部 patch cut/broken/hole。
- curvature-aware perturbation。
- registration jitter positive control，用来约束模型不要把轻微配准变化误判成异常。

关键点：P4 证明 geometry 不适合直接加权为 object score，但 geometry 可以作为伪异常生成和训练监督的来源。

#### M4：Positive-aware calibration head

P6 已经证明 naive fusion 的主要风险是 positive control 被抬高。因此 calibration head 的训练和选择必须显式看 positive/anomaly boundary。

输入特征：

```text
pasdf_topk
pasdf_gt_proxy_spread
template_residual_topk
residual_overlap
bbox_ratio
pair_ratio
assignment_entropy
registration_confidence
class_id_or_template_token
```

输出：

```text
score_calibrated
confidence
failure_reason
```

训练标签不直接用测试 GT。四类 smoke 阶段可使用：

- normal training samples + generated pseudo anomalies。
- positive control 作为 calibration validation，不参与伪造提升。
- anomaly test labels 只用于最终评估，不用于调参时反复偷看。

### 7.4 损失函数与训练目标

建议的最小 loss：

```text
L = L_sdf_normal
  + lambda_margin * L_margin_pseudo
  + lambda_consistency * L_template_consistency
  + lambda_calib * L_positive_calibration
```

其中：

- `L_sdf_normal`：正常 surface query 的 SDF 接近 0。
- `L_margin_pseudo`：伪异常点的 SDF residual 高于 margin。
- `L_template_consistency`：同一正常样本在相近模板解释下 score 不应剧烈跳变。
- `L_positive_calibration`：positive control 的 object score 不应被 calibration head 抬高。

最低实现可以先不训练完整 SDF MLP，只训练 calibration head；如果 P7-A/P7-B 已经修复 `cap3`，再进入 P7-C 的 SDF 训练。

### 7.5 为什么这条路线有创新性

RA-MT-DSDF 不是简单复现 PASDF，因为它新增：

- 多模板 normal prototype bank。
- registration confidence/uncertainty 显式输出。
- pseudo anomaly discriminative SDF training。
- positive-aware object calibration。
- 直接针对本项目真实 failure mode 的消融闭环。

它也不是 P4 naive geometry fusion，因为它不把 normal/curvature/distance 手工加到 final score，而是把这些信号放进 template assignment、伪异常生成和 calibration 约束中。

## 8. 推荐辅线

### 8.1 PO3AD 官方训练对照与 Norm-AS 迁移

目的：

- 建立 PASDF 之外的强训练型对照。
- 检查 `helmet1` 点级弱定位是否是 SDF 特有问题，还是 3D AD 普遍问题。
- 把 Norm-AS 迁移到 SDF margin training。

最小实验：

| 实验 | 类别 | 输出 |
|---|---|---|
| PO3AD smoke | `cap3/tap1/helmet1/ashtray0` | object/pixel AUROC、false positive list、heatmap |
| Norm-AS transplant | 同上 | pseudo anomaly generation 产物和 SDF margin loss smoke |

### 8.2 Reg2Inv/3DKeyAD 启发的配准表征对照

目的：

- 让配准从“前处理步骤”变成“可解释中间变量”。
- 检查 `cap3` false positive 是否能由 multi-prototype assignment 修复。

最小实验：

- 对每个测试样本与 4 个 normal template 分别计算 residual/confidence。
- 输出 top-1/top-2 margin 和 assignment entropy。
- 比较 PASDF object score、residual score 和 calibrated score 的排序。

### 8.3 高分辨率局部候选区域重评分

目的：

- 回应用户之前观察到的 `tap1` GT 点很少、黑色 GT 点不明显的问题。
- 避免 16k 下采样损失微小缺陷。

建议流程：

1. 在 16k 点上用 PASDF/RA-MT-DSDF 得到 top-k candidate。
2. 映射回原始高密度点云。
3. 以 candidate 为中心取局部 patch。
4. 在 patch 上计算 local SDF residual / geometry descriptor / cluster discrepancy。
5. 输出 refined heatmap 与原始 GT overlay。

这条路线适合 P8，不抢 P7 主线。

### 8.4 多类别 shared head 扩展

目的：

- 借鉴 MC3D-AD/SeDiR，避免 40 类每类单独训练。
- 在 P7 四类成功后，尝试 shared encoder + class/template token。

最小设计：

```text
shared_point_encoder(points)
class_token(class_id)
template_token(template_id)
sdf_head(shared_feature, class_token, template_token, query_points)
calibration_head(score_features, class_token)
```

风险：多类别语义混叠会伤害异常定位，必须作为 P8/P9，而不是 P7 起点。

## 9. 不建议作为近期主线的方向

### 9.1 继续手工调 geometry fusion

P4/P6 已经给出负结果。继续调权重很难形成可信创新，且会被 positive control 反例击穿。

### 9.2 直接复刻完整 DLF-3AD

DLF-3AD 思想非常相关，但直接重做全文会变成另一个复现项目。我们应该抽取 `discriminative SDF + noisy/pseudo abnormal training` 思想，结合 PASDF failure evidence 做自己的模块。

### 9.3 直接上 diffusion 或 consistency model

R3D-AD/CM3D-AD 有研究价值，但当前指标和工程成本不适合替代 PASDF 主线。可以作为 P8 小子集探索。

### 9.4 3DShape2VecSet 作为唯一主线

shape prior 很有吸引力，但它不是 AD 原生任务，点级投影、训练时间和环境依赖都不轻。建议只做 smoke 或未来工作。

### 9.5 只做 zero-shot / point-language model

zero-shot 方向适合附录，但本项目最强证据是 3D 几何、PASDF、registration failure 和 SDF scoring。转向多视角/语言模型会削弱主线一致性。

## 10. P7-P8 实验矩阵

### 10.1 P7 四类 smoke

| 实验 ID | 方法 | 类别 | 目标 | 是否必须 |
|---|---|---|---|---|
| P7-A0 | 固定 PASDF baseline | `cap3/tap1/helmet1/ashtray0` | 对照与复核输入 | 是 |
| P7-A1 | multi-template scoring | 同上 | 降低 `cap3` template false positive | 是 |
| P7-A2 | registration confidence metrics | 同上 | 输出 confidence/uncertainty 证据 | 是 |
| P7-A3 | positive-aware calibration head | 同上 | 修 object boundary | 是 |
| P7-A4 | pseudo anomaly generation | 同上 | 为 discriminative SDF 训练准备数据 | 是 |
| P7-A5 | discriminative SDF smoke | 同上 | 点级定位和对象级分离改进 | 建议 |
| P7-B1 | PO3AD official smoke | 同上 | 判别式强对照 | 建议 |

### 10.2 P8 扩展

| 实验 ID | 方法 | 范围 | 目标 |
|---|---|---|---|
| P8-A | RA-MT-DSDF 40 类 | Anomaly-ShapeNet 40 类 | 判断是否进入主表 |
| P8-B | Real3D-AD subset | 2-4 类 | 合成到真实泛化 |
| P8-C | high-res local rescore | 3-5 个样本 | 微小缺陷定位 refinement |
| P8-D | multi-class shared head | 4 类或 40 类 | 统一模型探索 |

### 10.3 必须报告的指标

- object AUROC / object AUPR。
- pixel AUROC / pixel AUPR。
- false positive top list。
- `max positive - min anomaly` boundary margin。
- weak localization count。
- registration confidence distribution。
- multi-template assignment entropy。
- 推理时间、显存、训练耗时。

### 10.4 P7 成功门槛

四类 smoke 阶段至少满足以下之一：

| 成功门槛 | 解释 |
|---|---|
| `cap3_positive9/7/10` score 明显下降 | 证明 template false positive 被修复 |
| `tap1` strict boundary 由 failed 变为 pass | 证明 calibration 有对象级收益 |
| `helmet1` weak-localization count 下降 | 证明点级定位有改善 |
| 四类平均 object/pixel AUROC 不低于 PASDF，且一类 failure 明显改善 | 证明没有破坏强 baseline |

### 10.5 止损门槛

如果四类 smoke 同时出现以下问题，应停止该路线：

- positive score 被系统性抬高。
- anomaly score 与 positive score margin 变差。
- object AUROC 提升但 pixel AUROC 明显下降，且无法解释。
- 同一命令不同 run 的 ranking 不稳定。

## 11. 8xRTX 4090 48G 算力使用计划

8 张 4090 不应继续只用于 CPU 评估和小图可视化。建议按实验并行，而不是单次盲目大 sweep。

| GPU | 任务 | 说明 |
|---:|---|---|
| 0 | `cap3` multi-template + calibration | template false positive 主类 |
| 1 | `tap1` calibration + pseudo anomaly | soft boundary 主类 |
| 2 | `helmet1` discriminative SDF smoke | 点级定位弱主类 |
| 3 | `ashtray0` control | 防止新方法破坏强 baseline |
| 4 | hyperparameter sweep | K templates、margin、top-k ratio、calibration features |
| 5 | PO3AD official smoke | 判别式训练对照 |
| 6 | Real3D-AD/high-res local rescore | P8 扩展预研 |
| 7 | evaluation/visualization/retry | 汇总、失败重跑、图像产出 |

执行原则：

- 每次只开放 2-3 个有效变量，不做无约束 grid search。
- 每个实验目录必须包含 config snapshot、git hash、metrics CSV、README。
- smoke 成功前不扩 40 类。
- 大训练在 Docker/conda 内执行；git pull/commit/push 在宿主机执行。

## 12. 代码框架与接口建议

### 12.1 目录结构

建议新增模块：

```text
src/pcdad/prototypes/
  __init__.py
  template_bank.py          # normal template bank, assignment, confidence
  registration_confidence.py

src/pcdad/training/
  __init__.py
  pseudo_anomaly.py         # Norm-AS / NPG / patch corruption
  discriminative_sdf.py     # losses and training utilities

src/pcdad/calibration/
  __init__.py
  positive_aware.py         # calibration head, boundary metrics

scripts/
  build_template_bank.py
  run_p7_multitemplate.py
  train_p7_calibration.py
  train_p7_discriminative_sdf.py
  run_po3ad_smoke.py

configs/experiment/
  P7_ra_mt_dsdf_cap3.yaml
  P7_ra_mt_dsdf_tap1.yaml
  P7_ra_mt_dsdf_helmet1.yaml
  P7_ra_mt_dsdf_ashtray0.yaml
```

接口原则：

- `scripts/` 只做参数解析和调用。
- 所有核心逻辑放 `src/pcdad/`。
- 第三方 repo 不直接改源码。
- 每个新模块先写纯函数单测，再跑真实实验。

### 12.2 核心数据结构

建议最小 dataclass：

```python
@dataclass(frozen=True)
class TemplateAssignment:
    class_name: str
    sample_id: str
    template_id: str
    rank: int
    nn_mean: float
    nn_topk_mean: float
    residual_overlap: float
    bbox_ratio: float
    pair_ratio: float
    assignment_entropy: float
    registration_confidence: float
```

```python
@dataclass(frozen=True)
class CalibrationRecord:
    class_name: str
    sample_id: str
    label: int
    pasdf_score: float
    template_score: float
    registration_confidence: float
    calibrated_score: float
    failure_reason: str
```

```python
@dataclass(frozen=True)
class PseudoAnomalySpec:
    mode: str
    normal_scale: float
    patch_radius: float
    curvature_weight: float
    jitter_scale: float
    seed: int
```

### 12.3 CLI 与产物规范

每个脚本输出：

```text
experiments/P7_<method>/<class_or_scope>/<run_id>/
  config.yaml
  git_hash.txt
  metrics.csv
  per_sample_scores.csv
  failure_toplist.csv
  README.md
  svg/
```

关键命令示例：

```bash
PYTHONPATH=src python scripts/run_p7_multitemplate.py \
  --score-root experiments/P5_pasdf_scores/representative \
  --template-root third_party/PASDF/data/ShapeNetAD \
  --classes cap3 tap1 helmet1 ashtray0 \
  --output-dir experiments/P7_ra_mt_dsdf/multitemplate_smoke
```

```bash
PYTHONPATH=src python scripts/train_p7_calibration.py \
  --input-csv experiments/P7_ra_mt_dsdf/multitemplate_smoke/per_sample_scores.csv \
  --classes cap3 tap1 helmet1 ashtray0 \
  --output-dir experiments/P7_ra_mt_dsdf/calibration_smoke
```

### 12.4 测试策略

必须新增单测：

- `tests/test_template_bank.py`
  - 多模板排序稳定。
  - assignment entropy 在单模板时为 0。
  - residual overlap 边界值正确。
- `tests/test_registration_confidence.py`
  - confidence 在高 residual/高 entropy 时下降。
  - 输入缺字段时抛出明确错误。
- `tests/test_pseudo_anomaly.py`
  - 法向扰动保持 shape。
  - patch corruption 可复现。
  - seed 固定时输出一致。
- `tests/test_positive_aware_calibration.py`
  - positive score 不被 calibration head 无约束抬高。
  - boundary margin 计算正确。

## 13. 风险与止损条件

| 风险 | 表现 | 止损条件 | 替代方案 |
|---|---|---|---|
| 多模板没有改善 | `cap3_positive9/7/10` 仍排最高 | 四类 smoke 无一改善 | 转向 discriminative SDF/PO3AD |
| calibration 过拟合 | validation positive 被压低但 anomaly 也被压低 | AUROC 或 margin 变差 | 降低特征复杂度，只保留 confidence gate |
| pseudo anomaly 不真实 | 训练 loss 好看但真实 anomaly 无收益 | pixel/object 都不改善 | 调整 Norm-AS/NPG 或只保留 calibration |
| 训练工程过重 | 3 天内无法稳定训练 1 类 | loss/指标不可复现 | 先完成 non-training multi-template |
| PO3AD 环境阻塞 | PTv3/Minkowski/依赖失败 | 半天无法跑通 smoke | 只保留论文值与 Norm-AS 思路 |
| high-res rescore 太慢 | 单样本分钟级以上 | 无法批量 10 样本 | 只作为可视化附录 |
| 40 类扩展失败 | 四类好，40 类均值下降 | 均值下降且无 failure 修复 | 只把 RA-MT-DSDF 定位为 targeted robustness module |

## 14. 迁移会话提示词

如需换新 agent，可直接使用：

```text
你是一个 3D 点云异常检测方向的资深研究型工程 agent。当前仓库位于：
/home/xiaobo.xia/JiafengWu/code_folder/area1/Anomaly

请先阅读：
1. docs/document/SERVER_AGENT_KICKOFF.md
2. docs/document/SOP_engineering_workflow.md
3. docs/document/3d_point_cloud_defect_detection_research_plan.md
4. docs/document/stage_record/2026-06-14_p6_delivery_evidence_pack.md
5. docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md
6. docs/document/delivery_pack/2026-06-14_p6_delivery_pack/README.md
7. docs/document/tech_arche/P7_innovation_research_roadmap.md

当前状态：
- P3 PASDF 40 类 baseline 已复现，mean object AUROC=0.900214149779，mean pixel AUROC=0.896009030694。
- P4 naive geometry enhancement 已收口为负结果，不扩 40 类。
- P5/P6 完成 cap3/tap1/helmet1 failure-mode closure。
- cap3 主要问题是 registration/template false positive。
- tap1 主要问题是 PASDF soft object boundary，不恢复 additive geometry fusion。
- helmet1 主要问题是点级定位弱和 positive boundary 混淆。
- 当前 tag v0.1-p6-delivery，最新 main 已包含 delivery pack。

下一阶段目标：
不要继续停留在复现和 bad case 分析。请执行 P7 创新路线，优先设计并实现 RA-MT-DSDF：multi-template prototype bank + registration confidence + discriminative SDF pseudo anomaly training + positive-aware calibration。先做 cap3/tap1/helmet1/ashtray0 四类 smoke，再决定是否扩 40 类。所有训练和测试在 Docker/conda 容器中执行，git push/pull 在宿主机执行。文档必须中文，关键设计先写入 docs/document/tech_arche/。
```

## 15. References

1. Bozhong Zheng, Jinye Gan, Xiaohao Xu, Xintao Chen, Wenqiao Li, Xiaonan Huang, Na Ni, Yingna Wu. **Bridging 3D Anomaly Localization and Repair via High-Quality Continuous Geometric Representation**. arXiv:2505.24431, 2025. https://arxiv.org/abs/2505.24431 . Official code: https://github.com/ZZZBBBZZZ/PASDF .
2. Jianan Ye, Weiguang Zhao, Xi Yang, Guangliang Cheng, Kaizhu Huang. **PO3AD: Predicting Point Offsets toward Better 3D Point Cloud Anomaly Detection**. CVPR 2025, pp. 1353-1362. https://openaccess.thecvf.com/content/CVPR2025/html/Ye_PO3AD_Predicting_Point_Offsets_toward_Better_3D_Point_Cloud_Anomaly_CVPR_2025_paper.html . Official code: https://github.com/yjnanan/PO3AD .
3. Wenqiao Li, Xiaohao Xu, Yao Gu, Bozhong Zheng, Shenghua Gao, Yingna Wu. **Towards Scalable 3D Anomaly Detection and Localization: A Benchmark via 3D Anomaly Synthesis and A Self-Supervised Learning Network**. CVPR 2024, pp. 22207-22216. https://openaccess.thecvf.com/content/CVPR2024/html/Li_Towards_Scalable_3D_Anomaly_Detection_and_Localization_A_Benchmark_via_CVPR_2024_paper.html . Official dataset/code: https://github.com/Chopper-233/Anomaly-ShapeNet .
4. Jiaqi Liu, Guoyang Xie, Ruitao Chen, Xinpeng Li, Jinbao Wang, Yong Liu, Chengjie Wang, Feng Zheng. **Real3D-AD: A Dataset of Point Cloud Anomaly Detection**. NeurIPS 2023 Datasets and Benchmarks. https://openreview.net/forum?id=zGthDp4yYe . Official code/data: https://github.com/M-3LAB/Real3D-AD .
5. Zheyuan Zhou, Le Wang, Naiyu Fang, Zili Wang, Lemiao Qiu, Shuyou Zhang. **R3D-AD: Reconstruction via Diffusion for 3D Anomaly Detection**. ECCV 2024 / arXiv:2407.10862. https://arxiv.org/abs/2407.10862 . Official code: https://github.com/zhouzheyuan/r3d-ad .
6. Haibo Xiao, Hanzhe Liang, Jie Zhou, Jinbao Wang, Can Gao. **Learning Discriminative Signed Distance Functions from Multi-scale Level-of-detail Features for 3D Anomaly Detection**. arXiv:2605.03437, 2026. https://arxiv.org/abs/2605.03437 .
7. Yuyang Yu, Zhengwei Chen, Xuemiao Xu, Lei Zhang, Haoxin Yang, Yongwei Nie, Shengfeng He. **Registration is a Powerful Rotation-Invariance Learner for 3D Anomaly Detection**. arXiv:2510.16865, 2025. https://arxiv.org/abs/2510.16865 . Official code: https://github.com/CHen-ZH-W/Reg2Inv .
8. Yuqi Cheng, Yihan Sun, Hui Zhang, Weiming Shen, Yunkang Cao. **Towards High-Resolution 3D Anomaly Detection: A Scalable Dataset and Real-Time Framework for Subtle Industrial Defects**. arXiv:2507.07435, 2025. https://arxiv.org/abs/2507.07435 .
9. Zi Wang, Katsuya Hotta, Koichiro Kamide, Yawen Zou, Chao Zhang, Jun Yu. **3DKeyAD: High-Resolution 3D Point Cloud Anomaly Detection via Keypoint-Guided Point Clustering**. arXiv:2507.13110, 2025. https://arxiv.org/abs/2507.13110 .
10. Jiayi Cheng, Can Gao, Jie Zhou, Jiajun Wen, Tao Dai, Jinbao Wang. **MC3D-AD: A Unified Geometry-aware Reconstruction Model for Multi-category 3D Anomaly Detection**. IJCAI 2025, pp. 837-845. https://www.ijcai.org/proceedings/2025/94 . Official code: https://github.com/iCAN-SZU/MC3D-AD .
11. SuYeon Kim, Wongyu Lee, MyeongAh Cho. **A Semantically Disentangled Unified Model for Multi-category 3D Anomaly Detection**. CVPR 2026, pp. 33036-33045. https://openaccess.thecvf.com/content/CVPR2026/html/Kim_A_Semantically_Disentangled_Unified_Model_for_Multi-category_3D_Anomaly_Detection_CVPR_2026_paper.html .
12. Pranav A, Shashank B, Pranav Siddappa, Dominik Seuss, Minal Moharir, Subramanya KN. **Two Steps Are All You Need: Efficient 3D Point Cloud Anomaly Detection with Consistency Models**. CVPR Workshops 2026 / arXiv:2605.05372. https://arxiv.org/abs/2605.05372 .
13. Yatian Pang, Wenxiao Wang, Francis E. H. Tay, Wei Liu, Yonghong Tian, Li Yuan. **Masked Autoencoders for Point Cloud Self-supervised Learning**. ECCV 2022. https://www.ecva.net/papers/eccv_2022/papers_ECCV/papers/136620591.pdf . Official code: https://github.com/Pang-Yatian/Point-MAE .
14. Xumin Yu, Lulu Tang, Yongming Rao, Tiejun Huang, Jie Zhou, Jiwen Lu. **Point-BERT: Pre-training 3D Point Cloud Transformers with Masked Point Modeling**. CVPR 2022. https://arxiv.org/abs/2111.14819 . Official code: https://github.com/Julie-tang00/Point-BERT .
15. Xiaoyang Wu, Li Jiang, Peng-Shuai Wang, Zhijian Liu, Xihui Liu, Yu Qiao, Wanli Ouyang, Tong He, Hengshuang Zhao. **Point Transformer V3: Simpler, Faster, Stronger**. CVPR 2024. https://arxiv.org/abs/2312.10035 . Official code: https://github.com/Pointcept/PointTransformerV3 .
16. Biao Zhang, Jiapeng Tang, Matthias Niessner, Peter Wonka. **3DShape2VecSet: A 3D Shape Representation for Neural Fields and Generative Diffusion Models**. ACM TOG / SIGGRAPH 2023. https://dl.acm.org/doi/abs/10.1145/3592442 . Official code: https://github.com/1zb/3DShape2VecSet .
17. 本仓库阶段记录：`docs/document/stage_record/2026-06-08_p0_p3_stage_check.md`、`docs/document/stage_record/2026-06-09_p4_geometry_closure.md`、`docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md`、`docs/document/stage_record/2026-06-14_p6_delivery_evidence_pack.md`。
