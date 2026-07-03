"""Pipeline state, persisted (encrypted) between steps."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from letterlens.domain import (
    Classification,
    Explanation,
    Extraction,
    LetterDocument,
    LetterStatus,
    Passage,
    VerifiedFacts,
)

STEPS = ("classify", "extract", "verify", "retrieve", "explain", "finalize")


