"""P6 delivery evidence pack generation."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeliveryEvidenceRecord:
    """One final-delivery evidence item tied to a claim and reproducible artifact."""

    stage: str
    evidence_id: str
    claim: str
    conclusion: str
    status: str
    artifact_status: str
    stage_record_path: str
    result_csv_path: str
    artifact_paths: tuple[str, ...]
    generation_command: str
    commit_hash: str
    notes: str


@dataclass(frozen=True)
class _EvidenceSpec:
    stage: str
    evidence_id: str
    claim: str
    conclusion: str
    stage_record_path: str
    result_csv_path: str
    artifact_paths: tuple[str, ...]
    generation_command: str
    notes: str


DELIVERY_EVIDENCE_FIELDS: tuple[str, ...] = (
    "stage",
    "evidence_id",
    "claim",
    "conclusion",
    "status",
    "artifact_status",
    "stage_record_path",
    "result_csv_path",
    "artifact_paths",
    "generation_command",
    "commit_hash",
    "notes",
)


def build_default_delivery_evidence_records(
    *,
    repo_root: str | Path,
    commit_hash: str,
) -> tuple[DeliveryEvidenceRecord, ...]:
    """Build the default P3-P6 delivery evidence index."""

    root = Path(repo_root)
    return tuple(
        _record_from_spec(spec, repo_root=root, commit_hash=commit_hash) for spec in _specs()
    )


def write_delivery_evidence_csv(
    records: Sequence[DeliveryEvidenceRecord],
    path: str | Path,
) -> Path:
    """Write delivery evidence records to a stable CSV file."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DELIVERY_EVIDENCE_FIELDS)
        writer.writeheader()
        for record in records:
            row = asdict(record)
            row["artifact_paths"] = ";".join(record.artifact_paths)
            writer.writerow({field: row[field] for field in DELIVERY_EVIDENCE_FIELDS})
    return output


def render_delivery_evidence_markdown(
    records: Sequence[DeliveryEvidenceRecord],
    *,
    title: str = "P6 交付证据包",
) -> str:
    """Render a Chinese Markdown delivery evidence pack."""

    record_tuple = tuple(records)
    if not record_tuple:
        raise ValueError("At least one delivery evidence record is required")

    commit_hash = record_tuple[0].commit_hash
    lines = [
        f"# {title}",
        "",
        "## 目录",
        "",
        "- [1. 交付范围](#1-交付范围)",
        "- [2. 核心结论](#2-核心结论)",
        "- [3. 证据索引](#3-证据索引)",
        "- [4. SOP 对照](#4-sop-对照)",
        "- [5. 下一步建议](#5-下一步建议)",
        "",
        "## 1. 交付范围",
        "",
        f"- 当前记录 commit：`{commit_hash}`。",
        "- 本证据包覆盖 P3 baseline、P4 几何负结果、P5 targeted case study、"
        "P6 诊断与 failure-mode closure。",
        "- `experiments/` 下的大型产物不进入 git；本文件只记录路径、命令和结论。",
        "",
        "## 2. 核心结论",
        "",
        "- P3 PASDF 40 类复现达标：mean object AUROC=`0.900214149779`，"
        "mean pixel AUROC=`0.896009030694`。",
        "- P4 naive geometry enhancement 不进入主表；A2/A3/A4 smoke 没有稳定区分"
        " anomaly 与 positive control。",
        "- P6 positive-aware alpha sweep 拒绝恢复 additive geometry fusion。",
        "- `cap3` 收口为 registration/template false positive；`tap1` 收口为 PASDF"
        " soft object boundary；`helmet1` 收口为点级定位弱和 positive boundary 混淆。",
        "",
        "## 3. 证据索引",
        "",
        "| 阶段 | 证据 ID | 结论声明 | 当前结论 | 入库记录状态 | 实验产物状态 |",
        "|---|---|---|---|---|---|",
    ]
    for record in record_tuple:
        lines.append(
            f"| {record.stage} | `{record.evidence_id}` | {record.claim} | "
            f"{record.conclusion} | {record.status} | {record.artifact_status} |"
        )

    lines.extend(
        [
            "",
            "## 4. SOP 对照",
            "",
            "| 阶段 | 阶段记录 | 结果 CSV | 实验产物路径 | 生成命令 |",
            "|---|---|---|---|---|",
        ]
    )
    for record in record_tuple:
        artifact_paths = "<br>".join(f"`{path}`" for path in record.artifact_paths) or "NA"
        lines.append(
            f"| {record.stage} | `{record.stage_record_path}` | "
            f"{_fmt_path(record.result_csv_path)} | {artifact_paths} | "
            f"`{record.generation_command}` |"
        )

    lines.extend(
        [
            "",
            "## 5. 下一步建议",
            "",
            "- 进入最终报告/PPT/demo 打包阶段，优先复用本证据包中的 claim 与 artifact path。",
            "- 不继续扩大 naive geometry fusion；若时间允许，只把 cap3 template robustness 和 "
            "helmet1 heatmap/GT overlay 作为附录级补充。",
            "- 发布前从干净 shell 核对 README 最小复现命令，并记录最终 commit 或 tag。",
            "",
        ]
    )
    return "\n".join(lines)


