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

