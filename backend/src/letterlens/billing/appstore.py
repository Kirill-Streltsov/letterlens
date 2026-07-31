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


def _has_extension(cert: x509.Certificate, oid: x509.ObjectIdentifier) -> bool:
    try:
        cert.extensions.get_extension_for_oid(oid)
    except x509.ExtensionNotFound:
        return False
    return True


def verify_signed_payload(
    token: str, root_der: bytes | None = None, now: datetime | None = None
) -> dict[str, Any]:
    root_der = root_der if root_der is not None else ROOT_CERT.read_bytes()
    now = now or datetime.now(UTC)
    try:
        header = json.loads(_b64url(token.split(".")[0]))
    except (ValueError, IndexError) as exc:
        raise AppStoreVerificationError("malformed JWS") from exc
    if header.get("alg") != "ES256":
        raise AppStoreVerificationError("unexpected algorithm")
    chain_b64 = header.get("x5c") or []
    if len(chain_b64) != 3:
        raise AppStoreVerificationError("x5c must contain three certificates")
    leaf, intermediate, root = (x509.load_der_x509_certificate(base64.b64decode(c)) for c in chain_b64)

    pinned = x509.load_der_x509_certificate(root_der)
    if root.fingerprint(hashes.SHA256()) != pinned.fingerprint(hashes.SHA256()):
        raise AppStoreVerificationError("root certificate is not Apple Root CA - G3")
    _verify_signed_by(intermediate, pinned)
    _verify_signed_by(leaf, intermediate)
    if not _has_extension(leaf, LEAF_OID) or not _has_extension(intermediate, INTERMEDIATE_OID):
        raise AppStoreVerificationError("certificate is not an App Store signing certificate")
    for cert in (leaf, intermediate):
        if not cert.not_valid_before_utc <= now <= cert.not_valid_after_utc:
            raise AppStoreVerificationError("certificate is outside its validity period")

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            key=leaf.public_key(),  # type: ignore[arg-type]
            algorithms=["ES256"],
            options={"verify_aud": False, "verify_exp": False, "verify_iat": False},
        )
    except jwt.PyJWTError as exc:
        raise AppStoreVerificationError("JWS signature invalid") from exc
    return payload


