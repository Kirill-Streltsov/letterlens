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

