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


class TranslatedItem(Frozen):
    index: int
    text: str


class TranslatedLabel(Frozen):
    id: str
    label: str


class ExplanationTranslation(Frozen):
    """One explanation translated item by item. Code maps the items back by index or id,
    so line links, citations and fact ids stay exactly as in the checked source."""

    headline: str
    letter_kind: str
    summary: list[TranslatedItem]
    next_steps: list[TranslatedItem]
    deadline_labels: list[TranslatedLabel]
    amount_labels: list[TranslatedLabel]
