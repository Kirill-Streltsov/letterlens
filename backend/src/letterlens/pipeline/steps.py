"""Pipeline steps. Each step is a pure function of (state, deps) -> state.

The same functions run in-process (local development, tests) and inside the
Step Functions worker Lambda (production). Steps never log letter text.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from letterlens.domain import (
    Citation,
    Explanation,
    ExplanationDraft,
    Extraction,
    LetterType,
    NextStep,
    Passage,
    SummarySentence,
    VerifiedFacts,
)
from letterlens.extraction.rules import extract_with_rules
from letterlens.grounding.german import find_amounts, find_dates
from letterlens.grounding.verifier import verify
from letterlens.i18n import COUNSELLING_HINT, DISCLAIMER, languages, localized
from letterlens.llm import Gateway, Task
from letterlens.llm import prompts as P
from letterlens.llm.providers.fake import FakeProvider
from letterlens.llm.types import LLMError
from letterlens.ml.classifier import LinearModel
from letterlens.pipeline.state import PipelineState
from letterlens.rag.retriever import HybridRetriever
from letterlens.safety.guardrail import is_advisory_output
from letterlens.safety.pii import PiiVault

log = logging.getLogger(__name__)

_URL = re.compile(r"https?://\S+|www\.\S+")
_EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_NUMBER = re.compile(r"\d[\d.,]*\d|\d")


@dataclass(frozen=True)
class PipelineDeps:
    gateway: Gateway
    retriever: HybridRetriever
    classifier: LinearModel


