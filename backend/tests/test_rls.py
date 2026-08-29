"""Tenant isolation tests. They run as role letterlens_app with RLS active.

Each test states one isolation rule from docs/security/threat-model.md.
"""

from __future__ import annotations

import psycopg
import pytest

from letterlens.crypto import Kek, new_dek
from letterlens.db import Database, DbContext
from letterlens.db import repo as R
from letterlens.pipeline.state import PipelineState
from letterlens.synthetic import generate_corpus, to_document

pytestmark = pytest.mark.db
KEYS = R.KeyRing(Kek(new_dek()))


