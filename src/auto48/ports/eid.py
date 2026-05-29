"""eID verification port: Protocol + stub adapter.

The ``EidPort`` Protocol defines the interface that Phase 2 will implement
against TARA (Estonian national auth) and Smart-ID. For now, ``StubEidAdapter``
returns a fake "verified" result so that the rest of the system can be built
without a live eID integration.

Phase 2 wiring:
    - Replace ``StubEidAdapter`` with a ``TaraAdapter`` / ``SmartIdAdapter``
      that calls the real external services.
    - Register the concrete adapter via the FastAPI dependency-injection layer
      (e.g. ``Annotated[EidPort, Depends(get_eid_adapter)]``).
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EidPort(Protocol):
    """Abstraction over identity-verification backends (TARA, Smart-ID, …)."""

    async def start_verification(self, person_identifier: str) -> str:
        """Initiate a verification flow for *person_identifier*.

        Args:
            person_identifier: National ID or phone number used by the backend.

        Returns:
            An opaque challenge/session string the client must present to
            ``check_status``.
        """
        ...

    async def check_status(self, session_id: str) -> bool:
        """Poll whether the verification identified by *session_id* succeeded.

        Returns:
            ``True`` if identity has been confirmed; ``False`` if still pending
            or if verification failed.
        """
        ...


class StubEidAdapter:
    """Fake eID adapter used until TARA/Smart-ID is wired in Phase 2.

    ``start_verification`` always returns a deterministic fake challenge;
    ``check_status`` always reports "verified". Do NOT use in production.
    """

    async def start_verification(self, person_identifier: str) -> str:
        # Return a predictable stub value so tests can assert on it.
        return f"stub-challenge-{person_identifier}"

    async def check_status(self, session_id: str) -> bool:  # noqa: ARG002
        return True