def render_final_delivery_report_draft(
    records: Sequence[DeliveryEvidenceRecord],
    *,
    title: str = "最终报告草稿",
) -> str:
    """Render a compact final report draft from evidence records."""

    record_tuple = tuple(records)
    if not record_tuple:
        raise ValueError("At least one delivery evidence record is required")

    lines = [
        f"# {title}",
        "",
        "## 目录",
        "",
        "- [1. 摘要](#1-摘要)",
        "- [2. 方法与实验主线](#2-方法与实验主线)",
        "- [3. 关键结果](#3-关键结果)",
        "- [4. 失败模式分析](#4-失败模式分析)",
        "- [5. 局限与后续工作](#5-局限与后续工作)",
        "",
        "## 1. 摘要",
        "",
        "本项目以 Anomaly-ShapeNet 40 类协议为主基准，复现 PASDF 官方权重并完成"
        "几何增强、targeted case study 和 P6 failure-mode closure。当前自跑 PASDF "
        "mean object AUROC 为 `0.900214149779`，达到论文级锚点。",
        "",
        "## 2. 方法与实验主线",
        "",
        "- P3：PASDF 官方权重评估，固定 40 类 baseline。",
        "- P4：法向、曲率、距离 residual smoke，用负结果关闭 naive geometry enhancement。",
        "- P5：导出 per-point PASDF score，人工和定量分析代表类别。",
        "- P6：positive-aware alpha sweep、region explanation、top-k calibration 与"
        " failure-mode closure。",
        "",
        "## 3. 关键结果",
        "",
        "| Evidence ID | 结论 |",
        "|---|---|",
    ]
    for record in record_tuple:
        lines.append(f"| `{record.evidence_id}` | {record.conclusion} |")

    lines.extend(
        [
            "",
            "## 4. 失败模式分析",
            "",
            "- `cap3`：normal positive 样本与 template 在局部帽檐/鸭舌结构上不重合，"
            "导致 template residual 与 PASDF top-k 高分重叠。",
            "- `tap1`：PASDF 对 GT 局部有信号，但 object score 幅度低；geometry residual "
            "可作为诊断解释，不支持 additive fusion 进入主表。",
            "- `helmet1`：mean anomaly 可高于 positive 均值，但最高 positive 仍压住边界，"
            "点级定位需要热力图/GT overlay 人工复查。",
            "",
            "## 5. 局限与后续工作",
            "",
            "- 当前交付不包含 Real3D-AD 全量验证和 MiniShift 压力测试。",
            "- 当前几何增强为诊断工具，不作为最终性能提升 claim。",
            "- 后续更值得投入的是 template selection、registration robustness 和更强的"
            " positive-aware calibration，而不是继续调 naive additive fusion。",
            "",
        ]
    )
    return "\n".join(lines)


