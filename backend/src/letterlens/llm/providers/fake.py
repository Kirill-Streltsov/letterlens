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
            {
                "text": f"The subject is: {subject}.",
                "line_ids": (facts.get("subject") or {}).get("line_ids") or [],
            },
        ]
        for d in facts.get("deadlines", []):
            when = d.get("due_date") or "a date that you must check"
            check = " Please check this date in the original." if d["status"] != "verified" else ""
            summary.append({"text": f"Deadline: {when}.{check}", "line_ids": d["line_ids"]})
        for a in facts.get("amounts", [])[:3]:
            label = _DIRECTION_TEXT.get(a["direction"], "")
            summary.append({"text": f"Amount {label}: {a['value']} EUR.", "line_ids": a["line_ids"]})
        next_steps = [
            {"text": f"General information: {p['title']}.", "citation_ids": [p["id"]]}
            for p in passages[:3]
        ]
        return {
            "headline": f"Letter from {sender}",
            "letter_kind": f"{ctx.get('letter_type', 'other')} letter from {sender}",
            "summary": summary[:6],
            "next_steps": next_steps,
            "deadline_labels": [
                {"id": d["id"], "label": d["description"]} for d in facts.get("deadlines", [])
            ],
            "amount_labels": [
                {"id": a["id"], "label": a["description"][:60]} for a in facts.get("amounts", [])
            ],
        }

    @staticmethod
    def _answer(ctx: dict[str, Any]) -> dict[str, Any]:
        question = ctx.get("question", "")
        if check_question_rules(question).blocked:
            return {"answer": "", "line_ids": [], "citation_ids": [], "refused": True}
        passages = ctx.get("passages", [])
        cite = [passages[0]["id"]] if passages else []
        title = passages[0]["title"] if passages else "this kind of letter"
        return {
            "answer": f"General information about {title}. The letter itself names the details.",
            "line_ids": [],
            "citation_ids": cite,
            "refused": False,
        }

    @staticmethod
    def _guard(ctx: dict[str, Any]) -> dict[str, Any]:
        result = check_question_rules(ctx.get("question", ""))
        category = {
            Verdict.ALLOW: "general_information",
            Verdict.LEGAL_ADVICE: "individual_legal_advice",
            Verdict.INJECTION: "prompt_injection",
        }[result.verdict]
        return {"category": category, "rationale": f"offline rules ({result.layer})"}

    @staticmethod
    def _echo(ctx: dict[str, Any]) -> dict[str, Any]:
        return {"text": ctx.get("text", "")}

    @staticmethod
    def _translate(ctx: dict[str, Any]) -> dict[str, Any]:
        return {"translation": f"[{ctx.get('language', 'en')}] {ctx.get('text', '')}"}


def hash_embedding(text: str, dim: int = 256) -> list[float]:
    """Deterministic bag-of-words vector. Only for tests; it has no semantic quality."""
    vec = [0.0] * dim
    for token in re.findall(r"\w{3,}", text.lower()):
        h = int(hashlib.blake2b(token.encode(), digest_size=8).hexdigest(), 16)
        vec[h % dim] += 1.0 if (h >> 8) % 2 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
