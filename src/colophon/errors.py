"""Domain-specific exception types used across Colophon.

Errors flow up from focused subsystems as typed failures so CLI and tests can
distinguish config, expression, and deploy problems.
"""

from __future__ import annotations




class ExpressionResolutionError(ValueError):
    """Raised when a YAML expression cannot be resolved during build."""


class DeployConfigError(ValueError):
    """Raised when deployment configuration is missing or invalid."""


class DeployError(RuntimeError):
    """Raised when a deployment side effect fails."""


class ProjectConfigError(ValueError):
    """Raised when project configuration is missing or invalid."""