def _record_from_spec(
    spec: _EvidenceSpec,
    *,
    repo_root: Path,
    commit_hash: str,
) -> DeliveryEvidenceRecord:
    tracked_paths = tuple(
        path
        for path in (spec.stage_record_path, spec.result_csv_path)
        if path and _is_tracked_path(path)
    )
    artifact_paths = tuple(path for path in (spec.result_csv_path, *spec.artifact_paths) if path)
    untracked_artifact_paths = tuple(path for path in artifact_paths if not _is_tracked_path(path))
    return DeliveryEvidenceRecord(
        stage=spec.stage,
        evidence_id=spec.evidence_id,
        claim=spec.claim,
        conclusion=spec.conclusion,
        status=_path_group_status(repo_root, tracked_paths, ready="tracked_ready"),
        artifact_status=_path_group_status(
            repo_root,
            untracked_artifact_paths,
            ready="artifact_ready",
            missing="missing_artifact",
            empty="not_applicable",
        ),
        stage_record_path=spec.stage_record_path,
        result_csv_path=spec.result_csv_path,
        artifact_paths=spec.artifact_paths,
        generation_command=spec.generation_command,
        commit_hash=commit_hash,
        notes=spec.notes,
    )


def _path_group_status(
    repo_root: Path,
    paths: Sequence[str],
    *,
    ready: str,
    missing: str = "missing_tracked_record",
    empty: str = "not_applicable",
) -> str:
    if not paths:
        return empty
    if all((repo_root / path).exists() for path in paths):
        return ready
    return missing


def _is_tracked_path(path: str) -> bool:
    return path.startswith("docs/") or path in {"README.md", "pyproject.toml"}


def _fmt_path(path: str) -> str:
    return "NA" if not path else f"`{path}`"


