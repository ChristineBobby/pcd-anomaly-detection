from __future__ import annotations

import csv
from pathlib import Path

from pcdad.analysis.delivery_evidence import (
    DeliveryEvidenceRecord,
    build_default_delivery_evidence_records,
    render_delivery_evidence_markdown,
    write_delivery_evidence_csv,
)


def test_default_delivery_evidence_records_are_stable(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "docs/document/stage_record").mkdir(parents=True)
    (repo_root / "docs/document/stage_record/2026-06-08_p0_p3_stage_check.md").write_text(
        "p3",
        encoding="utf-8",
    )
    (repo_root / "experiments/E1_pasdf_baseline/full_40cls").mkdir(parents=True)
    (repo_root / "experiments/E1_pasdf_baseline/full_40cls/evaluation_results.csv").write_text(
        "class,pixel_auc,object_auc\n",
        encoding="utf-8",
    )

    records = build_default_delivery_evidence_records(
        repo_root=repo_root,
        commit_hash="abc1234",
    )

    assert len(records) == 9
    assert tuple(record.evidence_id for record in records) == (
        "p3_pasdf_baseline_40cls",
        "p4_geometry_negative_closure",
        "p5_pasdf_score_export",
        "p5_targeted_case_study",
        "p6_targeted_diagnostics",
        "p6_alpha_sweep_positive_gating",
        "p6_region_explanation",
        "p6_pasdf_calibration",
        "p6_failure_mode_closure",
    )
    first = records[0]
    assert first.stage == "P3"
    assert first.status == "tracked_ready"
    assert first.artifact_status == "artifact_ready"
    assert first.commit_hash == "abc1234"


def test_default_generation_commands_match_current_cli_flags(tmp_path: Path) -> None:
    records = build_default_delivery_evidence_records(
        repo_root=tmp_path,
        commit_hash="abc1234",
    )
    commands = {record.evidence_id: record.generation_command for record in records}

    assert (
        "--output-dir experiments/P5_pasdf_scores/representative"
        in commands["p5_pasdf_score_export"]
    )
    assert "--output-root" not in commands["p5_pasdf_score_export"]
    assert "--alpha-grid 0.0 0.1 0.25 0.5 0.75 1.0" in commands["p6_alpha_sweep_positive_gating"]
    assert "--mode" not in commands["p6_alpha_sweep_positive_gating"]
    assert "--run-region-explanation" in commands["p6_region_explanation"]
    assert "--mode" not in commands["p6_region_explanation"]


def test_delivery_evidence_csv_and_markdown_are_stable(tmp_path: Path) -> None:
    record = DeliveryEvidenceRecord(
        stage="P6",
        evidence_id="p6_failure_mode_closure",
        claim="cap3/tap1/helmet1 failure mode 已收口。",
        conclusion="cap3 是 template false positive；tap1 不恢复 additive fusion。",
        status="tracked_ready",
        artifact_status="artifact_ready",
        stage_record_path="docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md",
        result_csv_path="docs/document/stage_record/2026-06-14_p6_failure_mode_closure.csv",
        artifact_paths=("experiments/P6_failure_mode_closure/failure_mode_closure_records.csv",),
        generation_command="PYTHONPATH=src python scripts/run_p6_failure_mode_closure.py",
        commit_hash="abc1234",
        notes="直接服务最终报告。",
    )

    csv_path = write_delivery_evidence_csv((record,), tmp_path / "index.csv")
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

    assert rows == [
        {
            "stage": "P6",
            "evidence_id": "p6_failure_mode_closure",
            "claim": "cap3/tap1/helmet1 failure mode 已收口。",
            "conclusion": "cap3 是 template false positive；tap1 不恢复 additive fusion。",
            "status": "tracked_ready",
            "artifact_status": "artifact_ready",
            "stage_record_path": (
                "docs/document/stage_record/2026-06-14_p6_failure_mode_closure.md"
            ),
            "result_csv_path": (
                "docs/document/stage_record/2026-06-14_p6_failure_mode_closure.csv"
            ),
            "artifact_paths": (
                "experiments/P6_failure_mode_closure/failure_mode_closure_records.csv"
            ),
            "generation_command": "PYTHONPATH=src python scripts/run_p6_failure_mode_closure.py",
            "commit_hash": "abc1234",
            "notes": "直接服务最终报告。",
        }
    ]

    markdown = render_delivery_evidence_markdown((record,))

    assert "# P6 交付证据包" in markdown
    assert "## 目录" in markdown
    assert "cap3/tap1/helmet1 failure mode 已收口。" in markdown
    assert "下一步建议" in markdown


def test_default_records_mark_missing_paths(tmp_path: Path) -> None:
    records = build_default_delivery_evidence_records(
        repo_root=tmp_path,
        commit_hash="abc1234",
    )

    assert records[0].status == "missing_tracked_record"
    assert records[0].artifact_status == "missing_artifact"
