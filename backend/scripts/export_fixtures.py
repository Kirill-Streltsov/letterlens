"""Write real API responses to contracts/fixtures/ for client contract tests (iOS, web).

Needs the local database (make migrate). tests/test_contract_fixtures.py checks that
the committed fixtures still validate against the current response models.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from letterlens.api.app import create_app
from letterlens.config import Settings
from letterlens.db import DbContext
from letterlens.db import repo as R
from letterlens.synthetic import generate_corpus, to_document

