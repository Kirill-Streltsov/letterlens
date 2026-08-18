"""API integration tests: HTTP -> services -> PostgreSQL (RLS on) -> offline pipeline."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from letterlens.api.app import create_app
from letterlens.config import Settings
from letterlens.db import DbContext
from letterlens.db import repo as R
from letterlens.synthetic import generate_corpus, to_document

pytestmark = pytest.mark.db
WEBHOOK_SECRET = "whsec_test_secret"


