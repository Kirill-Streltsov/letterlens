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

