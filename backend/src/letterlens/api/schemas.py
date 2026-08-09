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


class MeResponse(ApiModel):
    id: str
    display_name: str | None
    preferred_language: str
    plan: Literal["free", "plus"]
    plan_expires_at: datetime | None
    letters_this_month: int
    letters_limit: int | None
    memberships: list[MembershipInfo]
    is_platform_admin: bool


class UpdateMeRequest(ApiModel):
    display_name: str | None = Field(default=None, max_length=80)
    preferred_language: str | None = Field(default=None, max_length=8)


# --- Letters --------------------------------------------------------------------


class CreateLetterRequest(ApiModel):
    document: LetterDocument
    language: str = Field(default="en", max_length=8)
    retention_days: int = Field(default=30, ge=1, le=365)


