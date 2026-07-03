"""Pipeline state, persisted (encrypted) between steps."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from letterlens.domain import (
    Classification,
    Explanation,
    Extraction,
    LetterDocument,
    LetterStatus,
    Passage,
    VerifiedFacts,
)

STEPS = ("classify", "extract", "verify", "retrieve", "explain", "finalize")


class PipelineState(BaseModel):
    letter_id: str
    owner_id: str
    language: str = "en"
    document: LetterDocument
    classification: Classification | None = None
    extraction: Extraction | None = None
    facts: VerifiedFacts | None = None
    passages: list[Passage] | None = None
    explanations: dict[str, Explanation] = Field(default_factory=dict)
    degraded: bool = False
    degraded_reasons: list[str] = Field(default_factory=list)

    def mark_degraded(self, reason: str) -> None:
        self.degraded = True
        if reason not in self.degraded_reasons:
            self.degraded_reasons.append(reason)


class StateStore(Protocol):
    def load_state(self, letter_id: str) -> PipelineState: ...

    def save_state(self, state: PipelineState) -> None: ...

    def set_status(self, letter_id: str, status: LetterStatus, error: str | None = None) -> None: ...


class InMemoryStateStore:
    def __init__(self) -> None:
        self.states: dict[str, PipelineState] = {}
        self.status: dict[str, tuple[LetterStatus, str | None]] = {}

    def load_state(self, letter_id: str) -> PipelineState:
        return self.states[letter_id].model_copy(deep=True)

    def save_state(self, state: PipelineState) -> None:
        self.states[state.letter_id] = state.model_copy(deep=True)

    def set_status(self, letter_id: str, status: LetterStatus, error: str | None = None) -> None:
        self.status[letter_id] = (status, error)
