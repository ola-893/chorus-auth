import type { AuthConfig } from "./types";

const ACCESS_TOKEN_KEY = "chorus.auth0.access_token";
const DEMO_MODE_KEY = "chorus.demo_mode";
const PKCE_STATE_KEY = "chorus.auth0.pkce.state";
const PKCE_VERIFIER_KEY = "chorus.auth0.pkce.verifier";

function ensureBrowserCrypto(): Crypto {
  if (!window.crypto) {
    throw new Error("Browser crypto is required for Auth0 login.");
  }
  return window.crypto;
}

function normalizeAuth0Base(config: AuthConfig): string {
  const configured = config.auth0_issuer || config.auth0_domain;
  if (!configured) {
    throw new Error("Auth0 is not configured for this environment.");
  }

  if (configured.startsWith("http://") || configured.startsWith("https://")) {
    return configured.replace(/\/$/, "");
  }

  return `https://${configured.replace(/\/$/, "")}`;
}

function base64UrlEncode(data: Uint8Array): string {
  let value = "";
  data.forEach((item) => {
    value += String.fromCharCode(item);
  });
  return btoa(value).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function createRandomString(length = 48): string {
  const random = new Uint8Array(length);
  ensureBrowserCrypto().getRandomValues(random);
  return base64UrlEncode(random);
}

async function createCodeChallenge(verifier: string): Promise<string> {
  const digest = await ensureBrowserCrypto().subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return base64UrlEncode(new Uint8Array(digest));
}

function buildRedirectUri(path: string): string {
  return new URL(path, window.location.origin).toString();
}

function normalizeScope(scope: string): string {
  const parts = new Set(
    scope
      .split(/\s+/)
      .map((item) => item.trim())
      .filter(Boolean),
  );
  parts.add("openid");
  parts.add("profile");
  parts.add("email");
  return Array.from(parts).join(" ");
}

export function getStoredAccessToken(): string | null {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function clearStoredAccessToken(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function isDemoModeEnabled(): boolean {
  return window.localStorage.getItem(DEMO_MODE_KEY) === "true";
}

export function setDemoModeEnabled(enabled: boolean): void {
  if (enabled) {
    window.localStorage.setItem(DEMO_MODE_KEY, "true");
    return;
  }
  window.localStorage.removeItem(DEMO_MODE_KEY);
}

export async function beginAuth0Login(config: AuthConfig): Promise<void> {
  if (config.auth_mode !== "auth0") {
    throw new Error("Auth0 login is not enabled for this environment.");
  }
  if (!config.auth0_client_id) {
    throw new Error("Missing Auth0 client id.");
  }

  const verifier = createRandomString(64);
  const state = createRandomString(32);
  const challenge = await createCodeChallenge(verifier);
  window.sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
  window.sessionStorage.setItem(PKCE_STATE_KEY, state);
  setDemoModeEnabled(false);

  const params = new URLSearchParams({
    response_type: "code",
    client_id: config.auth0_client_id,
    redirect_uri: buildRedirectUri(config.callback_path),
    scope: normalizeScope(config.auth0_scope),
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  if (config.auth0_audience) {
    params.set("audience", config.auth0_audience);
  }

  window.location.assign(`${normalizeAuth0Base(config)}/authorize?${params.toString()}`);
}

export async function completeAuth0Callback(config: AuthConfig): Promise<void> {
  if (!config.auth0_client_id) {
    throw new Error("Missing Auth0 client id.");
  }

  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");
  const state = params.get("state");
  const verifier = window.sessionStorage.getItem(PKCE_VERIFIER_KEY);
  const expectedState = window.sessionStorage.getItem(PKCE_STATE_KEY);

  if (!code || !state || !verifier || !expectedState) {
    throw new Error("Missing Auth0 callback state.");
  }
  if (state !== expectedState) {
    throw new Error("Auth0 callback state mismatch.");
  }

  const response = await fetch(`${normalizeAuth0Base(config)}/oauth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      grant_type: "authorization_code",
      client_id: config.auth0_client_id,
      code_verifier: verifier,
      code,
      redirect_uri: buildRedirectUri(config.callback_path),
    }),
  });

  const payload = (await response.json()) as { access_token?: string; error_description?: string; error?: string };
  if (!response.ok || !payload.access_token) {
    throw new Error(payload.error_description || payload.error || "Auth0 token exchange failed.");
  }

  window.localStorage.setItem(ACCESS_TOKEN_KEY, payload.access_token);
  setDemoModeEnabled(false);
  window.sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  window.sessionStorage.removeItem(PKCE_STATE_KEY);
}
