"""Prototype-bank utilities for registration-aware diagnostics."""

from pcdad.prototypes.registration_confidence import (
    RegistrationConfidenceConfig,
    RegistrationConfidenceResult,
    registration_confidence_from_features,
)
from pcdad.prototypes.template_bank import (
    TemplateAssignment,
    TemplatePrototype,
    assignment_entropy,
    build_template_assignments,
)

__all__ = [
    "RegistrationConfidenceConfig",
    "RegistrationConfidenceResult",
    "TemplateAssignment",
    "TemplatePrototype",
    "assignment_entropy",
    "build_template_assignments",
    "registration_confidence_from_features",
]
