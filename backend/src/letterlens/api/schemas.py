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


class ErrorBody(ApiModel):
    code: str
    message: str
    request_id: str | None = None


# --- Me -----------------------------------------------------------------------


class LanguageInfo(ApiModel):
    code: str
    name: str
    native_name: str
    rtl: bool
    status: str


class MembershipInfo(ApiModel):
    tenant_id: str
    tenant_name: str
    role: str
    kind: str


