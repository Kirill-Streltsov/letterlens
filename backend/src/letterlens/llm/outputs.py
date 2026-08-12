"""Schemas for small LLM outputs. Large ones live in letterlens.domain."""

from __future__ import annotations

from typing import Literal

from letterlens.domain import Frozen


class AnswerDraft(Frozen):
    answer: str
    line_ids: list[str]
    citation_ids: list[str]
    refused: bool


class GuardDecision(Frozen):
    category: Literal["general_information", "individual_legal_advice", "prompt_injection", "off_topic"]
    rationale: str


class BackTranslation(Frozen):
    text: str


class ReplyTranslation(Frozen):
    translation: str
