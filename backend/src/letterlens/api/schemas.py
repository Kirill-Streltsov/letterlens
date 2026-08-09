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


class CreateLetterResponse(ApiModel):
    id: str
    status: LetterStatus
    expires_at: datetime


class UploadTarget(ApiModel):
    key: str
    url: str
    fields: dict[str, str]


class ImageUploadRequest(ApiModel):
    count: int = Field(ge=1, le=6)
    consent: Literal[True]


class ImageUploadResponse(ApiModel):
    targets: list[UploadTarget]


class DeadlineSummary(ApiModel):
    due_date: date | None
    status: str
    label: str


class LetterListItem(ApiModel):
    id: str
    status: LetterStatus
    letter_type: str | None
    headline: str | None
    sender: str | None
    next_deadline: DeadlineSummary | None
    created_at: datetime
    expires_at: datetime
    shared: bool


class ShareInfo(ApiModel):
    id: str
    tenant_id: str
    tenant_name: str
    case_status: str
    expires_at: datetime
    revoked: bool


