/** Runtime configuration. CDK writes /config.json at deploy time; local dev uses public/config.json. */

export interface AppConfig {
  apiBase: string;
  stage: "local" | "dev" | "prod";
  region: string;
  userPoolId: string;
  clientId: string;
  authDomain: string;
}

let cached: Promise<AppConfig> | null = null;

export function loadConfig(): Promise<AppConfig> {
  cached ??= fetch("/config.json", { cache: "no-store" }).then((r) => {
    if (!r.ok) throw new Error("config.json is missing");
    return r.json() as Promise<AppConfig>;
  });
  return cached;
}

export function resetConfigForTests(): void {
  cached = null;
}
