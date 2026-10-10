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
