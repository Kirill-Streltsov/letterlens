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


