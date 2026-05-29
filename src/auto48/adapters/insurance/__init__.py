"""Insurance adapter factory.

Returns :class:`StubInsuranceAdapter` unconditionally for now.
A real partner adapter can be wired here once credentials are available.
"""

from __future__ import annotations

from auto48.adapters.insurance.stub import StubInsuranceAdapter
from auto48.config import Settings
from auto48.ports.insurance import InsurancePort


def get_insurance_adapter(settings: Settings) -> InsurancePort:  # noqa: ARG001
    """Return the appropriate InsurancePort implementation for *settings*.

    Currently always returns the stub (no partner API configured yet).

    Args:
        settings: Application settings (reserved for future partner key checks).

    Returns:
        An :class:`InsurancePort`-compatible adapter.
    """
    return StubInsuranceAdapter()
