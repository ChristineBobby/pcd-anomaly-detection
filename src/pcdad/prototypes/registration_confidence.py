"""Registration confidence scoring from template-assignment features."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegistrationConfidenceConfig:
    """Weights and thresholds for registration confidence."""

    reference_topk_mean: float = 0.05
    residual_weight: float = 0.35
    entropy_weight: float = 0.25
    overlap_weight: float = 0.25
    concentration_weight: float = 0.15
    high_risk_threshold: float = 0.65
    moderate_risk_threshold: float = 0.30
    eps: float = 1e-12


@dataclass(frozen=True)
class RegistrationConfidenceResult:
    """Registration confidence and a coarse risk reason."""

    confidence: float
    risk_score: float
    risk_reason: str


def registration_confidence_from_features(
    *,
    nn_topk_mean: float,
    assignment_entropy: float,
    residual_overlap: float | None,
    bbox_ratio: float,
    pair_ratio: float,
    config: RegistrationConfidenceConfig | None = None,
) -> RegistrationConfidenceResult:
    """Convert residual and uncertainty features into a 0-1 confidence value."""

    cfg = config or RegistrationConfidenceConfig()
    _require_non_negative("nn_topk_mean", nn_topk_mean)
    _require_unit_interval("assignment_entropy", assignment_entropy)
    if residual_overlap is not None:
        _require_unit_interval("residual_overlap", residual_overlap)
    _require_non_negative("bbox_ratio", bbox_ratio)
    _require_non_negative("pair_ratio", pair_ratio)
    if cfg.reference_topk_mean <= 0.0:
        raise ValueError("reference_topk_mean must be positive")

    residual_risk = nn_topk_mean / (nn_topk_mean + cfg.reference_topk_mean + cfg.eps)
    overlap_risk = 0.0 if residual_overlap is None else residual_overlap
    concentration_risk = 1.0 - min(1.0, 0.5 * (bbox_ratio + pair_ratio))
    raw_risk = (
        cfg.residual_weight * residual_risk
        + cfg.entropy_weight * assignment_entropy
        + cfg.overlap_weight * overlap_risk
        + cfg.concentration_weight * concentration_risk
    )
    risk_score = _clip01(raw_risk)
    confidence = _clip01(1.0 - risk_score)
    if risk_score >= cfg.high_risk_threshold:
        reason = "template_mismatch_risk"
    elif risk_score >= cfg.moderate_risk_threshold:
        reason = "moderate_registration_risk"
    else:
        reason = "low_registration_risk"
    return RegistrationConfidenceResult(
        confidence=round(confidence, 6),
        risk_score=round(risk_score, 6),
        risk_reason=reason,
    )


def _require_non_negative(name: str, value: float) -> None:
    if value < 0.0:
        raise ValueError(f"{name} must be non-negative")


def _require_unit_interval(name: str, value: float) -> None:
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{name} must be in [0, 1]")


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
