"""HTTP routes. Thin: validate input, call a service, shape the response."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header, Query, Request, Response

from letterlens.api.deps import PrincipalDep, ServicesDep
from letterlens.api.errors import ApiError, forbidden
from letterlens.api.schemas import (
    AppStoreTransactionRequest,
    CaseDetail,
    CaseItem,
    CaseUpdate,
    CheckoutRequest,
    CheckoutResponse,
    CostRow,
    CounsellingService,
    CreateLetterRequest,
    CreateLetterResponse,
    ExplanationRequest,
    ImageUploadRequest,
    ImageUploadResponse,
    InviteRequest,
    InviteResponse,
    LanguageInfo,
    LetterCost,
    LetterListItem,
    LetterView,
    MembershipInfo,
    MeResponse,
    MessageOut,
    MessageRequest,
    PlanResponse,
    QuestionRequest,
    QuestionResponse,
    RedeemRequest,
    RetentionRequest,
    ShareInfo,
    ShareRequest,
    StatsRow,
    TranslateRequest,
    TranslateResponse,
    UpdateMeRequest,
    UploadTarget,
)
from letterlens.db import DbContext
from letterlens.db import repo as R
from letterlens.i18n import languages
from letterlens.pipeline.runner import EXPLAIN_ONLY
from letterlens.services.sharing import COUNSELLOR_LANGUAGE

router = APIRouter(prefix="/v1")
public = APIRouter()

IdempotencyKey = Annotated[str | None, Header(alias="Idempotency-Key", max_length=80)]


@public.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/languages", response_model=list[LanguageInfo], tags=["me"])
def list_languages() -> list[LanguageInfo]:
    return [
        LanguageInfo(code=l.code, name=l.name, native_name=l.native_name, rtl=l.rtl, status=l.status.value)
        for l in languages().values()
        if l.status.value != "disabled"
    ]


# --- me ---------------------------------------------------------------------------------


@router.get("/me", response_model=MeResponse, tags=["me"])
def me(principal: PrincipalDep, services: ServicesDep) -> MeResponse:
    settings = services.container.settings
    with services.container.db.session(principal.ctx) as conn:
        used = R.letters_this_month(conn, principal.user_id)
    return MeResponse(
        id=principal.user_id,
        display_name=principal.user.get("display_name"),
        preferred_language=principal.user["preferred_language"],
        plan=principal.plan,  # type: ignore[arg-type]
        plan_expires_at=principal.user.get("plan_expires_at"),
        letters_this_month=used,
        letters_limit=None if principal.plan == "plus" else settings.free_letters_per_month,
        memberships=[
            MembershipInfo(tenant_id=m.tenant_id, tenant_name=m.name, role=m.role, kind=m.kind)
            for m in principal.memberships
        ],
        is_platform_admin=principal.is_platform_admin,
    )


@router.patch("/me", status_code=204, tags=["me"])
def update_me(body: UpdateMeRequest, principal: PrincipalDep, services: ServicesDep) -> Response:
    if body.preferred_language and body.preferred_language not in languages():
        raise ApiError(400, "language_unavailable", "unknown language")
    with services.container.db.session(principal.ctx) as conn:
        R.update_user(conn, principal.user_id, **body.model_dump(exclude_none=True))
    services.principals.invalidate(principal.identity.sub)
    return Response(status_code=204)


@router.delete("/me", status_code=204, tags=["me"])
def delete_me(principal: PrincipalDep, services: ServicesDep) -> Response:
    """Delete the account and all letters. The data key is destroyed (crypto-shredding)."""
    with services.container.db.session(principal.ctx) as conn:
        R.audit(conn, principal.user_id, "account.delete", "user", principal.user_id)
        keys = R.delete_user(conn, principal.user_id)
    services.container.keys.cache.drop(principal.user_id)
    services.container.storage.delete(keys)
    services.principals.invalidate(principal.identity.sub)
    return Response(status_code=204)


