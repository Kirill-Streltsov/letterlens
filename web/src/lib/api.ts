/** Typed API client. Types come from contracts/openapi.json (npm run gen:api). */

import type { components } from "./api-types";
import { authHeaders } from "./auth";
import { loadConfig } from "./config";

export type Schemas = components["schemas"];
export type LetterView = Schemas["LetterView"];
export type LetterListItem = Schemas["LetterListItem"];
export type Me = Schemas["MeResponse"];
export type Language = Schemas["LanguageInfo"];
export type QuestionResponse = Schemas["QuestionResponse"];
export type CaseItem = Schemas["CaseItem"];
export type CaseDetail = Schemas["CaseDetail"];
export type Message = Schemas["MessageOut"];
export type CounsellingService = Schemas["CounsellingService"];
export type StatsRow = Schemas["StatsRow"];
export type LetterDocument = Schemas["LetterDocument"];
export type VerifiedDeadline = Schemas["VerifiedDeadline"];

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(method: string, path: string, body?: unknown, extra?: Record<string, string>): Promise<T> {
  const config = await loadConfig();
  const headers: Record<string, string> = { ...(await authHeaders()), ...extra };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(`${config.apiBase}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return undefined as T;
  const json = (await response.json().catch(() => ({}))) as { code?: string; message?: string };
  if (!response.ok) {
    throw new ApiError(response.status, json.code ?? "error", json.message ?? response.statusText);
  }
  return json as T;
}

export const api = {
  me: () => request<Me>("GET", "/v1/me"),
  updateMe: (body: Schemas["UpdateMeRequest"]) => request<void>("PATCH", "/v1/me", body),
  deleteMe: () => request<void>("DELETE", "/v1/me"),
  exportMe: () => request<Record<string, unknown>>("GET", "/v1/me/export"),
  languages: () => request<Language[]>("GET", "/v1/languages"),

  letters: () => request<LetterListItem[]>("GET", "/v1/letters"),
  letter: (id: string, lang: string) => request<LetterView>("GET", `/v1/letters/${id}?lang=${encodeURIComponent(lang)}`),
  createLetter: (document: LetterDocument, language: string, idempotencyKey: string) =>
    request<Schemas["CreateLetterResponse"]>("POST", "/v1/letters", { document, language }, {
      "Idempotency-Key": idempotencyKey,
    }),
  deleteLetter: (id: string) => request<void>("DELETE", `/v1/letters/${id}`),
  explain: (id: string, language: string) => request<{ started: boolean }>("POST", `/v1/letters/${id}/explanations`, { language }),
  ask: (id: string, question: string, language: string) =>
    request<QuestionResponse>("POST", `/v1/letters/${id}/questions`, { question, language }),

  services: () => request<CounsellingService[]>("GET", "/v1/counselling-services"),
  share: (id: string, tenantId: string) =>
    request<Schemas["ShareInfo"]>("POST", `/v1/letters/${id}/shares`, {
      tenant_id: tenantId,
      consent: true,
      consent_text_version: "share-consent-v1",
    }),
  revokeShare: (shareId: string) => request<void>("DELETE", `/v1/shares/${shareId}`),
  messages: (shareId: string) => request<Message[]>("GET", `/v1/shares/${shareId}/messages`),
  sendMessage: (shareId: string, text: string) => request<Message>("POST", `/v1/shares/${shareId}/messages`, { text }),
  redeemInvite: (code: string) => request<void>("POST", "/v1/invites/redeem", { code }),

  cases: (status?: string) => request<CaseItem[]>("GET", `/v1/counsellor/cases${status ? `?status=${status}` : ""}`),
  caseDetail: (shareId: string) => request<CaseDetail>("GET", `/v1/counsellor/cases/${shareId}`),
  updateCase: (shareId: string, body: Schemas["CaseUpdate"]) => request<void>("PATCH", `/v1/counsellor/cases/${shareId}`, body),
  translate: (text: string, language: string) =>
    request<Schemas["TranslateResponse"]>("POST", "/v1/counsellor/translate", { text, language }),
  stats: (tenantId: string, months = 12) => request<StatsRow[]>("GET", `/v1/counsellor/tenants/${tenantId}/stats?months=${months}`),
  invite: (tenantId: string) => request<Schemas["InviteResponse"]>("POST", "/v1/counsellor/invites", { tenant_id: tenantId }),

  checkout: (product: "plus" | "seats", tenantId?: string, quantity = 1) =>
    request<{ url: string }>("POST", "/v1/billing/checkout", { product, tenant_id: tenantId ?? null, quantity }),
};
