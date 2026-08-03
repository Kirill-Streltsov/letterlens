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


@dataclass
class Container:
    settings: Settings

    @cached_property
    def db(self) -> Database:
        return Database(self.settings.database_url.get_secret_value())

    @cached_property
    def keys(self) -> KeyRing:
        return KeyRing(get_kek())

    @cached_property
    def ledger(self) -> UsageLedger:
        return PgLedger(self.db)

    @cached_property
    def gateway(self) -> Gateway:
        return Gateway(build_provider(self.settings), self.settings, self.ledger)

    @cached_property
    def classifier(self) -> LinearModel:
        return default_model()

    @cached_property
    def retriever(self) -> HybridRetriever:
        index = EmbeddingIndex.load()
        use_dense = index is not None and index.model == self.settings.embedding_model
        return HybridRetriever(
            index=index if use_dense else None,
            embedder=self.gateway.embed if use_dense else None,
        )

    @cached_property
    def deps(self) -> PipelineDeps:
        return PipelineDeps(self.gateway, self.retriever, self.classifier)

    @cached_property
    def state_store(self) -> PgStateStore:
        return PgStateStore(self.db, self.keys)

    @cached_property
    def runner(self) -> Runner:
        if self.settings.pipeline_runner is PipelineRunner.STEPFUNCTIONS:
            return StepFunctionsRunner(self.settings.state_machine_arn)
        return InProcessRunner(self.state_store, lambda: self.deps)

    @cached_property
    def storage(self) -> ImageStorage:
        if self.settings.letters_bucket:
            return S3Storage(self.settings.letters_bucket, self.settings.aws_region)
        return DisabledStorage()
