"""StripePaymentAdapter: production payment adapter backed by the Stripe API.

Guards: instantiation raises a clear ConfigurationError when stripe_secret_key is
empty so unconfigured environments fail loudly rather than silently.
"""

from __future__ import annotations

import stripe

from auto48.ports.payment import PaymentResult


class StripePaymentAdapter:
    """Production adapter — calls Stripe API for subscriptions and charges."""

    def __init__(self, secret_key: str) -> None:
        if not secret_key:
            raise ValueError(
                "StripePaymentAdapter requires a non-empty stripe_secret_key. "
                "Set AUTO48_STRIPE_SECRET_KEY or leave it empty to use StubPaymentAdapter."
            )
        self._client = stripe.StripeClient(secret_key)

    async def create_subscription(
        self,
        customer_ref: str,
        plan: str,
    ) -> PaymentResult:
        """Create a Stripe subscription for the given customer.

        customer_ref is used as the Stripe customer id; callers must ensure the
        customer is pre-created in Stripe before calling this method.
        """
        sub = self._client.subscriptions.create(
            params={
                "customer": customer_ref,
                "items": [{"price": plan}],
                "expand": ["latest_invoice.payment_intent"],
            }
        )
        return PaymentResult(
            provider_id=sub.id,
            status=sub.status,
            client_secret=None,
        )

    async def create_promotion_charge(
        self,
        listing_ref: str,
        kind: str,
        amount_cents: int,
    ) -> PaymentResult:
        """Create a Stripe PaymentIntent for a one-off promotion charge."""
        intent = self._client.payment_intents.create(
            params={
                "amount": amount_cents,
                "currency": "eur",
                "metadata": {"listing_ref": listing_ref, "kind": kind},
                "automatic_payment_methods": {"enabled": True},
            }
        )
        return PaymentResult(
            provider_id=intent.id,
            status=intent.status,
            client_secret=intent.client_secret,
        )

    async def cancel_subscription(self, sub_ref: str) -> None:
        """Cancel an active Stripe subscription."""
        self._client.subscriptions.cancel(sub_ref)

    async def hold_deposit(
        self,
        *,
        amount_eur_cents: int,
        reference: str,
    ) -> PaymentResult:
        """Create a Stripe PaymentIntent with manual capture (escrow hold)."""
        intent = self._client.payment_intents.create(
            params={
                "amount": amount_eur_cents,
                "currency": "eur",
                "capture_method": "manual",
                "metadata": {"reference": reference},
                "automatic_payment_methods": {"enabled": True},
            }
        )
        return PaymentResult(
            provider_id=intent.id,
            status=intent.status,
            client_secret=intent.client_secret,
        )

    async def release_deposit(self, provider_id: str) -> PaymentResult:
        """Capture a previously held PaymentIntent, transferring funds to the seller."""
        intent = self._client.payment_intents.capture(provider_id)
        return PaymentResult(
            provider_id=intent.id,
            status=intent.status,
            client_secret=None,
        )

    async def refund_deposit(self, provider_id: str) -> PaymentResult:
        """Cancel/refund a held PaymentIntent back to the buyer."""
        intent = self._client.payment_intents.cancel(provider_id)
        return PaymentResult(
            provider_id=intent.id,
            status=intent.status,
            client_secret=None,
        )
