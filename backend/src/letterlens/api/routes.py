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
        plan=principal.plan,
        plan_expires_at=principal.user.get("plan_expires_at"),
        letters_this_month=used,
        letters_limit=None if principal.plan == "plus" else settings.free_letters_per_month,
        memberships=[
            MembershipInfo(tenant_id=m.tenant_id, tenant_name=m.name, role=m.role, kind=m.kind)
            for m in principal.memberships
        ],
        is_platform_admin=principal.is_platform_admin,
        plus_checkout_available=settings.stripe_secret_key is not None and bool(settings.stripe_price_plus),
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
    """Delete the account and all letters. The data key is destroyed (crypto-shredding).

    The sign-in account (email address, password hash) is deleted last. If that call fails, the
    request fails and can be repeated: the next sign-in finds no data and deletion runs again.
    """
    with services.container.db.session(principal.ctx) as conn:
        R.audit(conn, principal.user_id, "account.delete", "user", principal.user_id)
        keys = R.delete_user(conn, principal.user_id)
    services.container.keys.cache.drop(principal.user_id)
    services.container.storage.delete(keys)
    services.principals.invalidate(principal.identity.sub)
    services.container.directory.delete_user(principal.identity.sub)
    return Response(status_code=204)


@router.get("/me/export", tags=["me"])
def export_me(principal: PrincipalDep, services: ServicesDep) -> dict[str, object]:
    """GDPR Art. 20 export: all letters with their results, as JSON."""
    letters = []
    with services.container.db.session(principal.ctx) as conn:
        for row in R.list_letters(conn, principal.user_id, limit=1000):
            letters.append(
                services.letters.view(conn, row["id"], row["language"], include_images=False).model_dump(
                    mode="json"
                )
            )
    return {"user_id": principal.user_id, "letters": letters}


# --- letters --------------------------------------------------------------------------------


@router.post("/letters", status_code=202, response_model=CreateLetterResponse, tags=["letters"])
def create_letter(
    body: CreateLetterRequest,
    principal: PrincipalDep,
    services: ServicesDep,
    background: BackgroundTasks,
    idempotency_key: IdempotencyKey = None,
) -> CreateLetterResponse:
    response, start = services.letters.create(principal, body, idempotency_key)
    if start:
        background.add_task(services.container.runner.start, response.id)
    return response


@router.get("/letters", response_model=list[LetterListItem], tags=["letters"])
def list_letters(principal: PrincipalDep, services: ServicesDep) -> list[LetterListItem]:
    return services.letters.list_for(principal)


@router.get("/letters/{letter_id}", response_model=LetterView, tags=["letters"])
def get_letter(
    letter_id: str,
    principal: PrincipalDep,
    services: ServicesDep,
    lang: Annotated[str, Query(max_length=8)] = "en",
) -> LetterView:
    return services.letters.get(principal, _uuid(letter_id), lang)


@router.post("/letters/{letter_id}/explanations", status_code=202, tags=["letters"])
def request_explanation(
    letter_id: str,
    body: ExplanationRequest,
    principal: PrincipalDep,
    services: ServicesDep,
    background: BackgroundTasks,
) -> dict[str, bool]:
    start = services.letters.request_explanation(principal, _uuid(letter_id), body.language)
    if start:
        background.add_task(services.container.runner.start, letter_id, EXPLAIN_ONLY, body.language)
    return {"started": start}


@router.patch("/letters/{letter_id}", status_code=204, tags=["letters"])
def update_letter(
    letter_id: str, body: RetentionRequest, principal: PrincipalDep, services: ServicesDep
) -> Response:
    services.letters.set_retention(principal, _uuid(letter_id), body.retention_days)
    return Response(status_code=204)


@router.delete("/letters/{letter_id}", status_code=204, tags=["letters"])
def delete_letter(letter_id: str, principal: PrincipalDep, services: ServicesDep) -> Response:
    services.letters.delete(principal, _uuid(letter_id))
    return Response(status_code=204)


@router.post("/letters/{letter_id}/images", response_model=ImageUploadResponse, tags=["letters"])
def upload_images(
    letter_id: str, body: ImageUploadRequest, principal: PrincipalDep, services: ServicesDep
) -> ImageUploadResponse:
    targets = services.letters.image_targets(principal, _uuid(letter_id), body.count)
    return ImageUploadResponse(targets=[UploadTarget(**t) for t in targets])


@router.post("/letters/{letter_id}/questions", response_model=QuestionResponse, tags=["letters"])
def ask_question(
    letter_id: str, body: QuestionRequest, principal: PrincipalDep, services: ServicesDep
) -> QuestionResponse:
    return services.letters.ask(principal, _uuid(letter_id), body.question, body.language)


# --- sharing ------------------------------------------------------------------------------


@router.get("/counselling-services", response_model=list[CounsellingService], tags=["sharing"])
def counselling_services(
    principal: PrincipalDep, services: ServicesDep, city: Annotated[str | None, Query(max_length=80)] = None
) -> list[CounsellingService]:
    return services.sharing.services(principal, city)


@router.post("/letters/{letter_id}/shares", status_code=201, response_model=ShareInfo, tags=["sharing"])
def share_letter(
    letter_id: str,
    body: ShareRequest,
    principal: PrincipalDep,
    services: ServicesDep,
    background: BackgroundTasks,
) -> ShareInfo:
    info, needs_german = services.sharing.share(principal, _uuid(letter_id), body)
    if needs_german:
        background.add_task(services.container.runner.start, letter_id, EXPLAIN_ONLY, COUNSELLOR_LANGUAGE)
    return info


