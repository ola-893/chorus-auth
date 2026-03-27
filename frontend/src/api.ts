import type {
  ActionRequest,
  Agent,
  ApprovalQueueItem,
  AuditEvent,
  ConnectedAccount,
  DashboardEvent,
  Provider,
  User,
} from "./types";

const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

function buildUrl(path: string): string {
  return `${apiBase}${path}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildUrl(path), {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export const api = {
  getMe: () => request<User>("/api/me"),
  getConnections: () => request<ConnectedAccount[]>("/api/connections"),
  createConnection: (payload: {
    provider: Provider;
    external_account_id?: string;
    scopes: string[];
    status?: "connected";
    metadata?: Record<string, unknown>;
  }) =>
    request<ConnectedAccount>("/api/connections", {
      method: "POST",
      body: JSON.stringify({
        status: "connected",
        metadata: {},
        ...payload,
      }),
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
  getActions: () => request<ActionRequest[]>("/api/actions"),
  createAction: (payload: {
    agent_id: string;
    provider: Provider;
    capability_name: string;
    payload: Record<string, unknown>;
  }) =>
    request<ActionRequest>("/api/actions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
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

