"""Billing: Stripe (web Plus and B2B seats) and App Store (iOS Plus).

Webhooks are idempotent: each provider event id is processed once
(table billing_events). The plan of a user changes only here.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import stripe

from letterlens.api.errors import ApiError, bad_request, forbidden
from letterlens.billing.appstore import (
    AppStoreVerificationError,
    entitlement_from_transaction,
    verify_signed_payload,
)
from letterlens.container import Container
from letterlens.db import DbContext
from letterlens.db import repo as R
from letterlens.services.principal import Principal

log = logging.getLogger(__name__)


class BillingService:
    def __init__(self, container: Container) -> None:
        self.c = container

    # -- Stripe -----------------------------------------------------------------

    def _stripe(self) -> stripe.StripeClient:
        key = self.c.settings.stripe_secret_key
        if key is None:
            raise ApiError(501, "billing_disabled", "Stripe is not configured")
        return stripe.StripeClient(key.get_secret_value())

    def checkout(self, principal: Principal, product: str, tenant_id: str | None, quantity: int) -> str:
        s = self.c.settings
        if product == "plus":
            price, metadata, qty = s.stripe_price_plus, {"kind": "plus", "user_id": principal.user_id}, 1
        else:
            if tenant_id is None or not principal.is_tenant_admin(tenant_id):
                raise forbidden("tenant admins only")
            price, metadata, qty = s.stripe_price_seat, {"kind": "seats", "tenant_id": tenant_id}, quantity
