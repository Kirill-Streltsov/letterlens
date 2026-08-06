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

    @cached_property
    def letters(self) -> LetterService:
        return LetterService(self.container)

    @cached_property
    def sharing(self) -> SharingService:
        return SharingService(self.container, self.letters)

    @cached_property
    def billing(self) -> BillingService:
        return BillingService(self.container)


def get_services(request: Request) -> Services:
    services: Services = request.app.state.services
    return services


ServicesDep = Annotated[Services, Depends(get_services)]


def get_principal(request: Request, services: ServicesDep) -> Principal:
    headers = {k.lower(): v for k, v in request.headers.items()}
    try:
        identity = authenticate(headers, services.container.settings)
    except AuthError as exc:
        raise ApiError(401, "unauthorized", "authentication required") from exc
    return services.principals.resolve(identity)


PrincipalDep = Annotated[Principal, Depends(get_principal)]
