"""StubPaymentAdapter: deterministic offline adapter for dev and tests.

Returns fake but stable PaymentResults — no network calls, safe for CI.
"""

from __future__ import annotations

from auto48.ports.payment import PaymentResult


class StubPaymentAdapter:
    """Deterministic fake payment adapter — safe for dev and CI."""

    async def create_subscription(
        self,
        customer_ref: str,
        plan: str,
    ) -> PaymentResult:
        return PaymentResult(
            provider_id=f"stub_sub_{customer_ref}_{plan}",
            status="active",
            client_secret=None,
        )

    async def create_promotion_charge(
        self,
        listing_ref: str,
        kind: str,
        amount_cents: int,
    ) -> PaymentResult:
        return PaymentResult(
            provider_id=f"stub_pi_{listing_ref}_{kind}",
            status="succeeded",
            client_secret=f"stub_cs_{listing_ref}_{kind}",
        )

    async def cancel_subscription(self, sub_ref: str) -> None:
        # No-op for the stub.
        return

    async def hold_deposit(
        self,
        *,
        amount_eur_cents: int,
        reference: str,
    ) -> PaymentResult:
        return PaymentResult(
            provider_id=f"stub_hold_{reference}_{amount_eur_cents}",
            status="held",
            client_secret=None,
        )

    async def release_deposit(self, provider_id: str) -> PaymentResult:
        return PaymentResult(
            provider_id=provider_id,
            status="released",
            client_secret=None,
        )

    async def refund_deposit(self, provider_id: str) -> PaymentResult:
        return PaymentResult(
            provider_id=provider_id,
            status="refunded",
            client_secret=None,
        )
