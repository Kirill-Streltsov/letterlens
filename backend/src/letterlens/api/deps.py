"""FastAPI dependencies: services and the authenticated principal."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Annotated

from fastapi import Depends, Request

from letterlens.api.auth import AuthError, authenticate
from letterlens.api.errors import ApiError
from letterlens.billing.service import BillingService
from letterlens.container import Container
from letterlens.services.letters import LetterService
from letterlens.services.principal import Principal, PrincipalResolver
from letterlens.services.sharing import SharingService


@dataclass
class Services:
    container: Container

    @cached_property
    def principals(self) -> PrincipalResolver:
        return PrincipalResolver(self.container.db)

