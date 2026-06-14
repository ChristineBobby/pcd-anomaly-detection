from __future__ import annotations

import pytest

from pcdad.prototypes.registration_confidence import (
    RegistrationConfidenceConfig,
    registration_confidence_from_features,
)


def test_registration_confidence_decreases_for_high_overlap_and_entropy() -> None:
    config = RegistrationConfidenceConfig(reference_topk_mean=1.0)

    clean = registration_confidence_from_features(
        nn_topk_mean=0.05,
        assignment_entropy=0.0,
        residual_overlap=0.0,
        bbox_ratio=0.9,
        pair_ratio=0.7,
        config=config,
    )
    risky = registration_confidence_from_features(
        nn_topk_mean=0.8,
        assignment_entropy=1.0,
        residual_overlap=0.95,
        bbox_ratio=0.2,
        pair_ratio=0.1,
        config=config,
    )

    assert 0.0 <= risky.confidence < clean.confidence <= 1.0
    assert risky.risk_reason == "template_mismatch_risk"
    assert clean.risk_reason == "low_registration_risk"


def test_registration_confidence_allows_missing_overlap_but_penalizes_uncertainty() -> None:
    result = registration_confidence_from_features(
        nn_topk_mean=0.5,
        assignment_entropy=0.5,
        residual_overlap=None,
        bbox_ratio=0.5,
        pair_ratio=0.5,
        config=RegistrationConfidenceConfig(reference_topk_mean=1.0),
    )

    assert 0.0 < result.confidence < 1.0
    assert result.risk_reason == "moderate_registration_risk"


def test_registration_confidence_rejects_negative_features() -> None:
    with pytest.raises(ValueError, match="nn_topk_mean"):
        registration_confidence_from_features(
            nn_topk_mean=-0.1,
            assignment_entropy=0.0,
            residual_overlap=0.0,
            bbox_ratio=0.5,
            pair_ratio=0.5,
            config=RegistrationConfidenceConfig(reference_topk_mean=1.0),
        )
