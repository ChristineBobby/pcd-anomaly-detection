# 3D 点云缺陷检测调研与立项方案

撰写日期：2026 年 6 月 7 日
文档定位：课程设计用“调研 + 立项”方案
项目周期：20-30 天
团队规模：5 人
核心策略：以 Anomaly-ShapeNet 为主基准，选择一个可运行的开源 3D 表征/异常检测底座进行二次开发；复现只作为实验锚点，不作为创新边界。

<!-- TOC START -->
## 目录

- [1. 项目摘要](#1-项目摘要)
- [2. 背景与问题定义](#2-背景与问题定义)
- [3. 数据集与任务地图](#3-数据集与任务地图)
  - [3.1 主基准：Anomaly-ShapeNet](#31-主基准anomaly-shapenet)
  - [3.2 真实高精度场景：Real3D-AD](#32-真实高精度场景real3d-ad)
  - [3.3 高分辨率压力测试：MiniShift / Simple3D](#33-高分辨率压力测试minishift--simple3d)
  - [3.4 早期工业 3D 基准：MVTec 3D-AD](#34-早期工业-3d-基准mvtec-3d-ad)
  - [3.5 可选多传感器数据：MulSen-AD](#35-可选多传感器数据mulsen-ad)
- [4. 文献综述](#4-文献综述)
  - [4.0 SOTA 基准对照表（已逐项联网核实）](#40-sota-基准对照表已逐项联网核实)
  - [4.1 数据集与任务奠基工作](#41-数据集与任务奠基工作)
  - [4.2 强 3D AD 基线：任务锚点应升级为当前 SOTA（PO3AD / PASDF）](#42-强-3d-ad-基线任务锚点应升级为当前-sotapo3ad--pasdf)
  - [4.3 可改造开源底座：从“复现论文”转向“迁移强 3D 表征”](#43-可改造开源底座从复现论文转向迁移强-3d-表征)
  - [4.4 零样本与基础模型方向](#44-零样本与基础模型方向)
  - [4.5 点云自监督与骨干网络](#45-点云自监督与骨干网络)
- [5. 立项目标与交付物](#5-立项目标与交付物)
  - [5.1 核心目标](#51-核心目标)
  - [5.2 最低可交付版本](#52-最低可交付版本)
  - [5.3 理想版本](#53-理想版本)
- [6. 技术路线](#6-技术路线)
  - [6.1 总体流程](#61-总体流程)
  - [6.2 开源底座选择与批判性比较](#62-开源底座选择与批判性比较)
  - [6.3 主力路线：PASDF 复现 + 位姿对齐 + 几何残差增强](#63-主力路线pasdf-复现--位姿对齐--几何残差增强)
  - [6.4 稳健创新模块：曲率/法向感知伪异常生成](#64-稳健创新模块曲率法向感知伪异常生成)
  - [6.5 统一评分模块：多尺度几何提示与 top-k 聚合](#65-统一评分模块多尺度几何提示与-top-k-聚合)
  - [6.6 可选零样本扩展](#66-可选零样本扩展)
- [7. 实验设计](#7-实验设计)
  - [7.1 数据划分与预处理](#71-数据划分与预处理)
  - [7.2 评价指标](#72-评价指标)
  - [7.3 主实验矩阵](#73-主实验矩阵)
  - [7.4 消融实验](#74-消融实验)
  - [7.5 可视化与分析](#75-可视化与分析)
- [8. 算力与工程可行性](#8-算力与工程可行性)
- [9. 五人分工](#9-五人分工)
- [10. 20-30 天排期](#10-20-30-天排期)
  - [第 1-4 天：环境、数据、PASDF 复现起步](#第-1-4-天环境数据pasdf-复现起步)
  - [第 5-10 天：SOTA 锚点对齐](#第-5-10-天sota-锚点对齐)
  - [第 11-17 天：几何增强与消融](#第-11-17-天几何增强与消融)
  - [第 18-23 天：多数据集验证与压力测试](#第-18-23-天多数据集验证与压力测试)
  - [第 24-30 天：报告、PPT 和归档](#第-24-30-天报告ppt-和归档)
- [11. 风险与应对](#11-风险与应对)
- [12. 预期报告结构](#12-预期报告结构)
- [13. 已验证参考资料](#13-已验证参考资料)
- [14. 结论](#14-结论)
<!-- TOC END -->

## 1. 项目摘要

3D 点云缺陷检测的目标是在只使用正常样本或极少标注的条件下，判断工业物体是否存在几何异常，并在点级别定位异常区域。与 2D 图像异常检测相比，点云缺陷检测更关注三维表面结构、曲率突变、局部凹凸、断裂、孔洞、姿态偏差和采样密度变化。该方向近两年发展很快，已经从早期的 MVTec 3D-AD、Real3D-AD 真实扫描数据集，扩展到 Anomaly-ShapeNet、MulSen-AD、MiniShift 等更大规模或更高分辨率的基准。

本课程设计不应被理解成“找一篇 3D AD 论文随便复现一下”。更合理的立项方式是：先固定任务、数据集和指标，**以当前 SOTA（PASDF / PO3AD）为主力 backbone 复现到对标水平，再在其上做几何增强与系统性分析**。课设达到与顶会同等指标即视为成功，贡献定位在增强模块、失败分析与泛化研究，而非另起炉灶。推荐的主线是：

- 主数据集：Anomaly-ShapeNet，完整跑通训练、验证、可视化和报告。
- 次数据集：Real3D-AD，选择若干类别做真实场景泛化验证。
- 压力测试：MiniShift 或 MVTec 3D-AD 子集，用于讨论高分辨率、细微缺陷和不同采样密度下的局限。
- 主力 backbone：**PASDF（ICCV'25，Anomaly-ShapeNet O-AUROC 90.0 / Real3D-AD 80.2，SOTA）**，保底 backbone：Point-MAE/Point-BERT/PointNeXt 等点云骨干；对照锚点：PO3AD（CVPR'25，83.9/89.8）。3DShape2VecSet/VecSetX、Uni3D/OpenShape/ULIP 作为研究性补充或扩展，不作主线。
- 创新/贡献：在 SOTA backbone 之上叠加位姿对齐质量分析、法向/曲率/多尺度几何残差及其消融、分缺陷类型与分类别失败分析、合成→真实泛化研究。
- 可选扩展：参考 PointAD、PointAD+、BTP、OpenShape、Uni3D、ULIP 的点云-语言或点云-像素表示，做跨类别或跨数据集定性比较。

最低可交付版本为：Anomaly-ShapeNet 全类别或官方 40 类协议下的主实验 + 一个 SOTA backbone（PASDF 或保底路线）复现到可运行 + Real3D-AD 2-4 个类别抽样验证 + 点级热力图 + 消融表 + 失败案例分析。即使 MiniShift 或 MulSen-AD 因下载、显存或时间限制未完成，项目仍然完整。

## 2. 背景与问题定义

工业质检中的异常往往表现为表面微小形变、局部缺失、裂纹、凹陷、凸起或装配偏差。传统 2D 图像能捕获颜色和纹理，但对无纹理表面、透明物体、反光物体和真实几何形变并不稳定。点云直接记录物体表面的三维坐标，更适合判断结构缺陷。

本项目采用无监督或仅正常样本训练的异常检测设定。训练阶段主要使用正常样本，模型学习“正常几何形态”；测试阶段输入可能含缺陷的点云，输出两类结果：

- 对象级检测：判断整件物体是否异常，常用 O-AUROC、O-AUPR、I-AUC 或官方 benchmark 指标。
- 点级定位：给每个点一个异常分数，得到缺陷热力图，常用 P-AUROC、P-AUPR、PRO 或官方点级指标。

项目需要回答四个问题：

1. 哪类开源 3D 底座最适合作为 20-30 天课程设计的主线：AD 专用方法、强形状 autoencoder、点云自监督 backbone，还是开放世界多模态表示？
2. 强 encoder/decoder 或 neural field 表征能否通过重建残差、latent 偏离或局部几何残差转化为点级 anomaly heatmap？
3. 曲率、法向和多尺度邻域结构是否能提升点云缺陷定位，尤其是 crack、hole、concavity 等局部异常？
4. 方法从合成缺陷迁移到真实扫描数据时，最容易失败在哪些类别、缺陷类型和采样密度条件上？

## 3. 数据集与任务地图

### 3.1 主基准：Anomaly-ShapeNet

Anomaly-ShapeNet 是本项目的必做主基准。它基于 ShapeNet 合成点云异常，CVPR 2024 论文同时提出 IMRNet。官方仓库（已核实）说明：全集共 1600 个样本，从原始 40 类扩展到 40(+10)=50 类（新 10 类放在 `new` 目录），含 6 种异常（bulge、concavity、crack、hole、broken、sink），每类训练正常样本 4 个、测试 15~24 个，官方公开 pcd 点数约 8K~30K，异常占比约 1%~7%。本项目主实验遵循论文与官方 `Benchmark.pdf` 的 **40 类协议**（训练 40×4=160 个正常样本）。

> ⚠️ 数据口径待核实：课程任务书给出的点数为 17422~157824（均值约 55429）、测试 1312 个样本，明显高于官方公开 pcd 的 8K~30K。这说明课程方很可能分发了**网格重采样后的高密度版本**或不同打包。**第 1 天必须用脚本统计课程实际数据的真实点数分布、类别数与样本数**，并以实测值覆盖本节，下采样/显存/FPS 策略都依赖该实测结果。

选择它作为主基准有三个原因：

- 数据规模适中，下载和训练成本可控，适合课程设计周期。
- 异常类型和类别较多，适合做分类型失败分析。
- 近年 3D 点云异常检测论文普遍在该数据集上报告结果，方便对比 IMRNet、R3D-AD、PO3AD、MC3D-AD、PASDF、CASL 等方法。

执行建议：优先按官方 benchmark 的 40 类协议建立统一评估入口；底座可以不同，但数据划分、指标脚本、可视化和日志格式必须统一。若时间充足，再补充扩展 10 类或选择若干代表类别做额外分析。

### 3.2 真实高精度场景：Real3D-AD

Real3D-AD 是 NeurIPS 2023 Datasets & Benchmarks 数据集，包含 12 个类别、1,254 个高分辨率真实点云样本，单个样本从四万点到数百万点不等，官方同时提出 Reg3D-AD。它比 Anomaly-ShapeNet 更接近真实扫描场景，但预处理、下采样和配准成本明显更高。

本项目不建议在 Real3D-AD 上做全量主实验。更实际的做法是选择 2-6 个类别作为二阶段验证，例如 airplane、car、duck、shell 或 gemstone，覆盖不同点数、透明/非透明和不同缺陷比例。报告中重点分析合成数据训练得到的几何异常评分是否能迁移到真实点云。

### 3.3 高分辨率压力测试：MiniShift / Simple3D

MiniShift 是 AAAI 2026 数据集，强调高分辨率和细微缺陷。其样本规模为 2,577 个点云，每个样本 500,000 点，异常区域小于 1%。配套方法 Simple3D 使用多尺度邻域描述符和局部特征聚合，突出高分辨率场景下传统几何描述子的价值。

MiniShift 很适合用于讨论本项目方法的局限：当异常区域很小、点数很高、下采样会损失缺陷区域时，基于重建或局部打分的方法是否仍然可靠。考虑到时间和算力，建议只做子集实验，或仅复现 Simple3D 的一两个命令作为压力测试参考。

### 3.4 早期工业 3D 基准：MVTec 3D-AD

MVTec 3D-AD 是较早的无监督 3D 异常检测基准，包含 10 个物体类别和精确缺陷标注。它经常被多模态或零样本方法使用，因为它同时涉及 2D/2.5D/3D 表示。对本项目而言，MVTec 3D-AD 可以作为“跨基准讨论”而非主实验，特别适合在文献综述中说明 2D、RGB-D 和点云方法的差异。

### 3.5 可选多传感器数据：MulSen-AD

MulSen-AD 是 CVPR 2025 多传感器异常检测数据集，包含 RGB、点云和红外热成像等模态。它对课程设计的价值主要在背景和未来工作部分：真实工业缺陷不一定只体现在几何上，很多内部缺陷需要红外或其他传感器才能发现。本项目可以引用它说明“纯点云方案的边界”，但不建议把多传感器融合纳入核心实现。

## 4. 文献综述

### 4.0 SOTA 基准对照表（已逐项联网核实）

> 说明：下表数值全部来自官方仓库 `Benchmark.pdf` 与各方法 arXiv 原文（2026-06 核实），不依赖任何二手转述或记忆。空缺项表示该指标在可获取的原文页面中未给出确切数字，**不与其他口径混填**。Anomaly-ShapeNet 采用官方 40 类协议下的 O-AUROC（对象级，等价于部分论文的 I-AUROC）与 P-AUROC（点级）。

**表 4-A　Anomaly-ShapeNet（40 类）方法阶梯**

| 方法 | 会议/年份 | 核心范式 | 主干网络 | O-AUROC | P-AUROC | 来源 |
|---|---|---|---|---|---|---|
| BTF (Raw) | CVPR'23 | 手工几何描述子 | — | 49.3 | 55.0 | PO3AD Tab.1 |
| BTF (FPFH) | CVPR'23 | 手工几何描述子 | — | 52.8 | 62.8 | PO3AD Tab.1 |
| M3DM | CVPR'23 | 多模态记忆库 | Point-MAE | 55.2 | 61.6 | PO3AD Tab.1 |
| PatchCore (FPFH) | CVPR'22 | 记忆库 | FPFH | 56.8 | — | PO3AD Tab.1 |
| CPMF | PR'24 | 多视角投影+记忆 | — | 55.9 | 54.5 | PO3AD Tab.1 |
| Reg3D-AD | NeurIPS'23 | 配准+记忆库 | Point-MAE | 57.2 | 66.8 | PO3AD Tab.1 |
| **IMRNet** | **CVPR'24** | 迭代掩码重建 | Transformer | **66.1** | 65.0 | 官方 Benchmark.pdf |
| **R3D-AD** | **ECCV'24** | 扩散重建+Patch-Gen 伪异常 | Diffusion | **74.9** | — | R3D-AD 摘要 |
| **PO3AD** | **CVPR'25** | 预测点偏移+法向引导伪异常 | **Point Transformer V3** | **83.9** | **89.8** | PO3AD Tab.1 |
| **PASDF** | **ICCV'25** | 位姿对齐+连续 SDF+修复 | SDF-MLP | **90.0** | — | PASDF 摘要/Tab |
| **CASL** | **AAAI'26** | 多尺度曲率提示+U-Net 重建 | U-Net | leading（SOTA 级，原文未给全表均值） | — | CASL 摘要 |
| MC3D-AD | IJCAI'25 | 多类别统一几何重建 | Transformer | 多类设定下较单类 SOTA +9.3% | — | MC3D-AD 摘要 |

**表 4-B　Real3D-AD（12 类，真实高分辨率）方法阶梯**

| 方法 | 会议/年份 | O-AUROC | P-AUROC | 来源 |
|---|---|---|---|---|
| IMRNet | CVPR'24 | 72.5 | — | 官方 Benchmark.pdf |
| R3D-AD | ECCV'24 | 73.4 | — | R3D-AD 摘要 |
| Group3AD | ACM MM'24 | 75.1 | 73.5 | PASDF Tab.1 |
| PO3AD | CVPR'25 | 较 SOTA +1.4% | — | PO3AD 摘要 |
| **PASDF** | **ICCV'25** | **80.2** | 74.5 | PASDF Tab.1 |

**从对照表得到的三条立项级结论：**

1. **真正的性能天花板是 PASDF（O-AUROC 90.0）与 PO3AD（83.9 / P-AUROC 89.8），而非 IMRNet（66.1）。** 本项目的对照组（baseline）必须至少包含 PO3AD 或 PASDF 之一；只与 IMRNet 比较会被视为"刻意压低 baseline"，对答辩不利。建议将"任务锚点"从 IMRNet 升级为 PO3AD/PASDF。
2. **位姿对齐（registration / canonicalization）是被本方案低估的胜负手。** PASDF 之所以达到 90.0，核心在于先用 RANSAC + ICP + Chamfer 反馈把测试样本对齐到 canonical pose，再学连续 SDF；位姿不变性直接决定隐式场残差是否可靠。本方案第 6 章必须显式加入"位姿对齐模块"，否则任何 SDF/重建残差路线都会被姿态变化污染。
3. **强主干带来显著收益。** PO3AD 使用 Point Transformer V3 作为主干，而非 PointNet++/DGCNN 级网络。若走点云判别式路线，主干应优先考虑 PTv3 / Point-MAE，而不是轻量网络。

### 4.1 数据集与任务奠基工作

Anomaly-ShapeNet / IMRNet 将大规模合成 3D 异常和自监督重建网络结合起来，提供了 3D 点云缺陷检测可扩展 benchmark。IMRNet 通过 mask reconstruction 和迭代重建比较输入与修复结果，适合作为本项目的任务定义来源。

Real3D-AD / Reg3D-AD 解决了真实高精度点云数据不足的问题，强调 360 度覆盖、高分辨率、真实扫描和基于配准的检测基线。它是检验合成到真实泛化能力的关键数据集。

MVTec 3D-AD 提供较早的无监督 3D 异常检测和定位协议，是理解 2D、深度图、点云和多模态异常检测的重要起点。

MiniShift / Simple3D 把重点放在 50 万点高分辨率点云和占比小于 1% 的细微缺陷，说明只在低分辨率点云上取得好结果并不等同于可工业部署。

MulSen-AD 将外观、几何和内部属性统一到多传感器异常检测中，提示纯几何点云方法对内部缺陷和材料异常存在天然盲区。

### 4.2 强 3D AD 基线：任务锚点应升级为当前 SOTA（PO3AD / PASDF）

> 锚点定位（依据 §4.0 实测对照表）：本项目的对照与目标锚点应是**当前 SOTA**——PASDF（O-AUROC 90.0）与 PO3AD（O-AUROC 83.9、P-AUROC 89.8），而非 IMRNet（66.1）。把锚点设在 SOTA 上，既保证结果表可信，也使"复现一个强方法并做充分分析"本身成为合格的课设贡献。

PO3AD（CVPR 2025）是最强的判别式锚点之一，Anomaly-ShapeNet 上 O-AUROC 83.9 / P-AUROC 89.8（较 R3D-AD 提升约 9 个点）。它把训练任务设计为**预测点偏移**：用法向引导（Norm-AS）生成更可信的伪异常，让模型集中学习伪异常点到正常形态的位移幅度与方向，推理时直接用预测偏移作为异常分数。值得注意的是其主干为 **Point Transformer V3（PTv3）**，说明强主干对该任务收益显著。代码仓库提供完整训练/评估脚本，作者说明可在 RTX 3090 上运行，工程可行性高，适合作为本项目的**主对照方法**。

CASL 适合提供几何启发。它提出曲率增强自监督学习，核心观察是点级曲率本身就是有效的异常信号，并使用多尺度曲率提示引导 U-Net 重建。CASL 对本项目的启发很直接：不要只把点云当作无序 XYZ 坐标，也要把局部几何变化显式输入模型或评分函数。但 CASL 本身仍是 AD 专用框架，若作为主底座，应把创新重点放在“曲率如何与更强形状先验结合”，而不是只重复曲率提示。

R3D-AD 使用扩散模型重建异常点云，并提出 Patch-Gen 伪异常生成策略。它的结果和思想都很有价值，但扩散模型训练成本较高，不适合作为 20-30 天课程设计的首选主实现。

MC3D-AD 关注多类别统一模型，避免为每个类别单独训练。它适合用于对比“单类别训练”和“多类别共享模型”的取舍。如果团队进度顺利，可以把多类别训练作为扩展讨论。

PASDF（ICCV 2025）是当前 Anomaly-ShapeNet 公开**最高 O-AUROC（90.0）**、Real3D-AD 最高（80.2）的方法，将异常定位与几何修复统一在连续 signed distance field 中。其关键不在 SDF 本身，而在**位姿对齐 + 连续表示**两点：(1) Pose-wise Alignment Module（PAM）先用 RANSAC + ICP + Chamfer 反馈把每个样本对齐到 canonical pose，从而把"形状内在变化"与"姿态干扰"解耦；(2) 对齐后训练 SDF 网络（带正弦位置编码、clamped L1 损失），推理时以 `A(x)=|f_θ(x)|`（点到学到的正常零水平面的偏离）作为点级异常分数，top-K 聚合得对象级分数，并可用 Marching Cubes 抽取零水平面实现 in-situ 修复。其实现复杂度高于普通点云网络，但**官方已开源代码**，且课程算力（4090/3090）充足——因此本项目将其列为**主力 backbone 候选**而非"不建议复刻"（见 §6 路线 A 重写）。

### 4.3 可改造开源底座：从“复现论文”转向“迁移强 3D 表征”

3DShape2VecSet 是值得认真考虑的路线。它是 SIGGRAPH 2023 / ACM TOG 工作，官方 PyTorch 仓库已开源。论文目标不是异常检测，而是把 surface model 或 point cloud 编码成 neural field 上的 vector set 表示，用于形状编码、生成扩散、点云补全、文本/图像条件生成等任务。它的 encoder/decoder 比普通点云 AD 网络更偏“形状先验”，因此可以尝试改造成缺陷检测：

- 训练阶段只使用正常点云，学习每个类别或多类别的正常 shape latent。
- 测试阶段输入异常点云，经过 encoder-decoder 或 neural field 查询，得到重建点云、occupancy/SDF 场或采样表面。
- 点级异常分数来自输入点到重建表面的距离、局部 SDF 残差、法向/曲率残差，或 latent 与正常样本 latent 分布的距离。
- 若使用 3DShape2VecSet 的补全能力，可以把缺陷区域视为“被正常形状先验修复的区域”，再比较修复前后差异。

这条路线的优势是创新性强，能体现“把强 3D encoder/decoder 迁移到工业缺陷检测”。风险是工程量不低：原仓库主要面向 ShapeNet 形状表示和生成，训练命令默认需要较长周期，输出也不天然对应 Anomaly-ShapeNet 的逐点标签。若选择它作为主线，必须从一开始就设计点级投影和 anomaly score，不能只说“encoder/decoder 很强”。

VecSetX 是 3DShape2VecSet 作者后续维护的 VecSet 系列框架，加入 FlashAttention、normalized bottleneck、SDF regression 等工程增强，并提供部分预训练模型。它更现代，但环境依赖更重，README 中示例使用 PyTorch nightly、CUDA 12.4、FlashAttention、torch-cluster 等。它适合作为“如果环境顺利则使用”的增强底座，不适合作为唯一保底方案。

Point-MAE 和 Point-BERT 是更稳的自监督点云 backbone 路线。它们通过 masked modeling 学习局部 patch 表征，改造为缺陷检测时可以用 masked reconstruction error、patch token distance、feature memory bank 或轻量 decoder 输出 anomaly score。优势是代码成熟、点云输入直接，缺点是形状修复能力不如 3DShape2VecSet / SDF 类模型。

PointNeXt、PointMLP、DGCNN、PointNet++ 是判别式点云 backbone 路线。它们适合做快速特征提取、patch 分类头或 memory bank baseline。优势是实现和训练成本低，劣势是没有天然重建输出，点级 anomaly score 需要额外设计。

DeepSDF、Occupancy Networks、PASDF、3DShape2VecSet 代表隐式场/连续几何表示路线。它们适合处理“正常表面是什么”的问题，理论上很适合缺陷修复和重建残差；但若输入只是不完整点云或采样稀疏，点级标签投影、SDF 采样和推理速度都会成为风险。

Uni3D、OpenShape、ULIP 是开放世界 3D 表征和多模态对齐路线。它们能提供强全局语义 embedding，适合跨类别检索、zero-shot 分类或文本提示分析。对点级缺陷定位而言，它们不是天然主线，因为全局 embedding 很难直接给出细粒度 heatmap。更合理的用法是作为辅助分支：判断类别语义、跨数据集定性分析，或与几何异常热力图做后融合。

### 4.4 零样本与基础模型方向

PointAD 将 3D 点云渲染成多视角 2D 图像，再借助 CLIP 等视觉语言模型学习零样本异常语义，并把 2D 表示投回 3D 空间。它适合说明“当目标类别无训练样本时，能否用通用语义知识识别异常”。

PointAD+ 在 PointAD 基础上进一步加入显式 3D 表示和层次文本提示，强调渲染异常与空间异常的联合理解。由于它主要是预印本方向，建议在本项目中只作为未来工作或定性参考。

BTP 直接探索 point-language model 在零样本 3D 异常检测中的作用，避免把点云完全转成 2D 图像导致几何细节丢失。它与本项目的几何提示评分存在思想联系：异常检测不能只依赖视觉语义，也要保留点云原生几何。

### 4.5 点云自监督与骨干网络

Point-MAE 和 Point-BERT 代表点云 masked modeling 自监督预训练路线。它们不是专门为异常检测设计，但提供了可迁移的点云表征学习思路。

Point Transformer 为点云自注意力网络提供了基础结构，很多后续 3D 表征方法都借鉴其局部邻域建模和注意力机制。课程设计中不需要从头实现 Point Transformer，但需要理解其在点云局部结构建模中的作用。

## 5. 立项目标与交付物

### 5.1 核心目标

1. 完成 Anomaly-ShapeNet 数据集下载、预处理、官方指标脚本和可视化流程。
2. 在 Linux 服务器打通 PASDF（主力）环境，先用官方权重复现到接近 SOTA（O-AUROC≈90.0），再决定重训。
3. 加跑 PO3AD（对照锚点，目标≈83.9）；准备 Point-MAE 保底路线。
4. 在 PASDF 之上实现并消融本项目的几何增强：法向残差、多尺度曲率残差、多尺度 top-k + 局部一致性聚合。
5. 在 Anomaly-ShapeNet 40 类上完成主实验与消融实验，并量化位姿对齐(PAM)的贡献。
6. 在 Real3D-AD 选定类别上做二阶段验证，讨论合成→真实泛化。
7. 输出完整课程设计报告、PPT、可视化图和可运行 demo（含 SDF 修复展示）。

### 5.2 最低可交付版本

最低可交付版本不依赖所有数据集都完成，要求如下：

- Anomaly-ShapeNet 数据预处理和评估入口可复现。
- **PASDF 用官方权重复现成功，得到与论文可比的 O/P-AUROC**（哪怕未重训）。
- 至少一个对照锚点可比：PO3AD 实测结果，或 PO3AD/IMRNet 文献报告值（明确标注口径）。
- 至少 3 个类别有点级异常热力图、GT overlay 和失败案例。
- 至少完成消融：PASDF 原始 → +法向残差 → +曲率残差 → +多尺度 top-k 聚合，以及"关闭位姿对齐"对照。
- Real3D-AD 至少 2 个类别完成推理或抽样验证。
- 报告中明确写出未完成 MiniShift / MulSen-AD 全量实验的原因和后续计划。

### 5.3 理想版本

理想版本在最低可交付版本基础上增加：

- Anomaly-ShapeNet 官方 40 类完整结果。
- Real3D-AD 6-12 类验证。
- MiniShift 或 MVTec 3D-AD 子集压力测试。
- 与 IMRNet、R3D-AD、PO3AD、CASL、MC3D-AD、Simple3D 的文献结果对比表。
- 对 3DShape2VecSet/VecSetX、Point-MAE/Point-BERT、Uni3D/OpenShape/ULIP 等候选底座给出实测或工程可行性记录。
- 速度、显存和点数规模分析。
- 一个可交互 demo：输入点云，输出异常分数和 3D heatmap。

## 6. 技术路线

### 6.1 总体流程

项目流程分为六步：

1. 数据预处理：读取 PCD/PLY/OBJ，统一坐标归一化、采样点数、法向估计和邻域索引。
2. **位姿对齐（关键，新增）**：用 RANSAC（FPFH 粗配准）+ ICP 精配准 + Chamfer 反馈，把训练/测试样本对齐到 canonical pose。这是 PASDF 拿到 90.0 O-AUROC 的核心前提——位姿不变性直接决定 SDF/重建残差是否可靠。
3. 底座筛选：先在 1-2 个类别上跑通候选 repo 的输入、输出和 checkpoint，不急于全量训练。
4. 底座适配：把选定底座改造成 anomaly scorer，而不是只复现原任务。
5. 几何增强：融合重建/隐式场/latent 残差、法向变化和多尺度曲率差异，得到点级异常分数。
6. 评估可视化：输出对象级指标、点级指标、分类型结果、失败案例和计算开销。

### 6.2 开源底座选择与批判性比较

本项目建议把底座分为四类，并设置“决策门”：

| 路线 | 代表开源项目 | 适配思路 | 优势 | 主要风险 | 结论 |
|---|---|---|---|---|---|
| **SOTA AD 专用底座** | **PASDF、PO3AD**、CASL、MC3D-AD | 直接复现 SOTA + 位姿对齐，叠加几何增强模块 | **指标可达 SOTA（PASDF 90.0）**、代码开源、与点级定位直接对齐 | 复现工程量中等，需打通环境 | **推荐作为主力 backbone** |
| 强形状 encoder/decoder | 3DShape2VecSet、VecSetX、DeepSDF、Occupancy Networks | 正常形状重建、SDF/occupancy 残差、latent 偏离 | 思路与 PASDF 一脉相承，可作创新补充 | 训练/点级投影复杂，且与 PASDF 高度重叠 | 降为研究性补充，不作主线 |
| 点云自监督/判别 backbone | Point-MAE、Point-BERT、PointNeXt、PointMLP、DGCNN | patch feature distance、masked reconstruction、memory bank | 工程稳定，点云输入直接 | 重建能力有限，需额外 anomaly head | 推荐作为稳健保底主线 |
| 开放世界/多模态表征 | Uni3D、OpenShape、ULIP、PointAD、BTP | 文本/图像/点云 embedding 辅助跨类别分析 | 语义泛化强，适合 zero-shot 展示 | 全局语义不等于点级定位 | 适合扩展，不建议单独做主线 |

推荐的立项主线有两种：

- **路线 A（首选）：以 PASDF 为主力 backbone，跑通官方代码达到/接近 SOTA，再叠加本项目的几何增强与系统性分析作为课设贡献。** 优先级最高，指标有保障（目标 O-AUROC 接近 90.0）。第 1 周必须验证：官方 repo 能在现有 GPU 上完成位姿对齐 + SDF 训练，并复现单类别结果。课设的"创新/贡献"不要求超越 PASDF，而定位在：(i) 补充法向/曲率/多尺度几何残差并消融其增益；(ii) 系统的分缺陷类型 / 分类别失败分析；(iii) 合成→真实（Real3D-AD）泛化分析；(iv) 位姿对齐对各异常类型的敏感性研究。
- 路线 B（保底）：Point-MAE/Point-BERT 或 PointNeXt 作为稳健点云 backbone + 几何伪异常 + 多尺度 scoring。风险低于路线 A，适合 PASDF 环境受阻时切换。

> 关于"主创新撞车"：PASDF 已经实现了"连续 SDF + 修复 + 残差定位"。本项目**直接以 PASDF 为主力是经过认可的策略**——课设达到与顶会同等水平即合格，不必另起炉灶自研 3DShape2VecSet 路线（后者与 PASDF 高度重叠且工程风险更高）。3DShape2VecSet/VecSetX 仅在路线 A 提前完成、且想探讨"更强形状先验是否进一步提升"时，作为研究性补充实验。

若 PASDF 环境（SDF 训练、位姿对齐、点级投影）无法在第 1 周打通，应及时切换到路线 B，同时保留 PASDF 的调研与失败原因作为报告贡献。

### 6.3 主力路线：PASDF 复现 + 位姿对齐 + 几何残差增强

路线 A 以 PASDF 为主力 backbone，目标是先复现到接近官方 SOTA（O-AUROC≈90.0），再在其上做增强与分析。建议流程：

1. **位姿对齐（PAM）**：对每个样本，voxel 下采样后提取 FPFH → RANSAC 粗配准 → ICP 精配准，以 Chamfer 距离作收敛反馈，迭代对齐到一个选定的 canonical 正常样本坐标系。这一步决定后续 SDF 残差的可靠性，必须先单独验证对齐质量（可视化对齐前后叠加图）。
2. **SDF 训练（仅正常样本）**：在对齐后的正常点云附近采样 query 点（表面/外部/内部三类），加正弦位置编码，训练 SDF 网络 `f_θ`，用 clamped L1 损失拟合最近邻 GT 距离。每类别或多类别共享一个 SDF。
3. **点级异常分数**：测试样本先经 PAM 对齐，再把表面点输入 `f_θ`，以 `A(x)=|f_θ(x)|`（偏离学到的零水平面的程度）作为点级异常分数。
4. **几何残差增强（本项目贡献点）**：在 PASDF 原始 SDF 残差之外，叠加法向残差、多尺度曲率残差、局部一致性平滑项（见 §6.5），并消融每一项对 P-AUROC / O-AUROC 的增益。
5. **对象级聚合**：用 top-K pooling（取异常分数最高的 1%/3%/5% 点求均值），而非简单最大值。
6. **可选修复展示**：用 Marching Cubes 抽取 `f_θ` 零水平面得到正常模板 mesh，采样为修复点云，与输入对比，作为 demo 亮点。

报告需回答的研究问题：PASDF 的 SDF 残差在哪些缺陷类型（crack/hole/bulge/concavity/broken/sink）上最敏感、在哪些类别上因 shape prior 过强或位姿对齐失败而失效；叠加的几何残差是否带来可解释的增益。

> 备注：若想探讨"比 PASDF 更强的形状先验是否进一步提升"，可在路线 A 完成后，用 3DShape2VecSet/VecSetX 的 encoder 替换或增强 SDF 表征作为研究性补充（非必做）。其改造思路（正常 latent、重建/补全残差、latent 分布距离）保留如下，供有余力时参考：
>
> - 输入适配：把数据统一为 point cloud / surface samples / occupancy 或 SDF 查询点。
> - 正常训练：只用正常样本优化 autoencoder 或加载预训练 encoder 后少量 fine-tune。
> - 点级投影：查询重建表面最近距离、局部 SDF 绝对值、法向/曲率差异。
> - 对象级聚合：top-k pooling。

### 6.4 稳健创新模块：曲率/法向感知伪异常生成

伪异常生成的目的是在只有正常样本的情况下，为模型构造“可学习的异常区域”。推荐使用以下轻量策略：

1. 对每个点估计法向。使用 kNN 局部 PCA，取最小特征值对应方向为法向。
2. 计算多尺度曲率。对 k = 16、32、64 的邻域分别计算协方差特征值，定义曲率为最小特征值除以三个特征值之和。
3. 选择异常候选区域。既选择高曲率区域，也选择部分低曲率平滑区域，避免模型只学到“高曲率 = 异常”的简单规则。
4. 沿法向扰动。对局部 patch 做凸起或凹陷变形，扰动幅度随到 patch 中心距离衰减。
5. 构造裂纹和缺失。对细长邻域做点删除、局部拉开或局部压缩，模拟 crack、hole、broken。
6. 保存伪标签。记录被扰动点和邻域边界点，供训练分类头或加权损失使用。

该模块的优点是实现独立，不要求绑定某个 repo。它可以挂在 PO3AD/CASL 的数据增强阶段，也可以用于 Point-MAE/Point-BERT fine-tuning；若使用 3DShape2VecSet，则可作为正常形状先验是否会“修复伪异常”的验证数据。

### 6.5 统一评分模块：多尺度几何提示与 top-k 聚合

推理阶段不只依赖单一重建误差，而是根据底座输出融合多种几何差异：

- 坐标残差：输入点与重建/修复点的欧氏距离。
- 隐式场残差：输入点在 SDF/occupancy field 中的异常程度，或输入点到零水平面的距离。
- latent 残差：样本 latent 与正常样本 latent 分布的 Mahalanobis distance、kNN distance 或 cosine distance。
- 法向残差：输入法向与重建点云法向的夹角变化。
- 曲率残差：输入曲率与重建点云曲率在多尺度邻域下的差异。
- 局部一致性：邻域内异常分数的平滑一致性，用于减少孤立噪声点。

点级异常分数可以写成：

```text
s_i = w_xyz * d_xyz(i) + w_sdf * d_sdf(i) + w_z * d_latent(i) + w_n * d_normal(i) + w_c * d_curvature(i) + w_m * d_multiscale(i)
```

对象级分数使用 top-k pooling，而不是简单最大值。建议取异常分数最高的 1%、3%、5% 点分别作为超参数候选，用验证集或固定协议确定。

### 6.6 可选零样本扩展

若主实验提前完成，可以做一个轻量零样本定性实验：

- 使用 PointAD 或 BTP 思路，准备正常/异常文本提示，例如“normal smooth surface”“defective cracked surface”。
- 对 3D 点云渲染多视角图像，或使用开源点云语言模型提取 patch embedding。
- 与本项目几何异常热力图对比，观察语义提示是否能帮助跨类别缺陷识别。

该扩展只建议做定性展示，不作为主指标来源。原因是零样本方法依赖预训练模型、渲染视角和文本 prompt，20-30 天内较难完成严格复现。

## 7. 实验设计

### 7.1 数据划分与预处理

Anomaly-ShapeNet：

- 遵循官方 train/test 目录和官方 benchmark 协议。
- 主实验使用官方 40 类；扩展 10 类作为可选。
- 点数根据底座需求设置：AD 专用方法可使用默认点数；3DShape2VecSet/VecSet 类方法需要额外记录 surface samples、occupancy/SDF 查询点数和重建点数；Point-MAE/Point-BERT 类方法记录 patch 数与采样点数。
- 归一化策略、采样策略、法向估计 k 值必须写入实验配置。

Real3D-AD：

- 第一阶段选择 2-4 个类别，验证数据读取和推理。
- 第二阶段扩展到 6-12 个类别。
- 高点数样本先使用 voxel downsample 或 FPS 采样，保留原始点数用于速度/内存分析。

MiniShift / MVTec 3D-AD：

- 只做压力测试或定性讨论。
- MiniShift 子集重点观察 50 万点高分辨率下下采样是否丢失小缺陷。
- MVTec 3D-AD 适合与零样本或多视角渲染方法做背景比较。

### 7.2 评价指标

对象级：

- O-AUROC 或 I-AUC：衡量整件物体是否异常。
- O-AUPR 或 I-AP：类别不平衡时更有参考价值。
- Per-category mean：按类别平均，避免大类别主导结果。

点级：

- P-AUROC：衡量点级异常定位排序质量。
- P-AUPR：异常点比例很低时更敏感。
- PRO 或官方点级指标：若官方 benchmark 提供则优先使用。

效率：

- 单样本推理时间。
- 显存峰值。
- 输入点数与耗时关系。
- 是否需要逐类别训练。

注意：不同论文对 Anomaly-ShapeNet 的指标命名和官方脚本口径可能不完全一致。报告中必须说明采用的指标脚本来源，不能把不同口径的数值直接当作同一指标比较。

### 7.3 主实验矩阵

> 锚点说明：E1 复现 PASDF 官方权重作为主力 SOTA 锚点，并尽量加跑 PO3AD 作为第二锚点；目标是先把对照值"对齐到论文报告水平"（PASDF O-AUROC≈90.0、PO3AD≈83.9），再叠加增强。

| 实验编号 | 数据集 | 方法 | 目标 |
|---|---|---|---|
| E0 | Anomaly-ShapeNet 子集（1-2 类） | PASDF 官方权重直接评估 | 打通环境，确认能复现到接近论文值（先做评估，不训练） |
| E1 | Anomaly-ShapeNet 40 类 | PASDF（官方权重/重训）+ PO3AD（对照锚点） | 建立 SOTA 锚点，得到与论文可比的 O/P-AUROC |
| E2 | Anomaly-ShapeNet 40 类 | PASDF + 位姿对齐质量分析 | 验证 PAM 对齐质量与各类别/异常类型的关系 |
| E3 | Anomaly-ShapeNet 40 类 | + 法向残差 | 验证法向残差对点级定位的增益 |
| E4 | Anomaly-ShapeNet 40 类 | + 多尺度曲率残差 | 验证曲率残差对 crack/hole 等局部异常的增益 |
| E5 | Anomaly-ShapeNet 40 类 | + 多尺度 top-k 聚合 + 局部一致性 | 验证评分聚合对细小缺陷与对象级检测的增益 |
| E6 | Real3D-AD 选定类别 | PASDF vs full method | 验证真实点云泛化（对照 PASDF 论文 80.2） |
| E7 | MiniShift / MVTec 子集 | full method 或只推理 | 压力测试和失败分析 |

### 7.4 消融实验

> 以 PASDF 为固定 backbone，逐项叠加本项目的几何增强；A0 为 SOTA 对照锚点。

| 配置 | backbone | 位姿对齐(PAM) | SDF 残差 | 法向残差 | 多尺度曲率残差 | top-k+一致性聚合 | 目的 |
|---|---|---|---|---|---|---|---|
| A0 | PO3AD（对照锚点） | — | — | — | — | — | 建立 SOTA 锚点 |
| A1 | PASDF | 有 | 有 | 无 | 无 | 简单 max | 复现 PASDF 原始能力 |
| A2 | PASDF | 有 | 有 | 有 | 无 | 简单 max | 看法向残差增益 |
| A3 | PASDF | 有 | 有 | 有 | 有 | 简单 max | 看曲率残差增益 |
| A4 | PASDF | 有 | 有 | 有 | 有 | top-k+一致性 | 完整方法 |
| A5(消融) | PASDF | **关闭** | 有 | 有 | 有 | top-k+一致性 | 验证位姿对齐的必要性（预期显著下降） |
| A6 | A4 配置 | 有 | 有 | 有 | 有 | top-k+一致性 | 跨数据集（Real3D-AD）验证 |

说明：A5 特意关闭位姿对齐，用来量化"PAM 对齐对最终指标的贡献"，这本身就是一个有价值的分析结论（呼应 §4.0 结论 2）。

建议每个配置先在 3-5 个代表类别上跑小实验，确认趋势后再扩展全类别。代表类别应覆盖平滑表面、复杂曲面、细长结构和多孔结构。

### 7.5 可视化与分析

报告至少包含以下图表：

- 点级异常热力图：输入点云按异常分数着色。
- GT overlay：预测热力图与官方点级标签叠加。
- per-category 结果表：按类别列出对象级和点级指标。
- defect-type 分析：按 bulge、concavity、crack、hole、broken 等类型分析。
- 失败案例：至少 3 个，说明失败原因是采样、姿态、局部平滑、曲率混淆还是真实缺陷不明显。
- 速度/显存表：记录输入点数、batch size、推理时间和显存。

## 8. 算力与工程可行性

**运行环境（已确定）**：所有训练/评估在**远程 Linux 服务器**进行，可起 **4 × RTX 4090 48G**。本地 Windows 仅用于开发、可视化和文档。这一点很关键——PASDF 的 `install.sh` 检测到非 Linux 会直接退出，PO3AD 依赖的 MinkowskiEngine 在 Windows 上几乎无法编译；**两者都必须在 Linux 上跑，而我们正好有 Linux 服务器，故环境不再是阻塞项。**

**主力/对照方法环境依赖（已逐项联网核实）：**

| 方法 | Python | 框架 | 关键依赖 | MinkowskiEngine | 预训练权重 | 备注 |
|---|---|---|---|---|---|---|
| **PASDF（主力）** | 3.10 | PyTorch 1.11.0 + CUDA 11.3 | **PyTorch3D 0.7.4**、point-cloud-utils、trimesh、scikit-image | **不需要** | **官方提供**（Google Drive，含权重 + 预处理 SDF 样本，可跳过训练直接评估） | `conda create -n PASDF python=3.10 && bash install.sh PASDF`；仅 Linux；Anomaly-ShapeNet 输入下采样到 **16384 点**；每类最优 `voxel_size` 见 `config_files/voxel_sizes.yaml`（默认 0.03） |
| PO3AD（对照锚点） | 3.8 | PyTorch 1.9.0 + CUDA 11.1 | **MinkowskiEngine**、openblas | **需要** | 官方提供（Google Drive checkpoints） | 主干为 Point Transformer V3；MinkowskiEngine 安装是主要风险，建议预留半天并备 Docker 方案 |
| Point-MAE（保底） | 3.x | PyTorch | pointnet2_ops、KNN_CUDA 等 CUDA 扩展 | 不需要 | 官方提供预训练 | 编译 CUDA 扩展需匹配 torch/CUDA 版本 |

> 重点：**PASDF 不需要从头复现**——官方代码完整（`Train/`、`Test/`、`scripts/`）且提供预训练权重与预处理 SDF 样本，第一步可"下载权重→直接评估"复现到接近 90.0，再决定是否重训与增强。

**4×4090 48G 资源分配建议：**

- 4 卡的最佳用法不是分布式训练单个模型，而是**按类别/配置并行**：把 40 类或 A0-A6 消融配置切分到 4 张卡同时跑，最大化吞吐。
- GPU0：PASDF 主力复现与几何增强消融（A1-A5）。
- GPU1：PO3AD 对照锚点（A0）+ Point-MAE 保底路线。
- GPU2：Real3D-AD 下采样、推理与跨数据集验证（E6）。
- GPU3：可视化批处理、MiniShift/MVTec 子集压力测试（E7）、以及 ablation 重跑。
- 48G 显存对 Anomaly-ShapeNet（16384 点）非常宽裕，可显著增大 batch 或并行多类别。

工程注意事项：

- 第 1-2 天打通 PASDF 环境（Linux + py3.10 + PyTorch3D），先跑"下载权重→评估"验证可复现。PO3AD 的 MinkowskiEngine 单独排期，装不上不影响主力。
- 数据集下载：Anomaly-ShapeNet 走 Hugging Face / 百度网盘（提取码 `case`），Real3D-AD 走 Google Drive / 百度网盘；PASDF 的预训练权重 + 预处理 SDF 在其 README 的 Google Drive 文件夹。第 1 天即启动下载。
- 注意 PASDF 默认把点云下采样到 16384 点；若课程实发数据是高密度版（见 §3.1 待核实项），需确认重采样到 16384 是否丢失小缺陷，必要时调高分辨率并记录显存/耗时。
- 保存所有配置、随机种子、类别列表、`voxel_size`、checkpoint 路径和日志，避免后期无法复现表格。
- 至少预留 200-300GB 磁盘空间给数据、checkpoint、预处理 SDF 样本、重建 mesh 与可视化。

## 9. 五人分工

| 角色 | 负责人标签 | 主要职责 | 交付物 |
|---|---|---|---|
| A | 文献与报告负责人 | 梳理论文、维护引用、设计报告结构、统筹最终文档 | 文献综述、方法图、最终报告 |
| B | 数据与指标负责人 | 下载数据集、整理目录、预处理、实现/核对指标脚本 | 数据说明、预处理脚本、指标验证 |
| C | 开源底座负责人 | 跑通 PASDF（主力，含权重评估与重训）、PO3AD（对照）、Point-MAE（保底）等 repo 的 Linux 环境 | 底座可行性表、环境记录、checkpoint |
| D | 方法改造负责人 | 把选定底座改造成 anomaly scorer，实现重建/SDF/latent/几何残差和消融实验 | 改造模块、消融结果、参数分析 |
| E | 可视化与答辩负责人 | 制作热力图、GT overlay、PPT、demo 和失败案例 | 可视化图、PPT、演示脚本 |

协作方式：

- 每天同步一次实验状态：已完成类别、失败类别、显存/环境问题、指标变化。
- 每个实验必须记录命令、配置、日志路径和结果表。
- A 负责最终合并，但数据、代码和图表不能只存在个人电脑上，必须统一归档。

## 10. 20-30 天排期

### 第 1-4 天：环境、数据、PASDF 复现起步

- A 完成核心论文速读和引用表（PASDF、PO3AD、IMRNet、R3D-AD）。
- B 下载 Anomaly-ShapeNet（HF/百度网盘 `case`）+ PASDF 官方权重与预处理 SDF 样本（Google Drive），建数据目录与读取脚本；**用脚本统计课程实发数据真实点数/类别/样本数，核实 §3.1 待定项**。
- C 在 Linux 服务器搭好 PASDF 环境（py3.10/torch1.11/cu11.3/PyTorch3D），跑通"下载权重→`AD_test.py` 评估"，复现 1-2 类结果。
- D 实现法向、多尺度曲率、点到表面距离的小脚本，在少量点云上检查可视化。
- E 搭建 Open3D / matplotlib / PPT 图表模板，建好 GitHub 仓库与协作规范（见 SOP）。

验收点：PASDF 能在至少 1 类上复现到接近论文值；数据可读、法向/曲率可视化正常；真实点数分布已统计。

### 第 5-10 天：SOTA 锚点对齐

- C 把 PASDF 评估扩展到 40 类（用官方权重），得到全量 O/P-AUROC，与论文逐类对照。
- C 并行打通 PO3AD（MinkowskiEngine）作对照锚点；装不上则用论文报告值，不阻塞。
- B 核对官方指标脚本与类别列表，固化统一评估入口。
- D 完成第一版几何残差模块（法向残差 / 曲率残差），与 PASDF SDF 残差对接。
- E 生成第一版点级 heatmap、GT overlay 与 SDF 修复 mesh 展示。
- A 整理方法选择理由与初步结果表。

验收点：PASDF 40 类锚点结果可复现；至少一个对照锚点可比；几何残差模块能产出 heatmap。

### 第 11-17 天：几何增强与消融

- D 完成法向/曲率残差、多尺度 top-k + 局部一致性聚合模块。
- C/D 在 3-5 个代表类别上跑 A0-A5 消融（含"关闭位姿对齐"对照），确认趋势后扩到 40 类。
- B 检查 16384 点重采样 / 不同采样点数对指标的影响。
- E 整理消融图和失败案例（分缺陷类型 / 分类别）。
- A 更新方法章节和实验设计。

验收点：消融表中至少一项几何增强带来可解释收益；位姿对齐贡献被量化；若无收益，说明原因（shape prior 过强 / 投影失败 / 参数）。

### 第 18-23 天：多数据集验证与压力测试

- B 下载 Real3D-AD 选定类别，完成下采样和目录适配。
- C/D 在 Real3D-AD 上跑 PASDF 与 full method 推理（对照论文 80.2）。
- E 输出真实点云 heatmap 和类别失败案例。
- 若进度允许，尝试 MiniShift 或 MVTec 3D-AD 子集。

验收点：至少一个次数据集有可展示结果，报告能讨论合成→真实的泛化差距。

### 第 24-30 天：报告、PPT 和归档

- A 完成最终报告初稿和引用核对。
- E 完成答辩 PPT、demo（含 SDF 修复）和图表排版。
- B/C/D 补全实验表、速度/显存表、脚本说明与 README。
- 全组检查结果可复现，按 SOP 整理 GitHub 仓库与发布 tag。

验收点：报告、PPT、可视化、实验表、代码说明和备份结果全部完成。

若总周期只有 20 天，压缩方案：第 1-3 天环境+数据+PASDF 权重评估复现，第 4-8 天 40 类锚点+对照+几何残差模块，第 9-14 天增强与消融，第 15-17 天 Real3D-AD 抽样验证，第 18-20 天报告和答辩。MiniShift、MulSen-AD 和零样本扩展只写入未来工作。

## 11. 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| 底座路线过度发散 | 项目变成调研堆砌，无法落地 | 第 4 天设决策门，只保留 1 条主底座和 1 条保底底座 |
| PASDF 复现/环境受阻（SDF 训练、位姿对齐、点级投影） | 主力路线无法按期完成 | 优先用官方代码与预训练设置复现单类别；若打不通，切换 Point-MAE/Point-BERT 保底路线，并把 PASDF 失败原因写入报告 |
| 依赖安装失败 | 候选 repo 无法运行 | 记录失败原因；准备 AD 专用 repo、Point-MAE/Point-BERT、几何 baseline 三类 fallback |
| MinkowskiEngine 安装失败 | 仅影响 PO3AD 对照锚点（主力 PASDF 不依赖它） | 在 Linux 服务器上按官方步骤装；备 Docker 方案；若仍失败，PO3AD 改用论文报告值作对照，不阻塞主力 |
| 数据集下载慢或失效 | 影响实验开始时间 | 同时尝试 Hugging Face、百度网盘、Google Drive；第 1 天就启动下载 |
| 指标口径不一致 | 对比表不可信 | 统一使用官方脚本；文献数值只标“论文报告值”，不与自跑值混成同一列 |
| 强 encoder/decoder 不能直接定位缺陷 | 只得到全局重建，缺少点级 heatmap | 增加最近表面距离、SDF 查询、局部法向/曲率投影；必要时只把它作为对象级分支 |
| 创新模块不提升指标 | 项目创新不足 | 保留消融和失败分析；把贡献定位为底座适配和可解释几何增强，而非保证 SOTA |
| Real3D-AD 点数过高 | 显存和耗时增加 | 使用 voxel downsample / FPS；报告不同点数下性能和速度 |
| MiniShift 太大 | 无法全量实验 | 只做子集压力测试或文献讨论，不纳入最低交付 |
| 团队并行混乱 | 结果难以复现 | 建立统一实验记录表，所有命令、配置、日志和结果必须归档 |

## 12. 预期报告结构

最终课程设计报告建议采用以下结构：

1. 任务背景：3D 点云缺陷检测的工业意义和无监督设定。
2. 数据集调研：Anomaly-ShapeNet、Real3D-AD、MVTec 3D-AD、MiniShift、MulSen-AD。
3. 相关工作：IMRNet、PO3AD、CASL、R3D-AD、MC3D-AD、PASDF、3DShape2VecSet、Point-MAE、Point-BERT、Uni3D/OpenShape/ULIP、PointAD/BTP。
4. 底座选择：候选 repo 对比、运行情况、为何选主线、为何放弃其他路线。
5. 方法设计：底座适配、正常形状先验、重建/SDF/latent score、曲率/法向特征、多尺度评分。
6. 实验设置：数据划分、指标、硬件、参数。
7. 实验结果：主结果、消融、跨数据集验证、速度和显存。
8. 可视化分析：热力图、GT overlay、缺陷类型和失败案例。
9. 总结与展望：项目完成度、局限和未来多传感器/零样本方向。

## 13. 已验证参考资料

| 编号 | 方向 | 资料 | 可验证来源 |
|---|---|---|---|
| R1 | Anomaly-ShapeNet / IMRNet | Li et al., Towards Scalable 3D Anomaly Detection and Localization, CVPR 2024 | [CVPR Open Access](https://openaccess.thecvf.com/content/CVPR2024/html/Li_Towards_Scalable_3D_Anomaly_Detection_and_Localization_A_Benchmark_via_CVPR_2024_paper.html), [arXiv:2311.14897](https://arxiv.org/abs/2311.14897), [GitHub](https://github.com/Chopper-233/Anomaly-ShapeNet), [Hugging Face](https://huggingface.co/datasets/Chopper233/Anomaly-ShapeNet) |
| R2 | Real3D-AD / Reg3D-AD | Liu et al., Real3D-AD: A Dataset of Point Cloud Anomaly Detection, NeurIPS 2023 Datasets & Benchmarks | [NeurIPS Proceedings](https://proceedings.neurips.cc/paper_files/paper/2023/hash/611b896d447df43c898062358df4c114-Abstract-Datasets_and_Benchmarks.html), [arXiv:2309.13226](https://arxiv.org/abs/2309.13226), [GitHub](https://github.com/M-3LAB/Real3D-AD) |
| R3 | MVTec 3D-AD | Bergmann et al., The MVTec 3D-AD Dataset, VISAPP 2022 | [arXiv:2112.09045](https://arxiv.org/abs/2112.09045), [SciTePress DOI page](https://www.scitepress.org/Link.aspx?doi=10.5220%2F0010865000003124) |
| R4 | PO3AD | Ye et al., Predicting Point Offsets toward Better 3D Point Cloud Anomaly Detection, CVPR 2025 | [CVPR Open Access](https://openaccess.thecvf.com/content/CVPR2025/html/Ye_PO3AD_Predicting_Point_Offsets_toward_Better_3D_Point_Cloud_Anomaly_CVPR_2025_paper.html), [arXiv:2412.12617](https://arxiv.org/abs/2412.12617), [GitHub](https://github.com/yjnanan/PO3AD) |
| R5 | CASL | Zha et al., Curvature-Augmented Self-supervised Learning for 3D Anomaly Detection, AAAI 2026 | [arXiv:2511.12909](https://arxiv.org/abs/2511.12909), [GitHub](https://github.com/zyh16143998882/CASL) |
| R6 | BTP | Li et al., Back to Point: Exploring Point-Language Models for Zero-Shot 3D Anomaly Detection, CVPR 2026 | [CVPR 2026 Open Access list](https://openaccess.thecvf.com/CVPR2026?day=2026-06-05), [arXiv:2603.21511](https://arxiv.org/abs/2603.21511), [GitHub](https://github.com/wistful-8029/BTP-3DAD) |
| R7 | PASDF | Zheng et al., Bridging 3D Anomaly Localization and Repair via High-Quality Continuous Geometric Representation, ICCV 2025 | [ICCV Open Access](https://openaccess.thecvf.com/content/ICCV2025/html/Zheng_Bridging_3D_Anomaly_Localization_and_Repair_via_High-Quality_Continuous_Geometric_ICCV_2025_paper.html), [arXiv:2505.24431](https://arxiv.org/abs/2505.24431), [GitHub](https://github.com/ZZZBBBZZZ/PASDF) |
| R8 | R3D-AD | Zhou et al., Reconstruction via Diffusion for 3D Anomaly Detection, ECCV 2024 | [ECCV page](https://eccv.ecva.net/virtual/2024/poster/806), [arXiv:2407.10862](https://arxiv.org/abs/2407.10862) |
| R9 | MC3D-AD | Cheng et al., A Unified Geometry-aware Reconstruction Model for Multi-category 3D Anomaly Detection, IJCAI 2025 | [IJCAI Proceedings](https://www.ijcai.org/proceedings/2025/94), [arXiv:2505.01969](https://arxiv.org/abs/2505.01969), [GitHub](https://github.com/iCAN-SZU/MC3D-AD) |
| R10 | PointAD | Zhou et al., Comprehending 3D Anomalies from Points and Pixels for Zero-shot 3D Anomaly Detection, NeurIPS 2024 | [NeurIPS Proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/9a263e235f6d1521d13a8531c7974951-Abstract-Conference.html), [arXiv:2410.00320](https://arxiv.org/abs/2410.00320), [GitHub](https://github.com/zqhang/PointAD) |
| R11 | PointAD+ | Zhou et al., Learning Hierarchical Representations for Zero-shot 3D Anomaly Detection | [arXiv:2509.03277](https://arxiv.org/abs/2509.03277) |
| R12 | MiniShift / Simple3D | Cheng et al., Towards High-Resolution 3D Anomaly Detection, AAAI 2026 | [arXiv:2507.07435](https://arxiv.org/abs/2507.07435), [GitHub](https://github.com/hustCYQ/MiniShift-Simple3D), [Hugging Face](https://huggingface.co/datasets/ChengYuQi99/MiniShift) |
| R13 | MulSen-AD | Li et al., Multi-Sensor Object Anomaly Detection, CVPR 2025 | [CVPR Open Access](https://openaccess.thecvf.com/content/CVPR2025/html/Li_Multi-Sensor_Object_Anomaly_Detection_Unifying_Appearance_Geometry_and_Internal_Properties_CVPR_2025_paper.html), [GitHub](https://github.com/ZZZBBBZZZ/MulSen-AD) |
| R14 | Point-MAE | Pang et al., Masked Autoencoders for Point Cloud Self-supervised Learning | [arXiv:2203.06604](https://arxiv.org/abs/2203.06604), [GitHub](https://github.com/Pang-Yatian/Point-MAE) |
| R15 | Point-BERT | Yu et al., Pre-training 3D Point Cloud Transformers with Masked Point Modeling, CVPR 2022 | [arXiv:2111.14819](https://arxiv.org/abs/2111.14819), [GitHub](https://github.com/lulutang0608/Point-BERT) |
| R16 | Point Transformer | Zhao et al., Point Transformer | [arXiv:2012.09164](https://arxiv.org/abs/2012.09164) |
| R17 | 3DShape2VecSet | Zhang et al., A 3D Shape Representation for Neural Fields and Generative Diffusion Models, SIGGRAPH / ACM TOG 2023 | [arXiv:2301.11445](https://arxiv.org/abs/2301.11445), [Crossref DOI record](https://api.crossref.org/works/10.1145/3592442), [GitHub](https://github.com/1zb/3DShape2VecSet) |
| R18 | VecSetX | 3DShape2VecSet 作者维护的 VecSet 系列工程框架 | [GitHub](https://github.com/1zb/VecSetX), [Hugging Face](https://huggingface.co/Zbalpha/VecSetX) |
| R19 | Uni3D | Zhou et al., Exploring Unified 3D Representation at Scale, ICLR 2024 Spotlight | [arXiv:2310.06773](https://arxiv.org/abs/2310.06773), [GitHub](https://github.com/baaivision/Uni3D) |
| R20 | OpenShape | Liu et al., Scaling Up 3D Shape Representation Towards Open-World Understanding, NeurIPS 2023 | [arXiv:2305.10764](https://arxiv.org/abs/2305.10764), [GitHub](https://github.com/Colin97/OpenShape_code) |
| R21 | ULIP | Xue et al., Learning a Unified Representation of Language, Images, and Point Clouds for 3D Understanding, CVPR 2023 | [arXiv:2212.05171](https://arxiv.org/abs/2212.05171), [GitHub](https://github.com/salesforce/ULIP) |
| R22 | PointNeXt | Qian et al., Revisiting PointNet++ with Improved Training and Scaling Strategies, NeurIPS 2022 | [arXiv:2206.04670](https://arxiv.org/abs/2206.04670), [GitHub](https://github.com/guochengqian/PointNeXt) |
| R23 | PointMLP | Ma et al., Rethinking Network Design and Local Geometry in Point Cloud, ICLR 2022 | [arXiv:2202.07123](https://arxiv.org/abs/2202.07123), [GitHub](https://github.com/ma-xu/pointMLP-pytorch) |
| R24 | DeepSDF | Park et al., Learning Continuous Signed Distance Functions for Shape Representation | [arXiv:1901.05103](https://arxiv.org/abs/1901.05103), [GitHub](https://github.com/facebookresearch/DeepSDF) |
| R25 | Occupancy Networks | Mescheder et al., Learning 3D Reconstruction in Function Space | [arXiv:1812.03828](https://arxiv.org/abs/1812.03828), [GitHub](https://github.com/autonomousvision/occupancy_networks) |
| R26 | Point-E | Nichol et al., A System for Generating 3D Point Clouds from Complex Prompts | [arXiv:2212.08751](https://arxiv.org/abs/2212.08751), [GitHub](https://github.com/openai/point-e) |

## 14. 结论

本项目应把目标控制在“任务锚点清晰 + 开源底座二次开发 + 充分分析”。Anomaly-ShapeNet 是必须完整完成的主线，Real3D-AD 用来证明真实数据泛化，MiniShift/MVTec/MulSen-AD 作为扩展背景或压力测试。技术上，不建议从零设计复杂网络，也不应局限于复现 PO3AD/CASL；更有研究味道的路线是选择一个强 3D 表征底座，例如 3DShape2VecSet、Point-MAE/Point-BERT 或 VecSetX，把它改造成可输出点级 heatmap 的缺陷检测器。

只要能交付完整的主基准实验、清晰的热力图、规范的指标表和可信的失败分析，即使最终指标没有超过最新论文，课程设计仍然成立。真正重要的是让报告说明：我们为什么选择这个开源底座、它原本解决什么问题、为了缺陷检测改了什么、哪些分数来源有效、哪些情况下失败，以及这些失败说明了 3D 形状先验和工业缺陷定位之间的什么差距。
