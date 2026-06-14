"""Build a self-contained Markdown delivery pack with local SVG assets."""

# ruff: noqa: E501

from __future__ import annotations

import csv
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACK_ROOT.parents[3]
ASSET_ROOT = PACK_ROOT / "assets"


@dataclass(frozen=True)
class Asset:
    source: str
    target: str
    title: str
    caption: str


ASSETS: tuple[Asset, ...] = (
    Asset(
        source="experiments/p2_smoke/anomaly_shapenet_ashtray0_gt_normals.svg",
        target="assets/01_data/ashtray0_gt_normals.svg",
        title="Anomaly-ShapeNet 数据 smoke：ashtray0 点云、法向与 GT",
        caption=(
            "P2 数据准备阶段的可视化 smoke。该图用于说明数据加载、法向估计和 "
            "GT 点级标签读取链路已经打通。"
        ),
    ),
    Asset(
        source="experiments/P4_geometry_smoke/config_svgs/A4_pasdf_geom_full/cap3_cap3_bending0.svg",
        target="assets/02_p4_geometry/a4_cap3_bending0.svg",
        title="P4 A4 几何 smoke：cap3 bending anomaly",
        caption=(
            "A4 加大 normal/curvature 权重后，异常样本 object score 并没有稳定压过 "
            "positive control，说明 naive geometry 不适合直接扩 40 类主表。"
        ),
    ),
    Asset(
        source="experiments/P4_geometry_smoke/config_svgs/A4_pasdf_geom_full/cap3_cap3_positive0.svg",
        target="assets/02_p4_geometry/a4_cap3_positive0.svg",
        title="P4 A4 几何 smoke：cap3 positive control",
        caption=("positive control 在几何残差下同样容易被抬高，是 P4 收口为负结果的主要证据之一。"),
    ),
    Asset(
        source="experiments/P5_case_study/template_overlay/cap3/cap3_positive9_template_overlay.svg",
        target="assets/03_cap3_overlay/cap3_positive9_template_overlay.svg",
        title="cap3_positive9 sample/template overlay",
        caption=(
            "红点为 registered sample，蓝点为 template。该正常样本 object score 高，"
            "overlay 显示局部结构与 template 不重合，支持 template mismatch 解释。"
        ),
    ),
    Asset(
        source="experiments/P5_case_study/template_overlay/cap3/cap3_positive7_template_overlay.svg",
        target="assets/03_cap3_overlay/cap3_positive7_template_overlay.svg",
        title="cap3_positive7 sample/template overlay",
        caption=(
            "cap3_positive7 与 positive9 一样表现出局部错位，说明 cap3 false positive "
            "不是单个孤例。"
        ),
    ),
    Asset(
        source="experiments/P5_case_study/template_overlay/cap3/cap3_positive10_template_overlay.svg",
        target="assets/03_cap3_overlay/cap3_positive10_template_overlay.svg",
        title="cap3_positive10 sample/template overlay",
        caption=(
            "cap3_positive10 的 mean score 低但 object score 高，说明少量 top-k 高分点足以"
            "拉高对象级分数。"
        ),
    ),
    Asset(
        source="experiments/P5_case_study/pasdf_scores/cap3/cap3_positive9_pasdf_score.svg",
        target="assets/04_pasdf_heatmap/cap3_positive9_pasdf_score.svg",
        title="cap3_positive9 PASDF heatmap",
        caption=("正常样本的局部 PASDF 高分区域是 cap3 false positive 的直接可视化证据。"),
    ),
    Asset(
        source="experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken2_pasdf_vs_geometry.svg",
        target="assets/05_tap1_comparison/tap1_broken2_pasdf_vs_geometry.svg",
        title="tap1_broken2 PASDF vs geometry",
        caption=(
            "左侧 PASDF 分数较低但 GT 内均值高于背景；右侧 geometry residual 视觉上更红，"
            "但后续 P6 region metrics 显示 PASDF top-k 更贴近 GT。"
        ),
    ),
    Asset(
        source="experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_broken3_pasdf_vs_geometry.svg",
        target="assets/05_tap1_comparison/tap1_broken3_pasdf_vs_geometry.svg",
        title="tap1_broken3 PASDF vs geometry",
        caption=(
            "tap1 broken 类样本重复出现 PASDF 低幅度响应和 geometry 高视觉响应，"
            "触发了后续 positive-aware 诊断。"
        ),
    ),
    Asset(
        source="experiments/P5_case_study/pasdf_vs_geometry/tap1/tap1_hole0_pasdf_vs_geometry.svg",
        target="assets/05_tap1_comparison/tap1_hole0_pasdf_vs_geometry.svg",
        title="tap1_hole0 PASDF vs geometry",
        caption=(
            "hole0 说明 geometry residual 对局部孔洞也有视觉响应，但不能直接等价为对象级提升。"
        ),
    ),
    Asset(
        source="experiments/P5_case_study/pasdf_scores/helmet1/helmet1_concavity4_pasdf_score.svg",
        target="assets/06_helmet1/helmet1_concavity4_pasdf_score.svg",
        title="helmet1_concavity4 PASDF heatmap",
        caption=(
            "helmet1 是点级定位弱和 positive boundary 混淆代表类；该图用于最终报告中的"
            "人工复查入口。"
        ),
    ),
    Asset(
        source="experiments/P6_alpha_sweep/tap1_hybrid_scores/tap1/tap1_broken2_hybrid.svg",
        target="assets/07_p6_hybrid/tap1_broken2_hybrid.svg",
        title="P6 tap1_broken2 hybrid score",
        caption=(
            "hybrid 提升了 anomaly 样本局部分离，但 positive-aware alpha sweep 发现 positive "
            "object score 同步升高。"
        ),
    ),
    Asset(
        source="experiments/P6_alpha_sweep/tap1_hybrid_scores/tap1/tap1_positive0_hybrid.svg",
        target="assets/07_p6_hybrid/tap1_positive0_hybrid.svg",
        title="P6 tap1_positive0 hybrid score",
        caption=(
            "positive0 的 hybrid object score 被抬高，是拒绝 naive additive fusion 的关键反例。"
        ),
    ),
)