@router.delete("/shares/{share_id}", status_code=204, tags=["sharing"])
def revoke_share(share_id: str, principal: PrincipalDep, services: ServicesDep) -> Response:
    services.sharing.revoke(principal, _uuid(share_id))
    return Response(status_code=204)


@router.get("/shares/{share_id}/messages", response_model=list[MessageOut], tags=["sharing"])
def list_messages(share_id: str, principal: PrincipalDep, services: ServicesDep) -> list[MessageOut]:
    return services.sharing.messages(principal, _uuid(share_id))


@router.post("/shares/{share_id}/messages", status_code=201, response_model=MessageOut, tags=["sharing"])
def post_message(
    share_id: str, body: MessageRequest, principal: PrincipalDep, services: ServicesDep
) -> MessageOut:
    return services.sharing.post_message(principal, _uuid(share_id), body.text)


@router.post("/invites/redeem", status_code=204, tags=["sharing"])
def redeem_invite(body: RedeemRequest, principal: PrincipalDep, services: ServicesDep) -> Response:
    services.sharing.redeem(principal, body.code)
    services.principals.invalidate(principal.identity.sub)
    return Response(status_code=204)


# --- counsellor -----------------------------------------------------------------------------


@router.get("/counsellor/cases", response_model=list[CaseItem], tags=["counsellor"])
def cases(
    principal: PrincipalDep,
    services: ServicesDep,
    status: Annotated[str | None, Query(pattern="^(new|in_progress|closed)$")] = None,
) -> list[CaseItem]:
    return services.sharing.cases(principal, status)


@router.get("/counsellor/cases/{share_id}", response_model=CaseDetail, tags=["counsellor"])
def case_detail(share_id: str, principal: PrincipalDep, services: ServicesDep) -> CaseDetail:
    return services.sharing.case(principal, _uuid(share_id))


@router.patch("/counsellor/cases/{share_id}", status_code=204, tags=["counsellor"])
def update_case(share_id: str, body: CaseUpdate, principal: PrincipalDep, services: ServicesDep) -> Response:
    services.sharing.update_case(principal, _uuid(share_id), body.case_status, body.assigned_to)
    return Response(status_code=204)


@router.post("/counsellor/translate", response_model=TranslateResponse, tags=["counsellor"])
def translate(body: TranslateRequest, principal: PrincipalDep, services: ServicesDep) -> TranslateResponse:
    return TranslateResponse(
        translation=services.sharing.translate(principal, body.text, body.language),
        language=body.language,
    )


@router.get("/counsellor/tenants/{tenant_id}/stats", response_model=list[StatsRow], tags=["counsellor"])
def tenant_stats(
    tenant_id: str,
    principal: PrincipalDep,
    services: ServicesDep,
    months: Annotated[int, Query(ge=1, le=24)] = 12,
) -> list[StatsRow]:
    return services.sharing.stats(principal, _uuid(tenant_id), months)


@router.post("/counsellor/invites", response_model=InviteResponse, tags=["counsellor"])
def create_invite(body: InviteRequest, principal: PrincipalDep, services: ServicesDep) -> InviteResponse:
    return services.sharing.invite(principal, _uuid(body.tenant_id), body.role)


# --- billing ---------------------------------------------------------------------------------


@router.post("/billing/checkout", response_model=CheckoutResponse, tags=["billing"])
def checkout(body: CheckoutRequest, principal: PrincipalDep, services: ServicesDep) -> CheckoutResponse:
    return CheckoutResponse(
        url=services.billing.checkout(principal, body.product, body.tenant_id, body.quantity)
    )


@router.post("/billing/stripe/webhook", status_code=204, tags=["billing"])
async def stripe_webhook(request: Request, services: ServicesDep) -> Response:
    payload = await request.body()
    services.billing.stripe_webhook(payload, request.headers.get("stripe-signature"))
    return Response(status_code=204)


@router.post("/billing/appstore/transactions", response_model=PlanResponse, tags=["billing"])
def appstore_transaction(
    body: AppStoreTransactionRequest, principal: PrincipalDep, services: ServicesDep
) -> PlanResponse:
    plan, expires = services.billing.appstore_transaction(principal, body.signed_transaction)
    services.principals.invalidate(principal.identity.sub)
    return PlanResponse(plan=plan, plan_expires_at=expires)


@router.post("/billing/appstore/notifications", status_code=204, tags=["billing"])
async def appstore_notification(request: Request, services: ServicesDep) -> Response:
    body = await request.json()
    services.billing.appstore_notification(str(body.get("signedPayload", "")))
    return Response(status_code=204)


# --- platform admin ----------------------------------------------------------------------------


@router.get("/admin/costs", response_model=list[CostRow], tags=["admin"])
def costs(
    principal: PrincipalDep, services: ServicesDep, days: Annotated[int, Query(ge=1, le=90)] = 14
) -> list[CostRow]:
    if not principal.is_platform_admin:
        raise forbidden("platform admins only")
    with services.container.db.session(DbContext.as_system()) as conn:
        return [CostRow(**r) for r in R.cost_report(conn, days)]


@router.get("/admin/letters/{letter_id}/cost", response_model=LetterCost, tags=["admin"])
def letter_cost(letter_id: str, principal: PrincipalDep, services: ServicesDep) -> LetterCost:
    """Answers: what did this request cost? Readers can query their own letters."""
    lid = _uuid(letter_id)
    ctx = DbContext.as_system() if principal.is_platform_admin else principal.ctx
    with services.container.db.session(ctx) as conn:
        if not principal.is_platform_admin and R.letter_row(conn, lid) is None:
            raise ApiError(404, "not_found", "letter not found")
        return LetterCost(letter_id=lid, **R.letter_cost(conn, lid))


def _uuid(value: str) -> str:
    import uuid

    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise ApiError(404, "not_found", "not found") from exc