def _specs() -> tuple[_EvidenceSpec, ...]:
    return (
        _EvidenceSpec(
            stage="P3",
            evidence_id="p3_pasdf_baseline_40cls",
            claim="PASDF 官方权重在 Anomaly-ShapeNet 40 类协议上复现达标。",
            conclusion="mean object AUROC=0.900214149779；mean pixel AUROC=0.896009030694。",
            stage_record_path="docs/document/stage_record/2026-06-08_p0_p3_stage_check.md",
            result_csv_path="experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv",
            artifact_paths=(),
            generation_command=(
                "PYTHONPATH=src CUDA_VISIBLE_DEVICES=0 python scripts/evaluate.py "
                "--config configs/experiment/E1_pasdf_baseline.yaml "
                "--output-dir experiments/E1_pasdf_baseline/full_40cls"
            ),
            notes="P3 baseline 是后续 P4-P6 的固定锚点。",
        ),
        _EvidenceSpec(
            stage="P4",
            evidence_id="p4_geometry_negative_closure",
            claim="A2/A3/A4 naive geometry smoke 已完成并收口为负结果。",
            conclusion="normal/curvature 加权主要放大尺度，未稳定拉开 anomaly 与 positive。",
            stage_record_path="docs/document/stage_record/2026-06-09_p4_geometry_closure.md",
            result_csv_path=(
                "docs/document/stage_record/"
                "2026-06-09_a4_pasdf_geom_full_geometry_smoke_summary.csv"
            ),
            artifact_paths=("experiments/P4_geometry_smoke/config_svgs",),
            generation_command=(
                "PYTHONPATH=src python scripts/run_geometry_smoke.py "
                "--config configs/experiment/A4_pasdf_geom_full.yaml"
            ),
            notes="不建议直接扩到 40 类 A2/A3/A4。",
        ),
        _EvidenceSpec(
            stage="P5",
            evidence_id="p5_pasdf_score_export",
            claim="代表类别 PASDF per-point score 已导出。",
            conclusion="ashtray0/cap3/helmet1/tap1 可用于 targeted heatmap 与 GT 对照。",
            stage_record_path=(
                "docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md"
            ),
            result_csv_path=(
                "docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.csv"
            ),
            artifact_paths=("experiments/P5_pasdf_scores/representative",),
            generation_command=(
                "PYTHONPATH=src python scripts/export_pasdf_scores.py "
                "--config experiments/E1_pasdf_baseline/full_40cls/pasdf_test_ShapeNetAD.yaml "
                "--pasdf-root third_party/PASDF "
                "--classes cap3 helmet1 tap1 ashtray0 "
                "--output-dir experiments/P5_pasdf_scores/representative "
                "--summary-md "
                "docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.md "
                "--summary-csv "
                "docs/document/stage_record/2026-06-10_p5_pasdf_score_export_summary.csv "
                "--save-point-scores"
            ),
            notes="后续 P5/P6 所有 targeted diagnostics 的输入。",
        ),
        _EvidenceSpec(
            stage="P5",
            evidence_id="p5_targeted_case_study",
            claim="cap3 overlay 与 tap1 PASDF-vs-geometry case study 已完成。",
            conclusion=(
                "cap3 更像 registration/template mismatch；tap1 geometry residual "
                "可做局部解释但不等于最终融合方案。"
            ),
            stage_record_path="docs/document/stage_record/2026-06-13_p5_targeted_case_study.md",
            result_csv_path="docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv",
            artifact_paths=(
                "experiments/P5_case_study/template_overlay/cap3",
                "experiments/P5_case_study/pasdf_vs_geometry/tap1",
            ),
            generation_command=(
                "PYTHONPATH=src python scripts/visualize_pasdf_scores.py "
                "--score-root experiments/P5_pasdf_scores/representative "
                "--template-root third_party/PASDF/data/ShapeNetAD "
                "--output-dir experiments/P5_case_study "
                "--summary-md docs/document/stage_record/2026-06-13_p5_targeted_case_study.md "
                "--summary-csv docs/document/stage_record/2026-06-13_p5_targeted_case_study.csv"
            ),
            notes=(
                "详细中文报告见 "
                "docs/document/report/2026-06-13_p5_targeted_case_study_report.md。"
            ),
        ),
        _EvidenceSpec(
            stage="P6",
            evidence_id="p6_targeted_diagnostics",
            claim="cap3/tap1 targeted diagnostics 已生成。",
            conclusion=(
                "cap3 positive 的 NN top5 residual 明显高；" "tap1 hybrid 必须受 positive 约束。"
            ),
            stage_record_path=(
                "docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.md"
            ),
            result_csv_path=(
                "docs/document/stage_record/2026-06-13_p6_targeted_diagnostics_summary.csv"
            ),
            artifact_paths=("experiments/P6_targeted_diagnostics",),
            generation_command="PYTHONPATH=src python scripts/run_p6_targeted_diagnostics.py",
            notes="这是 P6 alpha sweep 和 region explanation 的前置诊断。",
        ),
        _EvidenceSpec(
            stage="P6",
            evidence_id="p6_alpha_sweep_positive_gating",
            claim="tap1 positive-aware alpha sweep 已完成。",
            conclusion="没有 alpha 同时满足 anomaly 分离提升和 positive-aware object 排序约束。",
            stage_record_path="docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.md",
            result_csv_path="docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.csv",
            artifact_paths=("experiments/P6_alpha_sweep",),
            generation_command=(
                "PYTHONPATH=src python scripts/run_p6_targeted_diagnostics.py "
                "--score-root experiments/P5_pasdf_scores/representative "
                "--template-root third_party/PASDF/data/ShapeNetAD "
                "--cap3-samples cap3_positive9 cap3_positive7 cap3_positive10 "
                "cap3_hole0 cap3_hole1 cap3_broken2 cap3_broken3 "
                "--tap1-samples tap1_broken2 tap1_broken3 tap1_hole0 "
                "--tap1-positive-samples tap1_positive0 tap1_positive1 tap1_positive2 "
                "tap1_positive3 tap1_positive4 "
                "--alpha-grid 0.0 0.1 0.25 0.5 0.75 1.0 "
                "--output-dir experiments/P6_alpha_sweep "
                "--summary-md docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.md "
                "--summary-csv docs/document/stage_record/2026-06-13_p6_alpha_sweep_summary.csv "
                "--alpha-sweep-csv experiments/P6_alpha_sweep/tap1_alpha_sweep_records.csv "
                "--max-points 4096"
            ),
            notes="该结论支撑不恢复 additive geometry fusion。",
        ),
        _EvidenceSpec(
            stage="P6",
            evidence_id="p6_region_explanation",
            claim="tap1 region explanation 与 cap3 residual overlap 已完成。",
            conclusion="geometry 对 tap1 的 GT-neighborhood enrichment 没有稳定优于 PASDF。",
            stage_record_path=(
                "docs/document/stage_record/2026-06-13_p6_region_explanation_summary.md"
            ),
            result_csv_path=(
                "docs/document/stage_record/2026-06-13_p6_region_explanation_summary.csv"
            ),
            artifact_paths=("experiments/P6_region_explanation",),
            generation_command=(
                "PYTHONPATH=src python scripts/run_p6_targeted_diagnostics.py "
                "--score-root experiments/P5_pasdf_scores/representative "
                "--template-root third_party/PASDF/data/ShapeNetAD "
                "--cap3-samples cap3_positive9 cap3_positive7 cap3_positive10 "
                "cap3_hole0 cap3_hole1 cap3_broken2 cap3_broken3 "
                "--tap1-samples tap1_broken2 tap1_broken3 tap1_hole0 "
                "--run-region-explanation "
                "--region-output-dir experiments/P6_region_explanation "
                "--region-summary-md "
                "docs/document/stage_record/2026-06-13_p6_region_explanation_summary.md "
                "--region-summary-csv "
                "docs/document/stage_record/2026-06-13_p6_region_explanation_summary.csv "
                "--top-ratio 0.05 "
                "--neighbor-radius-ratio 0.02"
            ),
            notes="把 geometry 固定为诊断信号，不作为性能提升 claim。",
        ),
        _EvidenceSpec(
            stage="P6",
            evidence_id="p6_pasdf_calibration",
            claim="PASDF top-k calibration 已覆盖 cap3/tap1/helmet1。",
            conclusion=(
                "cap3 和 helmet1 未通过 object 排序；tap1 只有 soft pass，" "没有 strict pass。"
            ),
            stage_record_path=(
                "docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.md"
            ),
            result_csv_path=(
                "docs/document/stage_record/2026-06-14_p6_pasdf_calibration_summary.csv"
            ),
            artifact_paths=("experiments/P6_pasdf_calibration/topk_calibration_records.csv",),
            generation_command="PYTHONPATH=src python scripts/run_p6_pasdf_calibration.py",
            notes="解释 object score 越高越异常，以及 top-k ratio 调整为何不足。",
        ),
        _EvidenceSpec(
            stage="P6",
            evidence_id="p6_failure_mode_closure",
            claim="cap3/tap1/helmet1 failure mode 已收口。",
            conclusion=(
                "cap3=registration/template false positive；tap1=soft object boundary；"
                "helmet1=point-level localization weakness。"
            ),
            stage_record_path="docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md",
            result_csv_path="docs/document/stage_record/2026-06-14_p6_failure_mode_closure.csv",
            artifact_paths=(
                "experiments/P6_failure_mode_closure/failure_mode_closure_records.csv",
            ),
            generation_command="PYTHONPATH=src python scripts/run_p6_failure_mode_closure.py",
            notes="本阶段进入最终交付证据包，不再扩 naive fusion。",
        ),
    )
