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


