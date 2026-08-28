"""In-process pipeline with the offline provider, including degraded mode and output sanitizing."""

from __future__ import annotations

import pytest

from letterlens.config import Settings
from letterlens.domain import ExplanationDraft, FactLabel, LetterStatus, NextStep, SummarySentence
from letterlens.llm import Gateway, InMemoryLedger, Task
from letterlens.llm.providers.fake import FakeProvider
from letterlens.ml.classifier import default_model
from letterlens.pipeline.runner import EXPLAIN_ONLY, InProcessRunner
from letterlens.pipeline.state import InMemoryStateStore, PipelineState
from letterlens.pipeline.steps import PipelineDeps, sanitize_explanation
from letterlens.rag.retriever import HybridRetriever
from letterlens.safety.pii import PiiVault
from letterlens.synthetic import generate_corpus, to_document