CSV_ASSETS: tuple[tuple[str, str], ...] = (
    (
        "experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv",
        "assets/csv/p3_pasdf_40cls_evaluation_results.csv",
    ),
    (
        "docs/document/stage_record/2026-06-14_p6_delivery_evidence_index.csv",
        "assets/csv/p6_delivery_evidence_index.csv",
    ),
    (
        "docs/document/stage_record/2026-06-14_p6_failure_mode_closure.csv",
        "assets/csv/p6_failure_mode_closure.csv",
    ),
)


def main() -> None:
    _copy_assets()
    _write_readme()
    _write_project_report()
    _write_failure_analysis()
    _write_reproduction()
    _write_visual_gallery()
    _write_manifest()


def _copy_assets() -> None:
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    for asset in ASSETS:
        _copy_file(asset.source, asset.target)
    for source, target in CSV_ASSETS:
        _copy_file(source, target)


def _copy_file(source: str, target: str) -> None:
    src = REPO_ROOT / source
    dst = PACK_ROOT / target
    if not src.exists():
        raise FileNotFoundError(f"Missing source asset: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _write_readme() -> None:
    commit = _git("rev-parse", "--short", "HEAD")
    tag = _git("describe", "--tags", "--exact-match", default="未打 tag")
    lines = [
        "# 3D 点云异常检测交付包",
        "",
        "## 目录",
        "",
        "- [1. 这个文件夹是什么](#1-这个文件夹是什么)",
        "- [2. 推荐阅读顺序](#2-推荐阅读顺序)",
        "- [3. 最核心结论](#3-最核心结论)",
        "- [4. 文件结构](#4-文件结构)",
        "- [5. 转发注意事项](#5-转发注意事项)",
        "",
        "## 1. 这个文件夹是什么",
        "",
        "这是一个可直接转发给课程组、组员或评审者的阶段交付包。它把当前仓库中的"
        "核心文档、实验结论、关键图片和复现命令整理到同一个目录中，并把所有图片"
        "复制到本目录的 `assets/` 下，Markdown 中只使用相对路径。",
        "",
        f"- 当前 commit：`{commit}`",
        f"- 当前 tag：`{tag}`",
        "- 主基准：Anomaly-ShapeNet 40 类协议",
        "- 主方法：PASDF 官方权重复现 + P4-P6 failure analysis",
        "- 关键结论：PASDF baseline 达到论文级 object AUROC；naive geometry fusion 不进入主表。",
        "",
        "## 2. 推荐阅读顺序",
        "",
        "1. `01_project_report.md`：完整项目报告，适合快速理解全局。",
        "2. `02_experiment_and_failure_analysis.md`：实验结果、图像判读和失败模式。",
        "3. `03_reproduction_and_evidence.md`：复现命令、证据路径和质量门。",
        "4. `04_visual_gallery.md`：所有图片集中图册。",
        "5. `MANIFEST.md`：文件清单、来源和用途。",
        "",
        "## 3. 最核心结论",
        "",
        "- P3 PASDF 40 类复现：mean object AUROC=`0.900214149779`，"
        "mean pixel AUROC=`0.896009030694`。",
        "- P4 A2/A3/A4 naive geometry enhancement：作为负结果收口，不扩 40 类。",
        "- P5/P6 `cap3`：normal positive 样本被打高分，主要证据指向"
        " registration/template mismatch。",
        "- P5/P6 `tap1`：PASDF 有局部信号但 object boundary 偏软；"
        "geometry 只能作为诊断解释，不能直接 additive fusion。",
        "- P6 `helmet1`：点级定位弱和 positive boundary 混淆，需要作为最终报告中的局限案例。",
        "",
        "## 4. 文件结构",
        "",
        "```text",
        "2026-06-14_p6_delivery_pack/",
        "├── README.md",
        "├── 01_project_report.md",
        "├── 02_experiment_and_failure_analysis.md",
        "├── 03_reproduction_and_evidence.md",
        "├── 04_visual_gallery.md",
        "├── MANIFEST.md",
        "├── assets/",
        "│   ├── 01_data/",
        "│   ├── 02_p4_geometry/",
        "│   ├── 03_cap3_overlay/",
        "│   ├── 04_pasdf_heatmap/",
        "│   ├── 05_tap1_comparison/",
        "│   ├── 06_helmet1/",
        "│   ├── 07_p6_hybrid/",
        "│   └── csv/",
        "└── scripts/",
        "    └── build_delivery_pack.py",
        "```",
        "",
        "## 5. 转发注意事项",
        "",
        "- 转发时请整个文件夹一起发送，不要只发单个 Markdown，否则图片相对路径会失效。",
        "- 如果需要直接发压缩包，可以使用同级目录下的 `2026-06-14_p6_delivery_pack.zip`。",
        "- 本包不包含原始数据、模型权重、NPZ 点级分数或完整实验日志。",
        "- 大型实验产物仍保留在服务器 `experiments/` 和 `data/` 目录中，本包只复制轻量 SVG/CSV。",
        "",
    ]
    _write("README.md", lines)


def _write_project_report() -> None:
    lines = [
        "# 项目技术报告",
        "",
        "## 目录",
        "",
        "- [1. 项目背景](#1-项目背景)",
        "- [2. 任务与数据](#2-任务与数据)",
        "- [3. 方法路线](#3-方法路线)",
        "- [4. 阶段进展](#4-阶段进展)",
        "- [5. 核心结果](#5-核心结果)",
        "- [6. 关键图示](#6-关键图示)",
        "- [7. 结论与定位](#7-结论与定位)",
        "",
        "## 1. 项目背景",
        "",
        "本项目研究无监督 3D 点云异常检测。任务目标是在只使用正常样本或极少标注"
        "条件下，判断一个 3D 点云物体是否异常，并在点级别定位异常区域。相比 2D 图像，"
        "点云异常更关注几何结构、局部凹凸、断裂、孔洞、配准误差和采样密度变化。",
        "",
        "项目主线不是重新从零训练一个弱 baseline，而是先复现当前强方法 PASDF，"
        "再围绕其失败模式做系统性分析。这样能保证结论建立在强基线之上，避免把"
        "低质量复现误当成方法创新。",
        "",
        "## 2. 任务与数据",
        "",
        "- 主数据集：Anomaly-ShapeNet。",
        "- 协议：官方 40 类协议。",
        "- 输入：每个样本固定为 `16384` 点的点云。",
        "- 输出：对象级异常分数和点级异常 heatmap。",
        "- 主要指标：object AUROC、pixel AUROC。",
        "",
        "P2 数据准备阶段已经完成高密度课程包统计、固定点数版本生成、DataLoader "
        "和点云/法向/GT 可视化 smoke。",
        "",
        "![P2 数据 smoke](assets/01_data/ashtray0_gt_normals.svg)",
        "",
        "## 3. 方法路线",
        "",
        "项目采用 PASDF 作为主 backbone。PASDF 的核心思想是：先把测试点云对齐到"
        " canonical template，再用连续 SDF 学习正常形状表面，推理时以点到正常零水平面"
        "的偏离作为点级异常分数，并通过 top-k 聚合得到对象级分数。",
        "",
        "在 PASDF baseline 之上，我们尝试了三类扩展或诊断：",
        "",
        "1. P4：法向、曲率、距离 residual 的 naive geometry enhancement。",
        "2. P5：导出 PASDF per-point score，做 representative case study。",
        "3. P6：positive-aware alpha sweep、region explanation、top-k calibration 和 failure-mode closure。",
        "",
        "## 4. 阶段进展",
        "",
        "| 阶段 | 状态 | 主要产物 | 结论 |",
        "|---|---|---|---|",
        "| P0-P2 | 已完成 | 仓库、环境、数据、DataLoader、数据统计 | 可稳定进入 PASDF 复现 |",
        "| P3 | 已完成 | 40 类 PASDF baseline | object AUROC 达到论文级锚点 |",
        "| P4 | 已完成 | A2/A3/A4 geometry smoke | naive geometry 不扩主表 |",
        "| P5 | 已完成 | representative PASDF score export 与图文报告 | cap3/tap1 failure mode 分化明显 |",
        "| P6 | 已完成 | calibration、alpha sweep、failure closure、evidence pack | 进入最终报告/PPT/demo 打包 |",
        "",
        "## 5. 核心结果",
        "",
        "| 方法 | 协议 | mean object AUROC | mean pixel AUROC | 说明 |",
        "|---|---|---:|---:|---|",
        "| PASDF official weights | Anomaly-ShapeNet 40 类 | `0.900214149779` | `0.896009030694` | P3 baseline，作为后续所有分析锚点 |",
        "",
        "这个 object AUROC 与计划中的 PASDF 论文目标 `90.0%` 基本一致，说明主线复现已经达标。",
        "",
        "## 6. 关键图示",
        "",
        "### 6.1 P4 几何增强负结果",
        "",
        "下图展示 A4 几何增强在 `cap3` anomaly 与 positive control 上的对照。"
        "几何分数能产生局部响应，但 positive control 也容易被抬高，因此不适合作为"
        "未经约束的对象级增强。",
        "",
        "![A4 cap3 bending anomaly](assets/02_p4_geometry/a4_cap3_bending0.svg)",
        "",
        "![A4 cap3 positive control](assets/02_p4_geometry/a4_cap3_positive0.svg)",
        "",
        "### 6.2 P5/P6 cap3 false positive",
        "",
        "`cap3_positive9/7/10` 都是正常样本，但 PASDF object score 偏高。"
        "sample/template overlay 显示局部结构不重合，结合 residual overlap 统计，"
        "该类更适合解释为 registration/template mismatch。",
        "",
        "![cap3 positive9 overlay](assets/03_cap3_overlay/cap3_positive9_template_overlay.svg)",
        "",
        "![cap3 positive9 PASDF heatmap](assets/04_pasdf_heatmap/cap3_positive9_pasdf_score.svg)",
        "",
        "### 6.3 P5/P6 tap1 soft boundary",
        "",
        "`tap1_broken2/broken3/hole0` 的 PASDF 对 GT 区域有信号，但 object score 幅度低。"
        "geometry residual 视觉上更明显，不过 P6 region metrics 表明 PASDF top-k 更贴近 GT，"
        "因此不支持直接恢复 additive fusion。",
        "",
        "![tap1 broken2 comparison](assets/05_tap1_comparison/tap1_broken2_pasdf_vs_geometry.svg)",
        "",
        "![tap1 positive hybrid counterexample](assets/07_p6_hybrid/tap1_positive0_hybrid.svg)",
        "",
        "## 7. 结论与定位",
        "",
        "当前项目可以作为一个完整、可复查的课程设计交付：",
        "",
        "- 强 baseline 已复现到位。",
        "- 几何增强没有强行包装成正结果，而是按实验事实收口为负结果。",
        "- P5/P6 对代表失败类给出了可视化、定量和后续方向。",
        "- 最终报告应强调：项目贡献是强基线复现、失败模式分析、正负结果闭环和工程可复现，而不是声称一个未经验证的新 SOTA 方法。",
        "",
    ]
    _write("01_project_report.md", lines)


def _write_failure_analysis() -> None:
    lines = [
        "# 实验结果与失败模式分析",
        "",
        "## 目录",
        "",
        "- [1. 结果总览](#1-结果总览)",
        "- [2. P4 naive geometry 为什么关闭](#2-p4-naive-geometry-为什么关闭)",
        "- [3. cap3：registration/template false positive](#3-cap3registrationtemplate-false-positive)",
        "- [4. tap1：PASDF soft boundary 与 fusion 拒绝](#4-tap1pasdf-soft-boundary-与-fusion-拒绝)",
        "- [5. helmet1：点级定位弱](#5-helmet1点级定位弱)",
        "- [6. 最终 failure-mode closure](#6-最终-failure-mode-closure)",
        "",
        "## 1. 结果总览",
        "",
        "| 问题 | 结论 | 证据 |",
        "|---|---|---|",
        "| PASDF baseline 是否达标 | 达标 | 40 类 mean object AUROC=`0.900214149779` |",
        "| 几何 residual 是否能直接提升主表 | 当前不能 | P4 A2/A3/A4 positive control 同样高分 |",
        "| cap3 失败原因 | template/registration false positive | positive overlay 错位 + residual top-k overlap 高 |",
        "| tap1 是否恢复 additive fusion | 不恢复 | alpha sweep 全部 strict=False/soft=False |",
        "| helmet1 如何处理 | 报告中作为 localization weakness 局限案例 | calibration 和 closure 记录 |",
        "",
        "## 2. P4 naive geometry 为什么关闭",
        "",
        "P4 A2/A3/A4 尝试把 distance、normal、curvature residual 组合成几何异常分数。"
        "结果显示，几何分数能放大局部差异，但不能稳定区分 anomaly 和 positive control。"
        "这类负结果很重要，因为它阻止我们把一个看起来有热力图响应、但对象级排序不可靠的"
        "分数扩大到 40 类主实验。",
        "",
        "![P4 A4 cap3 anomaly](assets/02_p4_geometry/a4_cap3_bending0.svg)",
        "",
        "![P4 A4 cap3 positive](assets/02_p4_geometry/a4_cap3_positive0.svg)",
        "",
        "## 3. cap3：registration/template false positive",
        "",
        "### 3.1 现象",
        "",
        "`cap3_positive9/7/10` 是正常样本，但 PASDF object score 很高：",
        "",
        "| sample | label | PASDF object score | 解释 |",
        "|---|---:|---:|---|",
        "| `cap3_positive9` | 0 | `0.109517` | 最高优先级 false positive |",
        "| `cap3_positive7` | 0 | `0.096982` | 第二优先级 false positive |",
        "| `cap3_positive10` | 0 | `0.064902` | 少量 top-k 高分点拉高 object score |",
        "",
        "### 3.2 图像证据",
        "",
        "![cap3 positive9 overlay](assets/03_cap3_overlay/cap3_positive9_template_overlay.svg)",
        "",
        "![cap3 positive7 overlay](assets/03_cap3_overlay/cap3_positive7_template_overlay.svg)",
        "",
        "![cap3 positive10 overlay](assets/03_cap3_overlay/cap3_positive10_template_overlay.svg)",
        "",
        "人工观察和图像都显示：红蓝点云不是良好重合状态，错位集中在帽檐、鸭舌状突出结构等局部区域。"
        "这说明 `cap3` 的高分不适合简单解释为阈值过低，而更像 template/canonical alignment 问题。",
        "",
        "### 3.3 定量证据",
        "",
        "| sample | label | PASDF object | residual overlap | closure |",
        "|---|---:|---:|---:|---|",
        "| `cap3_positive9` | 0 | `0.109517` | `0.902439` | strong positive template mismatch |",
        "| `cap3_positive7` | 0 | `0.096982` | `0.932927` | strong positive template mismatch |",
        "| `cap3_positive10` | 0 | `0.064902` | `0.975610` | strong positive template mismatch |",
        "",
        "这些 positive 样本的 PASDF top-k 高分点和 template residual top-k 高分点高度重叠，"
        "直接支持 registration/template false positive 结论。",
        "",
        "## 4. tap1：PASDF soft boundary 与 fusion 拒绝",
        "",
        "### 4.1 P5 图像证据",
        "",
        "![tap1 broken2 PASDF vs geometry](assets/05_tap1_comparison/tap1_broken2_pasdf_vs_geometry.svg)",
        "",
        "![tap1 broken3 PASDF vs geometry](assets/05_tap1_comparison/tap1_broken3_pasdf_vs_geometry.svg)",
        "",
        "![tap1 hole0 PASDF vs geometry](assets/05_tap1_comparison/tap1_hole0_pasdf_vs_geometry.svg)",
        "",
        "P5 图像上，geometry residual 右图更容易出现红色高分区域，PASDF 左图整体更蓝。"
        "但这只是视觉现象，不能直接推出 geometry 对对象级判断更好。",
        "",
        "### 4.2 P6 positive-aware 诊断",
        "",
        "alpha sweep 的核心约束是：提升 anomaly 的同时，不能把 positive object score 一起抬高。"
        "结果所有 alpha 都没有通过 strict 或 soft positive-aware gating。",
        "",
        "| alpha | min anomaly obj | mean anomaly obj | max positive obj | strict | soft |",
        "|---:|---:|---:|---:|---|---|",
        "| `0.0` | `0.651312` | `0.701104` | `0.799581` | False | False |",
        "| `0.5` | `0.934062` | `0.988108` | `1.097702` | False | False |",
        "| `1.0` | `1.276239` | `1.331737` | `1.439421` | False | False |",
        "",
        "下图是 positive counterexample。它说明 hybrid 分数能把正常样本也打高，不能直接作为最终对象级分数。",
        "",
        "![tap1 positive0 hybrid](assets/07_p6_hybrid/tap1_positive0_hybrid.svg)",
        "",
        "## 5. helmet1：点级定位弱",
        "",
        "`helmet1` 的 mean anomaly 可以高于 positive 均值，但最高 positive 仍压住 object boundary。"
        "因此它不适合继续用简单 top-k 或 fusion 调参处理，更适合作为报告中的点级定位局限案例。",
        "",
        "![helmet1 concavity4 PASDF heatmap](assets/06_helmet1/helmet1_concavity4_pasdf_score.svg)",
        "",
        "## 6. 最终 failure-mode closure",
        "",
        "| 类别 | Failure mode | Object boundary | 后续处理 |",
        "|---|---|---|---|",
        "| `cap3` | registration/template false positive | failed | 优先 template selection / registration robustness |",
        "| `tap1` | soft object boundary with low-amplitude local PASDF signal | soft_pass | 不恢复 additive fusion，保留 PASDF calibration 结论 |",
        "| `helmet1` | point-level localization weakness | failed | 补 heatmap/GT overlay 复查，作为局限案例 |",
        "",
    ]
    _write("02_experiment_and_failure_analysis.md", lines)


def _write_reproduction() -> None:
    lines = [
        "# 复现与证据清单",
        "",
        "## 目录",
        "",
        "- [1. 环境边界](#1-环境边界)",
        "- [2. 最小复现命令](#2-最小复现命令)",
        "- [3. 证据索引](#3-证据索引)",
        "- [4. 本包内 CSV](#4-本包内-csv)",
        "- [5. 质量门](#5-质量门)",
        "- [6. 未纳入本包的大型产物](#6-未纳入本包的大型产物)",
        "",
        "## 1. 环境边界",
        "",
        "- Docker/conda 容器用于训练、评估、测试和生成实验产物。",
        "- Git push/pull/fetch 在宿主机执行。",
        "- 大型数据、权重、NPZ、日志和完整实验目录不进入 git。",
        "- 当前交付 tag：`v0.1-p6-delivery`。",
        "",
        "## 2. 最小复现命令",
        "",
        "### 2.1 PASDF 40 类 baseline",
        "",
        "```bash",
        "PYTHONPATH=src CUDA_VISIBLE_DEVICES=0 python scripts/evaluate.py \\",
        "  --config configs/experiment/E1_pasdf_baseline.yaml \\",
        "  --output-dir experiments/E1_pasdf_baseline/full_40cls",
        "```",
        "",
        "### 2.2 P5 score export",
        "",
        "```bash",
        "export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}",
        "PYTHONPATH=src python scripts/export_pasdf_scores.py \\",
        "  --config experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml \\",
        "  --pasdf-root third_party/PASDF \\",
        "  --classes cap3 helmet1 tap1 ashtray0 \\",
        "  --output-dir experiments/P5_pasdf_scores/representative \\",
        "  --summary-md docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md \\",
        "  --summary-csv docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.csv \\",
        "  --save-point-scores",
        "```",
        "",
        "### 2.3 P5 case study 图像",
        "",
        "```bash",
        "PYTHONPATH=src python scripts/visualize_pasdf_scores.py \\",
        "  --score-root experiments/P5_pasdf_scores/representative \\",
        "  --template-root third_party/PASDF/data/ShapeNetAD \\",
        "  --output-dir experiments/P5_case_study \\",
        "  --summary-md docs/document/stage_record/2026-06-13_p5_targeted_case_study.md \\",
        "  --summary-csv docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv",
        "```",
        "",
        "### 2.4 P6 failure-mode closure",
        "",
        "```bash",
        "PYTHONPATH=src python scripts/run_p6_failure_mode_closure.py",
        "```",
        "",
        "### 2.5 本交付包重建",
        "",
        "```bash",
        "python3 docs/document/delivery_pack/2026-06-14_p6_delivery_pack/scripts/build_delivery_pack.py",
        "```",
        "",
        "## 3. 证据索引",
        "",
        "| 证据 | 本包内路径 | 原始来源 |",
        "|---|---|---|",
        "| P3 40 类评估 CSV | `assets/csv/p3_pasdf_40cls_evaluation_results.csv` | `experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv` |",
        "| P6 evidence index | `assets/csv/p6_delivery_evidence_index.csv` | `docs/document/stage_record/2026-06-14_p6_delivery_evidence_index.csv` |",
        "| P6 failure closure CSV | `assets/csv/p6_failure_mode_closure.csv` | `docs/document/stage_record/2026-06-14_p6_failure_mode_closure.csv` |",
        "",
        "## 4. 本包内 CSV",
        "",
        _csv_preview("assets/csv/p3_pasdf_40cls_evaluation_results.csv", limit=8),
        "",
        "## 5. 质量门",
        "",
        "最近一次交付阶段在 Docker `0613` 的 `pasdf` 环境中通过：",
        "",
        "```text",
        "pytest -q: 114 passed",
        "ruff check src scripts tests: passed",
        "black --check src scripts tests: passed",
        "mypy src/pcdad: passed",
        "```",
        "",
        "## 6. 未纳入本包的大型产物",
        "",
        "- `data/Anomaly-ShapeNet-v2/`：原始与预处理数据。",
        "- `third_party/PASDF/results/` 与权重：PASDF 官方资产。",
        "- `experiments/P5_pasdf_scores/representative/**/points/*.npz`：点级分数数组。",
        "- 完整 run.log、mesh、checkpoint 和大规模中间产物。",
        "",
    ]
    _write("03_reproduction_and_evidence.md", lines)


def _write_visual_gallery() -> None:
    lines = [
        "# 图册",
        "",
        "## 目录",
        "",
        "- [1. 数据与预处理](#1-数据与预处理)",
        "- [2. P4 几何 smoke](#2-p4-几何-smoke)",
        "- [3. cap3 template mismatch](#3-cap3-template-mismatch)",
        "- [4. tap1 PASDF vs geometry](#4-tap1-pasdf-vs-geometry)",
        "- [5. helmet1 与 P6 hybrid](#5-helmet1-与-p6-hybrid)",
        "",
        "## 1. 数据与预处理",
        "",
    ]
    for group_title, assets in _gallery_groups().items():
        if group_title != "数据与预处理":
            lines.extend(["", f"## {group_title}", ""])
        for asset in assets:
            lines.extend(
                [
                    f"### {asset.title}",
                    "",
                    f"![{asset.title}]({asset.target})",
                    "",
                    asset.caption,
                    "",
                ]
            )
    _write("04_visual_gallery.md", lines)


def _write_manifest() -> None:
    lines = [
        "# 文件清单",
        "",
        "## 目录",
        "",
        "- [1. Markdown 文件](#1-markdown-文件)",
        "- [2. 图片资产](#2-图片资产)",
        "- [3. CSV 资产](#3-csv-资产)",
        "- [4. 压缩包](#4-压缩包)",
        "",
        "## 1. Markdown 文件",
        "",
        "| 文件 | 用途 |",
        "|---|---|",
        "| `README.md` | 交付包入口和阅读顺序 |",
        "| `01_project_report.md` | 完整项目报告 |",
        "| `02_experiment_and_failure_analysis.md` | 实验结果与失败模式分析 |",
        "| `03_reproduction_and_evidence.md` | 复现命令与证据清单 |",
        "| `04_visual_gallery.md` | 图册 |",
        "| `MANIFEST.md` | 文件清单 |",
        "",
        "## 2. 图片资产",
        "",
        "| 本包路径 | 原始来源 | 用途 |",
        "|---|---|---|",
    ]
    for asset in ASSETS:
        lines.append(f"| `{asset.target}` | `{asset.source}` | {asset.title} |")
    lines.extend(["", "## 3. CSV 资产", "", "| 本包路径 | 原始来源 |", "|---|---|"])
    for source, target in CSV_ASSETS:
        lines.append(f"| `{target}` | `{source}` |")
    lines.extend(
        [
            "",
            "## 4. 压缩包",
            "",
            "| 文件 | 用途 |",
            "|---|---|",
            "| `../2026-06-14_p6_delivery_pack.zip` | 可直接转发的完整交付包压缩文件 |",
            "",
        ]
    )
    _write("MANIFEST.md", lines)


def _gallery_groups() -> dict[str, list[Asset]]:
    groups: dict[str, list[Asset]] = {
        "数据与预处理": [],
        "2. P4 几何 smoke": [],
        "3. cap3 template mismatch": [],
        "4. tap1 PASDF vs geometry": [],
        "5. helmet1 与 P6 hybrid": [],
    }
    for asset in ASSETS:
        if asset.target.startswith("assets/01_data"):
            groups["数据与预处理"].append(asset)
        elif asset.target.startswith("assets/02_p4_geometry"):
            groups["2. P4 几何 smoke"].append(asset)
        elif asset.target.startswith("assets/03_cap3_overlay") or asset.target.startswith(
            "assets/04_pasdf_heatmap"
        ):
            groups["3. cap3 template mismatch"].append(asset)
        elif asset.target.startswith("assets/05_tap1_comparison"):
            groups["4. tap1 PASDF vs geometry"].append(asset)
        else:
            groups["5. helmet1 与 P6 hybrid"].append(asset)
    return groups


def _csv_preview(relative_path: str, *, limit: int) -> str:
    path = PACK_ROOT / relative_path
    if not path.exists():
        return f"`{relative_path}` 尚未生成。"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        rows = [row for _, row in zip(range(limit + 1), reader, strict=False)]
    if not rows:
        return f"`{relative_path}` 为空。"
    header = rows[0]
    body = rows[1:]
    lines = [
        f"`{relative_path}` 前 {len(body)} 行预览：",
        "",
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        padded = row + [""] * (len(header) - len(row))
        lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    return "\n".join(lines)


def _write(relative_path: str, lines: list[str]) -> None:
    path = PACK_ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _git(*args: str, default: str = "") -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return default
    return result.stdout.strip() or default


if __name__ == "__main__":
    main()
