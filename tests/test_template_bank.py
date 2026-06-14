from __future__ import annotations

from pathlib import Path

import numpy as np

from pcdad.prototypes.template_bank import (
    TemplatePrototype,
    assignment_entropy,
    build_template_assignments,
)


def test_build_template_assignments_ranks_closer_template_first() -> None:
    sample = np.array([[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [0.0, 0.1, 0.0]])
    close_template = TemplatePrototype(
        class_name="cap3",
        template_id="template_close",
        points=sample + 0.01,
        source_path=Path("close.obj"),
    )
    far_template = TemplatePrototype(
        class_name="cap3",
        template_id="template_far",
        points=sample + 2.0,
        source_path=Path("far.obj"),
    )

    assignments = build_template_assignments(
        class_name="cap3",
        sample_id="cap3_positive9",
        sample_points=sample,
        templates=(far_template, close_template),
        pasdf_scores=None,
        top_ratio=0.5,
    )

    assert [item.template_id for item in assignments] == ["template_close", "template_far"]
    assert [item.rank for item in assignments] == [1, 2]
    assert assignments[0].nn_topk_mean < assignments[1].nn_topk_mean
    assert assignments[0].assignment_entropy > 0.0


def test_build_template_assignments_reports_pasdf_residual_overlap() -> None:
    sample = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [3.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    )
    template = TemplatePrototype(
        class_name="cap3",
        template_id="template0",
        points=np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [2.0, 0.0, 0.0],
                [10.0, 0.0, 0.0],
            ],
            dtype=np.float64,
        ),
    )
    pasdf_scores = np.array([0.0, 0.1, 0.2, 0.9], dtype=np.float64)

    assignments = build_template_assignments(
        class_name="cap3",
        sample_id="cap3_positive9",
        sample_points=sample,
        templates=(template,),
        pasdf_scores=pasdf_scores,
        top_ratio=0.25,
    )

    assert assignments[0].residual_overlap == 1.0
    assert assignments[0].assignment_entropy == 0.0


def test_assignment_entropy_is_zero_for_single_template() -> None:
    assert assignment_entropy(np.array([0.2], dtype=np.float64)) == 0.0
