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


class LetterView(ApiModel):
    id: str
    status: LetterStatus
    error: str | None
    language: str
    created_at: datetime
    expires_at: datetime
    lines: list[OcrLine]
    classification: Classification | None
    facts: VerifiedFacts | None
    explanation: Explanation | None
    explanation_languages: list[str]
    degraded: bool
    degraded_reasons: list[str]
    image_urls: list[str]
    shares: list[ShareInfo]


class ExplanationRequest(ApiModel):
    language: str = Field(max_length=8)


class RetentionRequest(ApiModel):
    retention_days: int = Field(ge=1, le=365)


class QuestionRequest(ApiModel):
    question: str = Field(min_length=3, max_length=600)
    language: str = Field(default="en", max_length=8)


class CitationOut(ApiModel):
    id: str
    title: str
    source_url: str
    source_name: str
    checked_on: date


class QuestionResponse(ApiModel):
    answer: str | None
    refused: bool
    reason: Literal["legal_advice", "prompt_injection", "off_topic", "unverified"] | None
    handover_suggested: bool
    line_ids: list[str]
    citations: list[CitationOut]


# --- Sharing and messages ----------------------------------------------------------


CONSENT_VERSION = "share-consent-v1"


class CounsellingService(ApiModel):
    id: str
    name: str
    city: str | None
    languages: list[str]


class ShareRequest(ApiModel):
    tenant_id: str
    consent: Literal[True]
    consent_text_version: Literal["share-consent-v1"]
    days: int = Field(default=30, ge=1, le=90)


class MessageOut(ApiModel):
    id: str
    author_role: Literal["client", "counsellor"]
    text: str
    original_text: str | None
    created_at: datetime


