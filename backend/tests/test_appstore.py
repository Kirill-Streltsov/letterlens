"""App Store JWS verification against a locally generated certificate chain."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from letterlens.billing.appstore import (
    INTERMEDIATE_OID,
    LEAF_OID,
    AppStoreVerificationError,
    entitlement_from_transaction,
    verify_signed_payload,
)

NOW = datetime(2026, 11, 26, tzinfo=UTC)


