/**
 * Session handling for the web app.
 *
 * Production: the app's own sign-in screens call the Cognito user-pool API (see cognito.ts).
 * Tokens live in sessionStorage and are cleared when the tab closes. The refresh token is
 * revoked on sign-out. In local development a "dev user" header replaces tokens.
 */

import { type AuthResult, CognitoClient } from "./cognito";
import { type AppConfig, loadConfig } from "./config";

const STORE = "letterlens.auth";
const DEV_USER = "letterlens.devUser";

export interface Tokens {
  accessToken: string;
  refreshToken?: string;
  expiresAt: number;
}

export function isLocal(config: AppConfig): boolean {
  return config.stage === "local";
}

export async function cognito(): Promise<CognitoClient> {
  const config = await loadConfig();
  return new CognitoClient(config.region, config.clientId);
}

export function storeSession(result: AuthResult, now = Date.now()): Tokens {
  const tokens: Tokens = {
    accessToken: result.accessToken,
    refreshToken: result.refreshToken,
    expiresAt: now + result.expiresIn * 1000,
  };
  sessionStorage.setItem(STORE, JSON.stringify(tokens));
  return tokens;
}

/** Local development only: act as a named demo user without a password. */
export function signInAsDevUser(user: string, groups = ""): void {
  sessionStorage.setItem(DEV_USER, user || "demo-client");
  if (groups) sessionStorage.setItem(`${DEV_USER}.groups`, groups);
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
    tokens = storeSession(await (await cognito()).refresh(tokens.refreshToken));
  }
  return { Authorization: `Bearer ${tokens.accessToken}` };
}

export function isSignedIn(): boolean {
  return Boolean(sessionStorage.getItem(STORE) || sessionStorage.getItem(DEV_USER));
}

export async function signOut(): Promise<void> {
  const config = await loadConfig();
  const raw = sessionStorage.getItem(STORE);
  sessionStorage.clear();
  if (!isLocal(config) && raw) {
    const { refreshToken } = JSON.parse(raw) as Tokens;
    // Best effort: a failed revocation must not keep the person signed in on this device.
    if (refreshToken) await (await cognito()).revoke(refreshToken).catch(() => undefined);
  }
  window.location.assign("/");
}
