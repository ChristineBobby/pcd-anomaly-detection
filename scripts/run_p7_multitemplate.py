"""Run P7-A multi-template registration diagnostics."""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from pcdad.analysis.pasdf_case_study import load_pasdf_point_score
from pcdad.data.dataset import read_pcd_points
from pcdad.prototypes.template_bank import (
    TemplateAssignment,
    TemplatePrototype,
    build_template_assignments,
)


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the P7-A CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-root", type=Path, required=True)
    parser.add_argument("--template-root", type=Path, required=True)
    parser.add_argument(
        "--template-mode",
        choices=("pasdf_obj", "train_pcd"),
        default="pasdf_obj",
        help="Template source layout: PASDF OBJ templates or Anomaly-ShapeNet train PCDs.",
    )
    parser.add_argument("--classes", nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--top-ratio", type=float, default=0.01)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def planned_outputs(args: argparse.Namespace) -> dict[str, Path]:
    """Return output paths planned by the CLI."""

    output_dir = Path(args.output_dir)
    return {
        "template_assignments_csv": output_dir / "template_assignments.csv",
        "per_sample_scores_csv": output_dir / "per_sample_scores.csv",
        "failure_toplist_csv": output_dir / "failure_toplist.csv",
        "readme": output_dir / "README.md",
        "config": output_dir / "config.yaml",
        "git_hash": output_dir / "git_hash.txt",
    }


ASSIGNMENT_FIELDS: tuple[str, ...] = (
    "class_name",
    "sample_id",
    "label",
    "point_count",
    "gt_point_count",
    "pasdf_object_score",
    "template_id",
    "rank",
    "nn_mean",
    "nn_p95",
    "nn_topk_mean",
    "residual_overlap",
    "bbox_ratio",
    "pair_ratio",
    "assignment_entropy",
    "registration_confidence",
    "risk_reason",
)

PER_SAMPLE_FIELDS: tuple[str, ...] = (
    *ASSIGNMENT_FIELDS,
    "top2_nn_topk_mean",
    "top1_top2_margin",
    "top1_top2_relative_margin",
)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    args = build_arg_parser().parse_args(argv)
    outputs = planned_outputs(args)
    if args.dry_run:
        for name, path in outputs.items():
            print(f"{name}: {path}")
        return 0
    records = run_multitemplate(args)
    write_assignments_csv(records, outputs["template_assignments_csv"])
    write_per_sample_scores_csv(records, outputs["per_sample_scores_csv"])
    write_failure_toplist_csv(records, outputs["failure_toplist_csv"])
    write_config(args, outputs["config"])
    write_git_hash(outputs["git_hash"])
    write_readme(args, outputs["readme"], records)
    return 0


def run_multitemplate(args: argparse.Namespace) -> tuple[dict[str, Any], ...]:
    """Run multi-template assignment for all requested classes."""

    rows: list[dict[str, Any]] = []
    for class_name in args.classes:
        templates = load_template_prototypes(args.template_root, class_name, args.template_mode)
        for score_path in iter_score_paths(args.score_root, class_name):
            payload = load_pasdf_point_score(score_path)
            points = payload["points"].astype(np.float64)
            scores = payload["point_scores"].astype(np.float64)
            assignments = build_template_assignments(
                class_name=class_name,
                sample_id=score_path.stem,
                sample_points=points,
                templates=templates,
                pasdf_scores=scores,
                top_ratio=args.top_ratio,
            )
            for assignment in assignments:
                rows.append(_row_from_assignment(assignment, payload))
    return tuple(rows)


def iter_score_paths(score_root: Path, class_name: str) -> tuple[Path, ...]:
    """Return P5 score NPZ paths for one class."""

    points_dir = Path(score_root) / class_name / "points"
    if not points_dir.exists():
        raise FileNotFoundError(f"score points directory not found: {points_dir}")
    paths = tuple(sorted(points_dir.glob("*.npz")))
    if not paths:
        raise FileNotFoundError(f"no score NPZ files found in {points_dir}")
    return paths


def load_template_prototypes(
    template_root: Path,
    class_name: str,
    template_mode: str = "pasdf_obj",
) -> tuple[TemplatePrototype, ...]:
    """Load template prototypes for one class."""

    if template_mode == "pasdf_obj":
        return _load_pasdf_obj_templates(template_root, class_name)
    if template_mode == "train_pcd":
        return _load_train_pcd_templates(template_root, class_name)
    raise ValueError(f"unsupported template mode: {template_mode}")


def _load_pasdf_obj_templates(
    template_root: Path, class_name: str
) -> tuple[TemplatePrototype, ...]:
    """Load PASDF-style OBJ templates for one class."""

    class_dir = Path(template_root) / class_name
    if not class_dir.exists():
        raise FileNotFoundError(f"template class directory not found: {class_dir}")
    paths = tuple(sorted(class_dir.glob(f"{class_name}_template*.obj")))
    if not paths:
        raise FileNotFoundError(f"no template OBJ files found in {class_dir}")
    return tuple(
        TemplatePrototype(
            class_name=class_name,
            template_id=path.stem,
            points=_load_obj_vertices(path),
            source_path=path,
        )
        for path in paths
    )


def _load_train_pcd_templates(
    template_root: Path, class_name: str
) -> tuple[TemplatePrototype, ...]:
    """Load Anomaly-ShapeNet normal train PCD templates for one class."""

    train_dir = Path(template_root) / class_name / "train"
    if not train_dir.exists():
        raise FileNotFoundError(f"template train directory not found: {train_dir}")
    paths = tuple(sorted(train_dir.glob(f"{class_name}_template*.pcd")))
    if not paths:
        raise FileNotFoundError(f"no template PCD files found in {train_dir}")
    return tuple(
        TemplatePrototype(
            class_name=class_name,
            template_id=path.stem,
            points=read_pcd_points(path).astype(np.float64),
            source_path=path,
        )
        for path in paths
    )


def write_assignments_csv(rows: tuple[dict[str, Any], ...], path: Path) -> Path:
    """Write template assignment rows."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ASSIGNMENT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in ASSIGNMENT_FIELDS})
    return path


def write_per_sample_scores_csv(rows: tuple[dict[str, Any], ...], path: Path) -> Path:
    """Write one top-ranked assignment per sample."""

    per_sample_rows = tuple(
        _with_assignment_margin(row, rows) for row in rows if int(row["rank"]) == 1
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PER_SAMPLE_FIELDS)
        writer.writeheader()
        for row in per_sample_rows:
            writer.writerow({field: row.get(field) for field in PER_SAMPLE_FIELDS})
    return path


def _with_assignment_margin(
    row: dict[str, Any], rows: tuple[dict[str, Any], ...]
) -> dict[str, Any]:
    sample_rows = sorted(
        (
            candidate
            for candidate in rows
            if candidate["class_name"] == row["class_name"]
            and candidate["sample_id"] == row["sample_id"]
        ),
        key=lambda candidate: int(candidate["rank"]),
    )
    if len(sample_rows) < 2:
        return {
            **row,
            "top2_nn_topk_mean": None,
            "top1_top2_margin": None,
            "top1_top2_relative_margin": None,
        }
    top1_value = float(sample_rows[0]["nn_topk_mean"])
    top2_value = float(sample_rows[1]["nn_topk_mean"])
    margin = top2_value - top1_value
    relative_margin = margin / top1_value if top1_value > 1e-12 else None
    return {
        **row,
        "top2_nn_topk_mean": round(top2_value, 6),
        "top1_top2_margin": round(margin, 6),
        "top1_top2_relative_margin": None if relative_margin is None else round(relative_margin, 6),
    }


def write_failure_toplist_csv(rows: tuple[dict[str, Any], ...], path: Path) -> Path:
    """Write positive samples with highest mismatch risk first."""

    positive_rows = [row for row in rows if int(row["label"]) == 0 and int(row["rank"]) == 1]
    positive_rows.sort(
        key=lambda row: (
            -float(row["pasdf_object_score"]),
            float(row["registration_confidence"]),
            row["sample_id"],
        )
    )
    return write_assignments_csv(tuple(positive_rows), path)


def write_config(args: argparse.Namespace, path: Path) -> Path:
    """Write a small config snapshot."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"score_root: {args.score_root}",
                f"template_root: {args.template_root}",
                f"template_mode: {args.template_mode}",
                "classes:",
                *[f"  - {class_name}" for class_name in args.classes],
                f"top_ratio: {args.top_ratio}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def write_git_hash(path: Path) -> Path:
    """Write current git hash if available."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        value = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        value = "unknown"
    path.write_text(value + "\n", encoding="utf-8")
    return path


def write_readme(args: argparse.Namespace, path: Path, rows: tuple[dict[str, Any], ...]) -> Path:
    """Write a concise run README."""

    path.parent.mkdir(parents=True, exist_ok=True)
    top_risks = [
        row
        for row in rows
        if int(row["rank"]) == 1 and row["risk_reason"] == "template_mismatch_risk"
    ]
    top_risks.sort(
        key=lambda row: (
            float(row["registration_confidence"]),
            -float(row["pasdf_object_score"]),
            row["class_name"],
            row["sample_id"],
        )
    )
    top_risks = top_risks[:10]
    lines = [
        "# P7-A Multi-template Registration Diagnostics",
        "",
        "## Command",
        "",
        "```bash",
        "PYTHONPATH=src python scripts/run_p7_multitemplate.py "
        f"--score-root {args.score_root} "
        f"--template-root {args.template_root} "
        f"--template-mode {args.template_mode} "
        f"--classes {' '.join(args.classes)} "
        f"--output-dir {args.output_dir} "
        f"--top-ratio {args.top_ratio}",
        "```",
        "",
        "## Summary",
        "",
        f"- classes: `{', '.join(args.classes)}`",
        f"- template-mode: `{args.template_mode}`",
        f"- assignment rows: `{len(rows)}`",
        f"- top-ratio: `{args.top_ratio}`",
        "",
        "## Top Template-mismatch Risks",
        "",
        "| class | sample | score | confidence | reason |",
        "|---|---|---:|---:|---|",
    ]
    for row in top_risks:
        lines.append(
            f"| {row['class_name']} | `{row['sample_id']}` | "
            f"{float(row['pasdf_object_score']):.6f} | "
            f"{float(row['registration_confidence']):.6f} | {row['risk_reason']} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _row_from_assignment(
    assignment: TemplateAssignment,
    payload: dict[str, np.ndarray[Any, np.dtype[Any]]],
) -> dict[str, Any]:
    mask = np.asarray(payload["mask"], dtype=np.int64).reshape(-1)
    points = np.asarray(payload["points"], dtype=np.float64)
    return {
        "class_name": assignment.class_name,
        "sample_id": assignment.sample_id,
        "label": int(np.asarray(payload["label"]).reshape(-1)[0]),
        "point_count": int(points.shape[0]),
        "gt_point_count": int(np.count_nonzero(mask)),
        "pasdf_object_score": round(float(np.asarray(payload["object_score"]).reshape(-1)[0]), 6),
        "template_id": assignment.template_id,
        "rank": assignment.rank,
        "nn_mean": assignment.nn_mean,
        "nn_p95": assignment.nn_p95,
        "nn_topk_mean": assignment.nn_topk_mean,
        "residual_overlap": assignment.residual_overlap,
        "bbox_ratio": assignment.bbox_ratio,
        "pair_ratio": assignment.pair_ratio,
        "assignment_entropy": assignment.assignment_entropy,
        "registration_confidence": assignment.registration_confidence,
        "risk_reason": assignment.risk_reason,
    }


def _load_obj_vertices(path: Path) -> np.ndarray[Any, np.dtype[np.float64]]:
    vertices: list[tuple[float, float, float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if not raw_line.startswith("v "):
                continue
            parts = raw_line.split()
            if len(parts) < 4:
                raise ValueError(f"malformed OBJ vertex line in {path}: {raw_line.rstrip()}")
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
    if not vertices:
        raise ValueError(f"OBJ file contains no vertices: {path}")
    return np.asarray(vertices, dtype=np.float64)


if __name__ == "__main__":
    raise SystemExit(main())
