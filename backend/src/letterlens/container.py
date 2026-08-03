"""Composition root: builds the long-lived objects once per process (or Lambda container)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from letterlens.config import PipelineRunner, Settings
from letterlens.crypto import get_kek
from letterlens.db import Database
from letterlens.db.repo import KeyRing, PgLedger, PgStateStore
from letterlens.llm import Gateway, UsageLedger, build_provider
from letterlens.ml.classifier import LinearModel, default_model
from letterlens.pipeline.runner import InProcessRunner, Runner, StepFunctionsRunner
from letterlens.pipeline.steps import PipelineDeps
from letterlens.rag.retriever import EmbeddingIndex, HybridRetriever
from letterlens.storage import DisabledStorage, ImageStorage, S3Storage


