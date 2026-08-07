"""Request and response models of the public API (OpenAPI source of truth)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from letterlens.domain import (
    Classification,
    Explanation,
    LetterDocument,
    LetterStatus,
    OcrLine,
    VerifiedFacts,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


