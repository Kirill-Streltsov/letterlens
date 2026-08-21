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


def cert(
    name: str,
    key: ec.EllipticCurvePrivateKey,
    issuer: tuple[x509.Name, ec.EllipticCurvePrivateKey] | None,
    oid: x509.ObjectIdentifier | None = None,
    ca: bool = False,
) -> x509.Certificate:
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    issuer_name, issuer_key = issuer if issuer else (subject, key)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(NOW - timedelta(days=10))
        .not_valid_after(NOW + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
    )
    if oid is not None:
        builder = builder.add_extension(x509.UnrecognizedExtension(oid, b"\x05\x00"), critical=False)
    return builder.sign(issuer_key, hashes.SHA256())


class Chain:
    def __init__(self, leaf_oid: x509.ObjectIdentifier | None = LEAF_OID) -> None:
        self.root_key = ec.generate_private_key(ec.SECP256R1())
        self.root = cert("Test Root", self.root_key, None, ca=True)
        self.int_key = ec.generate_private_key(ec.SECP256R1())
        self.intermediate = cert(
            "Test WWDR", self.int_key, (self.root.subject, self.root_key), INTERMEDIATE_OID, ca=True
        )
        self.leaf_key = ec.generate_private_key(ec.SECP256R1())
        self.leaf = cert("Test Leaf", self.leaf_key, (self.intermediate.subject, self.int_key), leaf_oid)

    def root_der(self) -> bytes:
        return self.root.public_bytes(serialization.Encoding.DER)

    def sign(self, payload: dict[str, Any]) -> str:
        x5c = [
            base64.b64encode(c.public_bytes(serialization.Encoding.DER)).decode()
            for c in (self.leaf, self.intermediate, self.root)
        ]
        return jwt.encode(payload, self.leaf_key, algorithm="ES256", headers={"x5c": x5c})


TX = {
    "bundleId": "app.letterlens.ios",
    "productId": "app.letterlens.plus.monthly",
    "environment": "Sandbox",
    "originalTransactionId": "1000",
    "expiresDate": int((NOW + timedelta(days=30)).timestamp() * 1000),
    "appAccountToken": "8a2d0f2e-0000-4000-8000-000000000001",
}


def test_valid_transaction() -> None:
    chain = Chain()
    payload = verify_signed_payload(chain.sign(TX), chain.root_der(), NOW)
    ent = entitlement_from_transaction(
        payload, "app.letterlens.ios", "app.letterlens.plus.monthly", "Sandbox", NOW
    )
    assert ent.active and ent.app_account_token == TX["appAccountToken"]


def test_foreign_root_is_rejected() -> None:
    chain, other = Chain(), Chain()
    with pytest.raises(AppStoreVerificationError, match="root"):
        verify_signed_payload(chain.sign(TX), other.root_der(), NOW)


def test_missing_apple_oid_is_rejected() -> None:
    chain = Chain(leaf_oid=None)
    with pytest.raises(AppStoreVerificationError, match="App Store signing"):
        verify_signed_payload(chain.sign(TX), chain.root_der(), NOW)


def test_tampered_payload_is_rejected() -> None:
    chain = Chain()
    header, _, sig = chain.sign(TX).split(".")
    forged = base64.urlsafe_b64encode(b'{"bundleId":"x"}').rstrip(b"=").decode()
    with pytest.raises(AppStoreVerificationError):
        verify_signed_payload(f"{header}.{forged}.{sig}", chain.root_der(), NOW)


