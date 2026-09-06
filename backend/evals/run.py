"""Evaluation suite and release gate.

Usage
  uv run python -m evals.run                       # offline profile (rules baseline), all suites
  uv run python -m evals.run --profile chaos       # fault injection: the model invents dates/amounts
  LETTERLENS_LLM_PROVIDER=mistral LETTERLENS_LLM_API_KEY=... \
  uv run python -m evals.run --profile live        # real model, adds the faithfulness suite
  uv run python -m evals.run --update-languages    # with --profile live: write language status

Exit code 1 when a gate in evals/thresholds.yaml fails. CI runs the offline and
chaos profiles on every pull request (.github/workflows/ci.yml).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from evals.handwritten import HANDWRITTEN
from letterlens.config import Settings
from letterlens.domain import FactStatus
from letterlens.llm import Gateway, InMemoryLedger, Task, build_provider
from letterlens.llm import prompts as P
from letterlens.llm.outputs import BackTranslation as _BackText
from letterlens.llm.outputs import GuardDecision
from letterlens.llm.providers.fake import FakeProvider
from letterlens.llm.types import LLMRequest, LLMResponse
from letterlens.ml.classifier import default_model
from letterlens.pipeline.state import InMemoryStateStore, PipelineState
from letterlens.pipeline.steps import STEP_FUNCTIONS, PipelineDeps, explain
from letterlens.rag.retriever import HybridRetriever
from letterlens.safety.guardrail import Verdict, check_question_rules
from letterlens.synthetic import SyntheticLetter, generate_corpus, to_document
from letterlens.synthetic.generator import AmountLabel, DeadlineLabel

ROOT = Path(__file__).resolve().parent
GOLDEN = ROOT / "golden" / "letters.jsonl"
REDTEAM = ROOT / "redteam" / "questions.jsonl"
THRESHOLDS = ROOT / "thresholds.yaml"
REPORTS = ROOT / "reports"
EXPLICIT_KINDS = {"explicit_date", "appointment"}

# Which corpus passages a good retrieval returns for each letter family.
EXPECTED_PASSAGES: dict[str, set[str]] = {
    "tax_assessment": {"tax-objection"},
    "tax_reminder": {"tax-return-reminder"},
    "tax_arrears": {"tax-late-payment"},
    "jobcenter_approval": {"benefits-objection"},
    "jobcenter_documents": {"cooperation-duty"},
    "jobcenter_invitation": {"jobcenter-appointment"},
    "familienkasse_refund": {"benefits-repayment", "tax-objection"},
    "insurance_arrears": {"health-arrears"},
    "insurance_questionnaire": {"family-insurance"},
    "insurance_rejection": {"benefits-objection"},
    "immigration_appointment": {"residence-renewal"},
    "immigration_hearing": {"hearing-letter"},
    "immigration_fiction": {"residence-renewal"},
    "landlord_utility_statement": {"utility-statement"},
    "landlord_rent_increase": {"rent-increase"},
    "landlord_reminder": {"rent-arrears"},
    "broadcast_fee": {"broadcast-fee"},
    "collection_agency": {"debt-collection"},
    "handwritten-court-order": {"court-payment-order"},
    "handwritten-termination": {"tenancy-termination"},
    "handwritten-jobcenter-change": {"benefits-repayment", "benefits-objection"},
    "handwritten-kindergeld-school": {"cooperation-duty"},
    "handwritten-sick-pay": {"benefits-objection"},
    "handwritten-injection": {"rent-arrears"},
}


