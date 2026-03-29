import { getStoredAccessToken, isDemoModeEnabled } from "./auth";
import type {
  ActionDetail,
  ActionRequest,
  Agent,
  ApprovalQueueItem,
  AuditEvent,
  AuthConfig,
  AuthSession,
  ConnectedAccount,
  ConnectionStartResponse,
  DashboardEvent,
  DashboardSummary,
  DemoResetResponse,
  Provider,
  ScenarioRunResult,
} from "./types";

const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

function buildUrl(path: string): string {
  return `${apiBase}${path}`;
}

function buildHeaders(init?: RequestInit): HeadersInit {
  const token = getStoredAccessToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(isDemoModeEnabled() ? { "X-Chorus-Demo-Mode": "true" } : {}),
    ...(init?.headers ?? {}),
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildUrl(path), {
    ...init,
    headers: buildHeaders(init),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

function maybeMyAccountToken(): string | undefined {
  return getStoredAccessToken() ?? undefined;
}

export const api = {
  getAuthConfig: () => request<AuthConfig>("/api/auth/config"),
  getAuthSession: () => request<AuthSession>("/api/auth/session"),
  getDashboardSummary: () => request<DashboardSummary>("/api/dashboard/summary"),
  getConnections: () => request<ConnectedAccount[]>("/api/connections"),
  startConnection: (provider: Provider, payload: { redirect_uri: string; requested_scopes: string[] }) =>
    request<ConnectionStartResponse>(`/api/connections/${provider}/start`, {
      method: "POST",
      body: JSON.stringify({
        ...payload,
        my_account_token: maybeMyAccountToken(),
      }),
    }),
  completeConnectionCallback: (payload: {
    provider: Provider;
    auth_session: string;
    connect_code: string;
    redirect_uri: string;
  }) => {
    const params = new URLSearchParams({
      provider: payload.provider,
      auth_session: payload.auth_session,
      connect_code: payload.connect_code,
      redirect_uri: payload.redirect_uri,
    });
    const myAccountToken = maybeMyAccountToken();
    if (myAccountToken) {
      params.set("my_account_token", myAccountToken);
    }
    return request<ConnectedAccount>(`/api/connections/callback?${params.toString()}`);
  },
  refreshConnection: (connectionId: string) =>
    request<ConnectedAccount>(`/api/connections/${connectionId}/refresh`, {
      method: "POST",
      body: JSON.stringify({
        my_account_token: maybeMyAccountToken(),
      }),
    }),
  disconnectConnection: (connectionId: string) =>
    request<ConnectedAccount>(`/api/connections/${connectionId}`, {
      method: "DELETE",
    }),
  getAgents: () => request<Agent[]>("/api/agents"),
  createAgent: (payload: {
    name: string;
    agent_type: string;
    description?: string;
    metadata?: Record<string, unknown>;
  }) =>
    request<Agent>("/api/agents", {
      method: "POST",
      body: JSON.stringify({
        metadata: {},
        ...payload,
      }),
    }),
  grantCapability: (
    agentId: string,
    payload: {
      capability_name: string;
      constraints: Record<string, unknown>;
    },
  ) =>
    request(`/api/agents/${agentId}/capability-grants`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  releaseQuarantine: (agentId: string) =>
    request<Agent>(`/api/agents/${agentId}/release-quarantine`, {
      method: "POST",
    }),
  getActions: () => request<ActionRequest[]>("/api/actions"),
  getActionDetail: (actionId: string) => request<ActionDetail>(`/api/actions/${actionId}/detail`),
  getApprovals: () => request<ApprovalQueueItem[]>("/api/approvals"),
  approve: (approvalId: string, reason?: string) =>
    request<ApprovalQueueItem>(`/api/approvals/${approvalId}/approve`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  reject: (approvalId: string, reason?: string) =>
    request<ApprovalQueueItem>(`/api/approvals/${approvalId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  getAudit: () => request<AuditEvent[]>("/api/audit"),
  resetDemo: () =>
    request<DemoResetResponse>("/api/demo/reset", {
      method: "POST",
    }),
  runScenario: (scenarioId: ScenarioRunResult["scenario_id"]) =>
    request<ScenarioRunResult>(`/api/demo/scenarios/${scenarioId}`, {
      method: "POST",
    }),
};

export function connectDashboardSocket(onEvent: (event: DashboardEvent) => void): WebSocket {
  const url = buildUrl("/ws/dashboard").replace("http://", "ws://").replace("https://", "wss://");
  const socket = new WebSocket(url);
  socket.onmessage = (message) => {
    const event = JSON.parse(message.data) as DashboardEvent;
    onEvent(event);
  };
  return socket;
}
