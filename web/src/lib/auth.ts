/**
 * Sign-in with the Cognito hosted UI: OAuth 2.0 authorization code flow with PKCE.
 * No client secret exists in the browser. Tokens live in sessionStorage and are
 * cleared when the tab closes. In local development a "dev user" header replaces tokens.
 */

import { type AppConfig, loadConfig } from "./config";

const STORE = "letterlens.auth";
const VERIFIER = "letterlens.pkce";
const DEV_USER = "letterlens.devUser";

export interface Tokens {
  accessToken: string;
  refreshToken?: string;
  expiresAt: number;
}

export function base64Url(bytes: Uint8Array): string {
  let s = "";
  bytes.forEach((b) => (s += String.fromCharCode(b)));
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

