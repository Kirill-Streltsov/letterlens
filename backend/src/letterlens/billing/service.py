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

