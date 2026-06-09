from __future__ import annotations

from pathlib import Path

from pcdad.analysis.pasdf_stability import (
    StabilityCollectionSpec,
    collect_pasdf_stability_runs,
    render_stability_markdown,
)


def _write_run(
    run_dir: Path,
    class_name: str,
    pixel_auc: float,
    object_auc: float,
    warning_count: int,
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
        f"[Open3D WARNING] Too few correspondences ({80 + index}) after mutual filter"
        for index in range(warning_count)
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


def test_collect_pasdf_stability_runs_summarizes_repeated_runs(tmp_path: Path) -> None:
    root = tmp_path / "stability"
    _write_run(root / "helmet2" / "run_001", "helmet2", 0.80, 0.64, 0)
    _write_run(root / "helmet2" / "run_002", "helmet2", 0.82, 0.70, 2)
    _write_run(root / "cap3" / "run_001", "cap3", 0.85, 0.77, 0)

    summary = collect_pasdf_stability_runs(
        StabilityCollectionSpec(root=root, classes=("helmet2", "cap3"))
    )

    assert len(summary.rows) == 3
    assert summary.rows[0].class_name == "cap3"
    assert summary.rows[1].class_name == "helmet2"
    assert summary.rows[1].warning_count == 0
    assert summary.rows[2].warning_sample_count == 1
    helmet2 = summary.by_class["helmet2"]
    assert helmet2.run_count == 2
    assert helmet2.mean_object_auc == 0.67
    assert helmet2.min_object_auc == 0.64
    assert helmet2.max_object_auc == 0.70


def test_render_stability_markdown_contains_chinese_summary(tmp_path: Path) -> None:
    root = tmp_path / "stability"
    _write_run(root / "helmet2" / "run_001", "helmet2", 0.80, 0.64, 0)
    _write_run(root / "helmet2" / "run_002", "helmet2", 0.82, 0.70, 2)
    summary = collect_pasdf_stability_runs(StabilityCollectionSpec(root=root, classes=("helmet2",)))

    markdown = render_stability_markdown(summary, title="P4 稳定性测试")

    assert markdown.startswith("# P4 稳定性测试")
    assert "## 类别稳定性摘要" in markdown
    assert "| helmet2 | 2 | 0.810000 | 0.670000 |" in markdown
    assert "## 全部 Run" in markdown
    assert "| helmet2 | run_002 | 0.820000 | 0.700000 | 2 | 1 |" in markdown
