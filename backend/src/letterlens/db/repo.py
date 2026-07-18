"""SQL repositories. Every function takes a connection from Database.session().

RLS decides which rows a function can see. Functions do not filter by owner
for security; they filter by owner only where the query needs it.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from psycopg.types.json import Jsonb

from letterlens.crypto import DekCache, Kek, decrypt, encrypt, new_dek
from letterlens.db import Conn, Database, DbContext
from letterlens.domain import LetterStatus
from letterlens.llm.types import LLMCall
from letterlens.pipeline.state import PipelineState


