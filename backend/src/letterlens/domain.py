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


