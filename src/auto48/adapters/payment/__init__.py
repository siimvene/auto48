"""Payment adapter factory.

Returns StripePaymentAdapter when stripe_secret_key is configured,
otherwise falls back to StubPaymentAdapter for offline dev and CI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from auto48.config import Settings
    from auto48.ports.payment import PaymentPort


def get_payment_adapter(settings: Settings) -> PaymentPort:
    """Return the appropriate PaymentPort implementation.

    Stripe adapter is returned only when stripe_secret_key is non-empty;
    otherwise the deterministic stub is used (safe for dev and CI).
    """
    from auto48.adapters.payment.stripe_adapter import StripePaymentAdapter
    from auto48.adapters.payment.stub import StubPaymentAdapter

    if settings.stripe_secret_key:
        return StripePaymentAdapter(secret_key=settings.stripe_secret_key)
    return StubPaymentAdapter()
