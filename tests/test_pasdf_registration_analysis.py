from __future__ import annotations

from pathlib import Path

from pcdad.analysis.pasdf_failures import analyze_pasdf_failures
from pcdad.analysis.pasdf_registration import (
    RegistrationDiagnosticInputs,
    build_registration_diagnostics,
    parse_registration_warning_events,
    render_registration_diagnostics_markdown,
)


def _write_results(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "class,pixel_auc,object_auc",
                "cap3,0.846928,0.550877",
                "cap4,0.863803,0.628070",
                "helmet2,0.834360,0.776812",
                "tap1,0.903394,0.766667",
                "helmet1,0.622745,0.957143",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_log(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "Evaluating [cap3]: 100%|done",
                "/workspace/data/16384/cap3/test/cap3_concavity2.pcd",
                "[Open3D WARNING] Too few correspondences (96) after mutual filter",
                "[Open3D WARNING] Too few correspondences (107) after mutual filter",
                "---cap3-- AUROC Pixel: 0.846928, AUROC Object: 0.550877",
                "Evaluating [cap4]: 100%|done",
                "/workspace/data/16384/cap4/test/cap4_positive11.pcd",
                "[Open3D WARNING] Too few correspondences (95) after mutual filter",
                "---cap4-- AUROC Pixel: 0.863803, AUROC Object: 0.628070",
                "Evaluating [tap1]: 100%|done",
                "/workspace/data/16384/tap1/test/tap1_bulge0.pcd",
                "---tap1-- AUROC Pixel: 0.903394, AUROC Object: 0.766667",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_parse_registration_warning_events_tracks_nearest_sample_path(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "run.log"
    _write_log(log_path)

    events = parse_registration_warning_events(log_path)

    assert len(events) == 3
    assert events[0].class_name == "cap3"
    assert events[0].sample_name == "cap3_concavity2.pcd"
    assert events[0].sample_path == Path("/workspace/data/16384/cap3/test/cap3_concavity2.pcd")
    assert events[0].correspondence_count == 96
    assert events[2].class_name == "cap4"
    assert events[2].sample_name == "cap4_positive11.pcd"


def test_build_registration_diagnostics_prioritizes_failures_with_voxel_values(
    tmp_path: Path,
) -> None:
    results_path = tmp_path / "evaluation_results.csv"
    log_path = tmp_path / "run.log"
    voxel_path = tmp_path / "voxel_sizes.yaml"
    _write_results(results_path)
    _write_log(log_path)
    voxel_path.write_text(
        "\n".join(
            [
                "ShapeNetAD:",
                "  cap3: 0.03",
                "  cap4: 0.02",
                "  helmet2: 0.03",
                "  tap1: 0.04",
                "  helmet1: 0.02",
                "",
            ]
        ),
        encoding="utf-8",
    )
    failure_summary = analyze_pasdf_failures(results_path, log_path=log_path)

    diagnostics = build_registration_diagnostics(
        RegistrationDiagnosticInputs(
            failure_summary=failure_summary,
            run_log=log_path,
            voxel_sizes_path=voxel_path,
            sweep_voxel_sizes=(0.02, 0.03, 0.04, 0.05),
            experiment_config=Path("configs/experiment/E1_pasdf_baseline.yaml"),
            output_root=Path("experiments/P4_registration_sweep"),
            max_classes=4,
        )
    )

    assert [row.class_name for row in diagnostics.priority_rows] == [
        "cap3",
        "cap4",
        "tap1",
        "helmet2",
    ]
    cap3 = diagnostics.priority_rows[0]
    assert cap3.warning_count == 2
    assert cap3.warning_sample_count == 1
    assert cap3.official_voxel_size == 0.03
    assert cap3.sweep_voxel_sizes == (0.02, 0.03, 0.04, 0.05)
    assert diagnostics.warning_sample_rows[0].sample_name == "cap3_concavity2.pcd"
    assert "--classes cap3 --voxel-size 0.02" in diagnostics.sweep_commands[0]
    assert (
        "--output-dir experiments/P4_registration_sweep/cap3/vs_0p020"
        in diagnostics.sweep_commands[0]
    )


def test_render_registration_diagnostics_markdown_contains_sweep_plan(
    tmp_path: Path,
) -> None:
    results_path = tmp_path / "evaluation_results.csv"
    log_path = tmp_path / "run.log"
    voxel_path = tmp_path / "voxel_sizes.yaml"
    _write_results(results_path)
    _write_log(log_path)
    voxel_path.write_text("ShapeNetAD:\n  cap3: 0.03\n  cap4: 0.02\n", encoding="utf-8")
    failure_summary = analyze_pasdf_failures(results_path, log_path=log_path)
    diagnostics = build_registration_diagnostics(
        RegistrationDiagnosticInputs(
            failure_summary=failure_summary,
            run_log=log_path,
            voxel_sizes_path=voxel_path,
            max_classes=2,
        )
    )

    markdown = render_registration_diagnostics_markdown(
        diagnostics,
        title="P4 Registration 诊断",
    )

    assert markdown.startswith("# P4 Registration 诊断")
    assert "| cap3 | 0.846928 | 0.550877 | 2 | 1 | 0.030 |" in markdown
    assert "cap3_concavity2.pcd" in markdown
    assert "--voxel-size 0.02" in markdown
