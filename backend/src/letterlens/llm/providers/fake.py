"""Offline, deterministic provider for local development, tests and CI.

It never calls a network. It produces schema-valid outputs from the
structured ``context`` of each request, using the rule-based extractor and
templates. Its quality is the "rules baseline" in evaluation reports.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from letterlens.domain import LetterDocument
from letterlens.extraction.rules import extract_with_rules
from letterlens.llm.types import LLMRequest, LLMResponse, PermanentError, Task
from letterlens.safety.guardrail import Verdict, check_question_rules

_DIRECTION_TEXT = {"to_pay": "to pay", "to_receive": "you receive", "info": "for information"}


class FakeProvider:
    name = "fake"

    def __init__(self, fail_tasks: set[Task] | None = None) -> None:
        self.fail_tasks = fail_tasks or set()
        self.calls: list[LLMRequest] = []

    def complete(self, request: LLMRequest, timeout: float) -> LLMResponse:
        self.calls.append(request)
        if request.task in self.fail_tasks:
            raise PermanentError("fake: configured failure")
        handler = {
            Task.EXTRACT: self._extract,
            Task.EXPLAIN: self._explain,
            Task.ANSWER: self._answer,
            Task.GUARD: self._guard,
            Task.BACKTRANSLATE: self._echo,
            Task.TRANSLATE_REPLY: self._translate,
        }[request.task]
        payload = handler(request.context)
        text = json.dumps(payload, ensure_ascii=False)
        return LLMResponse(
            text=text,
            model=request.model,
            provider=self.name,
            input_tokens=len(request.system + request.user) // 4,
            output_tokens=len(text) // 4,
            latency_ms=1,
        )

    def embed(self, texts: list[str], model: str, timeout: float) -> list[list[float]]:
        return [hash_embedding(t) for t in texts]

    # -- task handlers ------------------------------------------------------

    @staticmethod
    def _extract(ctx: dict[str, Any]) -> dict[str, Any]:
        doc = LetterDocument.model_validate(ctx["document"])
        return extract_with_rules(doc).model_dump(mode="json")

    @staticmethod
    def _explain(ctx: dict[str, Any]) -> dict[str, Any]:
        facts = ctx["facts"]
        passages: list[dict[str, str]] = ctx.get("passages", [])
        sender = (facts.get("sender") or {}).get("value") or "an authority"
        subject = (facts.get("subject") or {}).get("value") or "your case"
        first_line = (facts.get("sender") or {}).get("line_ids") or []
        summary = [
            {"text": f"This letter is from {sender}.", "line_ids": first_line},
