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

