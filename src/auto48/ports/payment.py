"""PaymentPort: clean-room protocol separating domain logic from payment providers.

Implementations live under adapters/payment/. The port lets the domain layer
stay unaware of whether payments go through Stripe, a stub, or another provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class PaymentResult:
    """Result returned by any PaymentPort operation."""

    provider_id: str
    status: str
    client_secret: str | None = field(default=None)


class PaymentPort(Protocol):
    """Async contract for payment providers (subscriptions + one-off charges)."""

    async def create_subscription(
        self,
        customer_ref: str,
        plan: str,
    ) -> PaymentResult:
        """Create or activate a subscription for the given customer reference.

        Args:
            customer_ref: Provider-agnostic customer identifier (e.g. seller profile id
                as string, or a Stripe customer id).
            plan: Subscription plan name (e.g. ``"basic"``, ``"pro"``).

        Returns:
            PaymentResult with provider_id set to the subscription id.
        """
        ...

    async def create_promotion_charge(
        self,
        listing_ref: str,
        kind: str,
        amount_cents: int,
    ) -> PaymentResult:
        """Initiate a one-off charge for a listing promotion.

        Args:
            listing_ref: Provider-agnostic listing identifier.
            kind: Promotion type (e.g. ``"bump"``, ``"featured"``, ``"spotlight"``).
            amount_cents: Charge amount in EUR cents.

        Returns:
            PaymentResult with client_secret populated if client-side confirmation is
            required (Stripe PaymentIntent flow).
        """
        ...

    async def cancel_subscription(self, sub_ref: str) -> None:
        """Cancel an active subscription identified by *sub_ref*.

        Args:
            sub_ref: Provider subscription id (e.g. Stripe subscription id).
        """
        ...
