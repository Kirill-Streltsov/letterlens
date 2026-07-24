"""Letter use cases for the reader (the client)."""

from __future__ import annotations

import logging
from typing import Any

from letterlens.api.errors import ApiError, bad_request, not_found
from letterlens.api.schemas import (
    CitationOut,
    CreateLetterRequest,
    CreateLetterResponse,
    DeadlineSummary,
    LetterListItem,
    LetterView,
    QuestionResponse,
    ShareInfo,
    dump,
)
from letterlens.container import Container
from letterlens.db import Conn
from letterlens.db import repo as R
from letterlens.domain import FactStatus, LetterStatus
from letterlens.i18n import REFUSAL, is_available, languages, localized
from letterlens.llm import Task
