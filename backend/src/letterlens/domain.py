"""Domain types shared by the pipeline, the API and the evaluation suite."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

LineId = Annotated[str, StringConstraints(pattern=r"^p\d+-l\d+$")]


class LetterType(StrEnum):
    TAX = "tax"
    BENEFITS = "benefits"
    HEALTH_INSURANCE = "health_insurance"
    IMMIGRATION = "immigration"
    LANDLORD = "landlord"
    OTHER = "other"


class LetterStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class FactStatus(StrEnum):
    """Trust state of one extracted fact.

    VERIFIED: the value occurs in the cited source line.
    NEEDS_CHECK: the value is estimated, or the source line does not contain it.
    The client shows NEEDS_CHECK facts as "please check", never as facts.
    """

    VERIFIED = "verified"
    NEEDS_CHECK = "needs_check"


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --------------------------------------------------------------------------
# Input
# --------------------------------------------------------------------------


class BBox(Frozen):
    """Normalized bounding box. The origin is the top-left corner of the page."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(ge=0, le=1)
    h: float = Field(ge=0, le=1)


class OcrLine(Frozen):
    page: int = Field(ge=1, le=50)
    index: int = Field(ge=1, le=500)
    text: str = Field(max_length=2000)
    bbox: BBox | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)

    @property
    def id(self) -> str:
        return f"p{self.page}-l{self.index}"


class LetterDocument(Frozen):
    """The OCR result of one letter. Clients produce it on the device."""

    lines: list[OcrLine] = Field(min_length=1, max_length=2000)
    ocr_engine: str = Field(default="unknown", max_length=64)

    def line_map(self) -> dict[str, OcrLine]:
        return {line.id: line for line in self.lines}

    def as_numbered_text(self) -> str:
        return "\n".join(f"[{line.id}] {line.text}" for line in self.lines)

    def plain_text(self) -> str:
        return "\n".join(line.text for line in self.lines)


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------


class Classification(Frozen):
    letter_type: LetterType
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[LetterType, float]
    model_version: str
    abstained: bool = False


# --------------------------------------------------------------------------
# Extraction (LLM output, before verification)
# --------------------------------------------------------------------------


class ExtractedText(Frozen):
    value: str | None
    line_ids: list[str]


class ExtractedReference(Frozen):
    label: str
    value: str
    line_ids: list[str]


class ExtractedDate(Frozen):
    value: str | None = Field(description="ISO date YYYY-MM-DD as written in the letter")
    line_ids: list[str]


class ExtractedDeadline(Frozen):
    kind: str = Field(description="explicit_date | relative")
    date: str | None = Field(description="ISO date for explicit deadlines, else null")
    relative_expression: str | None = Field(
        description="The German period text for relative deadlines, else null"
    )
    description: str = Field(description="Short English description of what is due")
    line_ids: list[str]


class ExtractedAmount(Frozen):
    value: str = Field(description="Decimal with a dot, for example 1234.56")
    currency: str
    description: str
    direction: str = Field(description="to_pay | to_receive | info")
    line_ids: list[str]


class ExtractedAction(Frozen):
    description: str
    line_ids: list[str]


