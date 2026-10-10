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

export function randomVerifier(): string {
  const bytes = new Uint8Array(48);
  crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

export async function challengeFor(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64Url(new Uint8Array(digest));
}

function redirectUri(): string {
  return `${window.location.origin}/auth/callback/`;
}

export function isLocal(config: AppConfig): boolean {
  return config.stage === "local";
}

export async function signIn(devUser?: string): Promise<void> {
  const config = await loadConfig();
  if (isLocal(config)) {
    sessionStorage.setItem(DEV_USER, devUser || "demo-client");
    window.location.assign("/letters/");
    return;
  }
  const verifier = randomVerifier();
  sessionStorage.setItem(VERIFIER, verifier);
  const params = new URLSearchParams({
    response_type: "code",
    client_id: config.clientId,
    redirect_uri: redirectUri(),
    scope: "openid email profile",
    code_challenge_method: "S256",
    code_challenge: await challengeFor(verifier),
  });
  window.location.assign(`https://${config.authDomain}/oauth2/authorize?${params}`);
}

async function tokenRequest(config: AppConfig, body: Record<string, string>): Promise<Tokens> {
  const response = await fetch(`https://${config.authDomain}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ client_id: config.clientId, ...body }),
  });
  if (!response.ok) throw new Error("sign-in failed");
  const json = (await response.json()) as { access_token: string; refresh_token?: string; expires_in: number };
  const tokens: Tokens = {
    accessToken: json.access_token,
    refreshToken: json.refresh_token ?? body.refresh_token,
    expiresAt: Date.now() + json.expires_in * 1000,
  };
  sessionStorage.setItem(STORE, JSON.stringify(tokens));
  return tokens;
}

export async function completeSignIn(code: string): Promise<void> {
  const config = await loadConfig();
  const verifier = sessionStorage.getItem(VERIFIER);
  if (!verifier) throw new Error("sign-in session expired");
  sessionStorage.removeItem(VERIFIER);
  await tokenRequest(config, {
    grant_type: "authorization_code",
    code,
    code_verifier: verifier,
    redirect_uri: redirectUri(),
  });
}

/** Headers that authenticate an API call, refreshing the access token when it is about to expire. */
export async function authHeaders(): Promise<Record<string, string>> {
  const config = await loadConfig();
  if (isLocal(config)) {
    const user = sessionStorage.getItem(DEV_USER);
    if (!user) return {};
    const groups = sessionStorage.getItem(`${DEV_USER}.groups`) ?? "";
    return { "X-Dev-User": user, ...(groups ? { "X-Dev-Groups": groups } : {}) };
  }
  const raw = sessionStorage.getItem(STORE);
  if (!raw) return {};
  let tokens = JSON.parse(raw) as Tokens;
  if (tokens.expiresAt - Date.now() < 60_000 && tokens.refreshToken) {
    tokens = await tokenRequest(config, { grant_type: "refresh_token", refresh_token: tokens.refreshToken });
  }
  return { Authorization: `Bearer ${tokens.accessToken}` };
}

