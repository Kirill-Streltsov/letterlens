"""Verify App Store signed data (StoreKit 2 transactions, Server Notifications V2).

Apple signs JWS payloads with a leaf certificate. The x5c header carries the
chain leaf -> Apple WWDR intermediate -> Apple Root CA - G3. This module
checks the chain against the pinned root certificate bundled with the code,
checks Apple's certificate OIDs and validity dates, and verifies the ES256
signature. It follows the checks of Apple's App Store Server Library.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

ROOT_CERT = Path(__file__).with_name("AppleRootCA-G3.cer")
LEAF_OID = x509.ObjectIdentifier("1.2.840.113635.100.6.11.1")
INTERMEDIATE_OID = x509.ObjectIdentifier("1.2.840.113635.100.6.2.1")


class AppStoreVerificationError(Exception):
    pass


def _b64url(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _verify_signed_by(cert: x509.Certificate, issuer: x509.Certificate) -> None:
    public_key = issuer.public_key()
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise AppStoreVerificationError("unexpected issuer key type")
    hash_alg = cert.signature_hash_algorithm
    if hash_alg is None:
        raise AppStoreVerificationError("certificate has no signature hash")
    try:
        public_key.verify(cert.signature, cert.tbs_certificate_bytes, ec.ECDSA(hash_alg))
    except Exception as exc:
        raise AppStoreVerificationError("certificate chain signature invalid") from exc


