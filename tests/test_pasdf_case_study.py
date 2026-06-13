from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from pcdad.analysis.pasdf_case_study import (
    PasdfCaseStudySpec,
    render_case_study_markdown,
    run_pasdf_case_study,
    write_case_study_csv,
)


def _write_score_npz(root: Path, class_name: str, sample_id: str) -> Path:
    path = root / class_name / "points" / f"{sample_id}.npz"
    path.parent.mkdir(parents=True)
    np.savez_compressed(
        path,
        points=np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]],
            dtype=np.float32,
        ),
        point_scores=np.array([0.1, 0.8, 0.4, 0.9], dtype=np.float64),
        mask=np.array([0, 1, 0, 1], dtype=np.int64),
        label=np.array(1, dtype=np.int64),
        object_score=np.array(0.9, dtype=np.float64),
        sample_path=np.array(f"/data/{class_name}/test/{sample_id}.pcd"),
    )
    return path


def _write_template_obj(root: Path, class_name: str) -> Path:
    path = root / class_name / f"{class_name}_template0.obj"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                "v 0.0 0.0 0.0",
                "v 1.0 0.0 0.0",
                "v 0.0 1.0 0.0",
                "v 1.0 1.0 0.0",
                "f 1 2 3",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_run_pasdf_case_study_loads_npz_writes_svg_and_records(tmp_path: Path) -> None:
    score_root = tmp_path / "scores"
    score_path = _write_score_npz(score_root, "cap3", "cap3_positive9")
    output_dir = tmp_path / "case_study"

    records = run_pasdf_case_study(
        PasdfCaseStudySpec(
            score_root=score_root,
            sample_ids=("cap3_positive9",),
            output_dir=output_dir,
            max_points=4,
            seed=7,
        )
    )

    assert len(records) == 1
    record = records[0]
    assert record.class_name == "cap3"
    assert record.sample_id == "cap3_positive9"
    assert record.label == 1
    assert record.point_count == 4
    assert record.gt_point_count == 2
    assert record.object_score == 0.9
    assert record.score_mean == 0.55
    assert record.score_p95 == 0.885
    assert record.gt_score_mean == 0.85
    assert record.background_score_mean == 0.25
    assert record.point_score_path == str(score_path)
    assert Path(record.svg_path).exists()
    assert "cap3_positive9" in Path(record.svg_path).read_text(encoding="utf-8")


def test_run_pasdf_case_study_writes_template_overlay_and_geometry_comparison(
    tmp_path: Path,
) -> None:
    score_root = tmp_path / "scores"
    template_root = tmp_path / "templates"
    _write_score_npz(score_root, "tap1", "tap1_broken2")
    _write_template_obj(template_root, "tap1")

    records = run_pasdf_case_study(
        PasdfCaseStudySpec(
            score_root=score_root,
            sample_ids=("tap1_broken2",),
            output_dir=tmp_path / "case_study",
            template_root=template_root,
            overlay_sample_ids=("tap1_broken2",),
            comparison_sample_ids=("tap1_broken2",),
            max_points=4,
            seed=7,
        )
    )

    record = records[0]
    assert record.template_overlay_path is not None
    assert record.geometry_comparison_path is not None
    assert record.geometry_object_score is not None
    assert record.geometry_gt_score_mean is not None
    assert record.geometry_background_score_mean is not None
    assert Path(record.template_overlay_path).exists()
    assert Path(record.geometry_comparison_path).exists()
    assert "sample=red template=blue" in Path(record.template_overlay_path).read_text(
        encoding="utf-8"
    )
    comparison_text = Path(record.geometry_comparison_path).read_text(encoding="utf-8")
    assert "PASDF score" in comparison_text
    assert "Geometry distance score" in comparison_text


def test_run_pasdf_case_study_rejects_missing_sample(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="missing_sample"):
        run_pasdf_case_study(
            PasdfCaseStudySpec(
                score_root=tmp_path / "scores",
                sample_ids=("missing_sample",),
                output_dir=tmp_path / "out",
            )
        )


def test_write_case_study_csv_and_markdown_are_stable(tmp_path: Path) -> None:
    score_root = tmp_path / "scores"
    template_root = tmp_path / "templates"
    _write_score_npz(score_root, "cap3", "cap3_positive9")
    _write_template_obj(template_root, "cap3")
    records = run_pasdf_case_study(
        PasdfCaseStudySpec(
            score_root=score_root,
            sample_ids=("cap3_positive9",),
            output_dir=tmp_path / "case_study",
            template_root=template_root,
            overlay_sample_ids=("cap3_positive9",),
            comparison_sample_ids=("cap3_positive9",),
            max_points=4,
        )
    )
    csv_path = tmp_path / "summary.csv"

    write_case_study_csv(records, csv_path)
    markdown = render_case_study_markdown(records, title="P5 case study")

    csv_text = csv_path.read_text(encoding="utf-8")
    assert csv_text.splitlines()[0] == (
        "class_name,sample_id,label,point_count,gt_point_count,object_score,score_mean,"
        "score_p95,score_max,gt_score_mean,background_score_mean,svg_path,point_score_path,"
        "template_overlay_path,geometry_comparison_path,geometry_object_score,"
        "geometry_gt_score_mean,geometry_background_score_mean"
    )
    assert "cap3,cap3_positive9,1,4,2,0.9,0.55,0.885,0.9,0.85,0.25" in csv_text
    assert markdown.startswith("# P5 case study")
    assert "`cap3_positive9`" in markdown
    assert "GT 内均值" in markdown
    assert "template overlay" in markdown
    assert "PASDF-vs-geometry" in markdown
