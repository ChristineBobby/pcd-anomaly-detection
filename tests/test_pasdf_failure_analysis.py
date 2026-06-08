from __future__ import annotations

from pathlib import Path

from pcdad.analysis.pasdf_failures import (
    FailureThresholds,
    analyze_pasdf_failures,
    parse_open3d_warnings_by_class,
    render_failure_report_markdown,
)


def _write_results(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "class,pixel_auc,object_auc",
                "ashtray0,0.92,1.0",
                "cap3,0.846,0.551",
                "helmet1,0.623,0.957",
                "tap1,0.903,0.767",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_log(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "Evaluating [ashtray0]: 100%|done",
                "---ashtray0-- AUROC Pixel: 0.92, AUROC Object: 1.0",
                "Evaluating [cap3]: 50%|running",
                "[Open3D WARNING] Too few correspondences (85) after mutual filter",
                "[Open3D WARNING] Too few correspondences (90) after mutual filter",
                "---cap3-- AUROC Pixel: 0.846, AUROC Object: 0.551",
                "Evaluating [tap1]: 50%|running",
                "[Open3D WARNING] Too few correspondences (74) after mutual filter",
                "---tap1-- AUROC Pixel: 0.903, AUROC Object: 0.767",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_parse_open3d_warnings_by_class_uses_current_evaluating_context(tmp_path: Path) -> None:
    log_path = tmp_path / "run.log"
    _write_log(log_path)

    warnings = parse_open3d_warnings_by_class(log_path)

    assert warnings.total_count == 3
    assert warnings.by_class == {"cap3": 2, "tap1": 1}
    assert warnings.unattributed_count == 0
    assert warnings.examples["cap3"][0].correspondence_count == 85


def test_analyze_pasdf_failures_summarizes_threshold_failures_and_means(tmp_path: Path) -> None:
    results_path = tmp_path / "evaluation_results.csv"
    log_path = tmp_path / "run.log"
    _write_results(results_path)
    _write_log(log_path)

    summary = analyze_pasdf_failures(
        results_path,
        log_path=log_path,
        thresholds=FailureThresholds(pixel_auc=0.85, object_auc=0.8),
    )

    assert summary.class_count == 4
    assert summary.mean_pixel_auc == 0.823
    assert summary.mean_object_auc == 0.81875
    assert [item.class_name for item in summary.object_failures] == ["cap3", "tap1"]
    assert [item.class_name for item in summary.pixel_failures] == ["helmet1", "cap3"]
    assert summary.min_object.class_name == "cap3"
    assert summary.min_pixel.class_name == "helmet1"
    assert summary.open3d_warnings.total_count == 3


def test_render_failure_report_markdown_contains_actionable_p4_sections(tmp_path: Path) -> None:
    results_path = tmp_path / "evaluation_results.csv"
    log_path = tmp_path / "run.log"
    _write_results(results_path)
    _write_log(log_path)
    summary = analyze_pasdf_failures(results_path, log_path=log_path)

    markdown = render_failure_report_markdown(summary, title="P4 Failure Summary")

    assert markdown.startswith("# P4 Failure Summary")
    assert "## Metric Summary" in markdown
    assert "| cap3 | 0.846000 | 0.551000 | 2 |" in markdown
    assert "## P4 Priority Classes" in markdown
    assert "`cap3`, `tap1`, `helmet1`" in markdown
