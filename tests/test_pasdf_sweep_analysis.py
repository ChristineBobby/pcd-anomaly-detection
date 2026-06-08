from __future__ import annotations

from pathlib import Path

from pcdad.analysis.pasdf_sweep import (
    SweepCollectionSpec,
    collect_pasdf_sweep_results,
    render_sweep_summary_markdown,
)


def _write_run(
    run_dir: Path, class_name: str, pixel_auc: float, object_auc: float, warnings: int
) -> None:
    run_dir.mkdir(parents=True)
    (run_dir / "evaluation_results.csv").write_text(
        "\n".join(
            [
                "class,pixel_auc,object_auc",
                f"{class_name},{pixel_auc},{object_auc}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    warning_lines = [
        f"[Open3D WARNING] Too few correspondences ({90 + index}) after mutual filter"
        for index in range(warnings)
    ]
    (run_dir / "run.log").write_text(
        "\n".join(
            [
                f"Evaluating [{class_name}]: 100%|done",
                f"/workspace/data/{class_name}/test/{class_name}_positive0.pcd",
                *warning_lines,
                f"---{class_name}-- AUROC Pixel: {pixel_auc}, AUROC Object: {object_auc}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_collect_pasdf_sweep_results_selects_best_object_auc_and_warning_counts(
    tmp_path: Path,
) -> None:
    root = tmp_path / "sweep"
    _write_run(root / "cap3" / "vs_0p020", "cap3", 0.84, 0.61, 0)
    _write_run(root / "cap3" / "vs_0p030", "cap3", 0.85, 0.55, 2)
    _write_run(root / "cap4" / "vs_0p020", "cap4", 0.86, 0.63, 1)

    summary = collect_pasdf_sweep_results(SweepCollectionSpec(root=root, classes=("cap3", "cap4")))

    assert len(summary.rows) == 3
    assert summary.rows[0].class_name == "cap3"
    assert summary.rows[0].voxel_size == 0.02
    assert summary.rows[0].warning_count == 0
    assert summary.rows[1].warning_sample_count == 1
    assert summary.best_by_class["cap3"].voxel_size == 0.02
    assert summary.best_by_class["cap3"].object_auc == 0.61
    assert summary.best_by_class["cap4"].voxel_size == 0.02


def test_render_sweep_summary_markdown_contains_best_table(tmp_path: Path) -> None:
    root = tmp_path / "sweep"
    _write_run(root / "cap3" / "vs_0p020", "cap3", 0.84, 0.61, 0)
    _write_run(root / "cap3" / "vs_0p030", "cap3", 0.85, 0.55, 2)
    summary = collect_pasdf_sweep_results(SweepCollectionSpec(root=root, classes=("cap3",)))

    markdown = render_sweep_summary_markdown(summary, title="P4 Voxel Sweep")

    assert markdown.startswith("# P4 Voxel Sweep")
    assert "| cap3 | 0.020 | 0.840000 | 0.610000 | 0 | 0 |" in markdown
    assert "## All Runs" in markdown
    assert "| cap3 | 0.030 | 0.850000 | 0.550000 | 2 | 1 |" in markdown
