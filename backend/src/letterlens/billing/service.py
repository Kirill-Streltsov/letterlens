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
        if not price:
            raise ApiError(501, "billing_disabled", "price is not configured")
        session = self._stripe().v1.checkout.sessions.create(
            params={
                "mode": "subscription",
                "line_items": [{"price": price, "quantity": qty}],
                "client_reference_id": metadata.get("user_id") or metadata.get("tenant_id"),
                "metadata": metadata,
                "subscription_data": {"metadata": metadata},
                "success_url": f"{s.public_web_url}/billing/success",
                "cancel_url": f"{s.public_web_url}/billing/cancel",
            }
        )
        if not session.url:
            raise ApiError(502, "stripe_error", "Stripe did not return a checkout URL")
        return session.url

    def stripe_webhook(self, payload: bytes, signature: str | None) -> None:
        secret = self.c.settings.stripe_webhook_secret
        if secret is None:
            raise ApiError(501, "billing_disabled", "Stripe is not configured")
        try:
            event = stripe.Webhook.construct_event(payload, signature, secret.get_secret_value())
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise bad_request("invalid_signature", "webhook signature is invalid") from exc
        with self.c.db.session(DbContext.as_system()) as conn:
            if not R.first_time_event(conn, "stripe", event.id):
                return
            obj: dict[str, Any] = event.data.object  # type: ignore[assignment]
            if event.type in {"customer.subscription.created", "customer.subscription.updated",
                              "customer.subscription.deleted"}:
                self._apply_subscription(conn, obj, deleted=event.type.endswith("deleted"))
            R.audit(conn, None, f"billing.stripe.{event.type}", "event", event.id)

    @staticmethod
    def _apply_subscription(conn: Any, sub: dict[str, Any], deleted: bool) -> None:
        metadata = sub.get("metadata") or {}
        active = not deleted and sub.get("status") in {"active", "trialing", "past_due"}
        items = (sub.get("items") or {}).get("data") or [{}]
        period_end = sub.get("current_period_end") or items[0].get("current_period_end")
        expires = datetime.fromtimestamp(period_end, UTC) if period_end else None
        if metadata.get("kind") == "plus" and metadata.get("user_id"):
            R.update_user(
                conn, metadata["user_id"], plan="plus" if active else "free",
                plan_source="stripe", plan_expires_at=expires,
                stripe_customer_id=sub.get("customer"),
            )
        elif metadata.get("kind") == "seats" and metadata.get("tenant_id"):
            quantity = int(items[0].get("quantity") or 0) if active else 0
            R.set_tenant_seats(conn, metadata["tenant_id"], quantity, sub.get("customer"))

    # -- App Store --------------------------------------------------------------

    def _entitlement(self, signed: str) -> Any:
        s = self.c.settings
        try:
            tx = verify_signed_payload(signed)
            return entitlement_from_transaction(
                tx, s.appstore_bundle_id, s.appstore_product_plus, s.appstore_environment
            )
        except AppStoreVerificationError as exc:
            raise bad_request("invalid_transaction", str(exc)) from exc

    def appstore_transaction(self, principal: Principal, signed_transaction: str) -> tuple[str, datetime | None]:
        ent = self._entitlement(signed_transaction)
        # The app sets appAccountToken = user id at purchase; reject foreign transactions.
        if ent.app_account_token and ent.app_account_token.lower() != principal.user_id.lower():
            raise forbidden("transaction belongs to another account")
        plan = "plus" if ent.active else "free"
        with self.c.db.session(principal.ctx) as conn:
            R.update_user(conn, principal.user_id, plan=plan, plan_source="appstore",
                          plan_expires_at=ent.expires_at)
            R.audit(conn, principal.user_id, "billing.appstore.transaction", "user", principal.user_id,
                    details={"active": ent.active})
        return plan, ent.expires_at

    def appstore_notification(self, signed_payload: str) -> None:
        try:
            notification = verify_signed_payload(signed_payload)
        except AppStoreVerificationError as exc:
            raise bad_request("invalid_notification", str(exc)) from exc
        data = notification.get("data") or {}
        signed_tx = data.get("signedTransactionInfo")
        uuid = notification.get("notificationUUID", "")
        if not signed_tx:
            return
        ent = self._entitlement(signed_tx)
        with self.c.db.session(DbContext.as_system()) as conn:
            if not R.first_time_event(conn, "appstore", uuid):
                return
            if ent.app_account_token:
                R.update_user(conn, ent.app_account_token, plan="plus" if ent.active else "free",
                              plan_source="appstore", plan_expires_at=ent.expires_at)
            R.audit(conn, None, f"billing.appstore.{notification.get('notificationType')}",
                    "event", uuid)
