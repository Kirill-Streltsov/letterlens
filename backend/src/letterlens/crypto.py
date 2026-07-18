"""Envelope encryption for letter content.

KEK (key encryption key): 32 random bytes held by the service only. In AWS it
is an SSM Parameter Store SecureString; locally it is an environment variable.
DEK (data encryption key): 32 random bytes per user, stored wrapped by the KEK
in table user_keys. Content is encrypted with AES-256-GCM. The record id is the
associated data, so a ciphertext cannot be moved to another record.

Deleting a user's row in user_keys makes all of that user's ciphertext
unreadable, including copies in database backups (crypto-shredding).
"""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from letterlens.config import Settings, get_settings

NONCE_BYTES = 12
KEK_VERSION = 1
_DEK_CACHE_SECONDS = 300


class CryptoError(Exception):
    pass


@dataclass(frozen=True)
class Kek:
    key: bytes
    version: int = KEK_VERSION

    def wrap(self, dek: bytes, user_id: str) -> bytes:
        return encrypt(self.key, dek, f"dek:{user_id}")

    def unwrap(self, wrapped: bytes, user_id: str) -> bytes:
        return decrypt(self.key, wrapped, f"dek:{user_id}")


def encrypt(key: bytes, plaintext: bytes, aad: str) -> bytes:
    nonce = os.urandom(NONCE_BYTES)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, aad.encode())


