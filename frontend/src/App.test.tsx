import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import App from "./App";

class MockWebSocket {
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;

  constructor(_url: string) {
    queueMicrotask(() => {
      this.onopen?.();
    });
  }

  close() {
    this.onclose?.();
  }
}

function mockJsonResponse(payload: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(payload),
    text: () => Promise.resolve(JSON.stringify(payload)),
  });
}

describe("App", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");

    const routeMap = new Map<string, unknown>([
      [
        "GET http://localhost:8000/api/auth/config",
        {
          auth_mode: "mock",
          allow_demo_mode: true,
          auth0_domain: null,
          auth0_issuer: null,
          auth0_client_id: null,
          auth0_audience: null,
          auth0_scope: "openid profile email",
          login_path: "/login",
          callback_path: "/login/callback",
        },
      ],
      [
        "GET http://localhost:8000/api/auth/session",
        {
          authenticated: true,
          auth_mode: "mock",
          allow_demo_mode: true,
          user: {
            id: "user-1",
            email: "demo@chorus.local",
            display_name: "Chorus Demo User",
            auth_subject: "mock|demo-user",
            auth_mode: "mock",
            connected_account_count: 2,
          },
        },
      ],
      [
        "GET http://localhost:8000/api/dashboard/summary",
        {
          auto_approved_count: 1,
          approval_requested_count: 1,
          blocked_count: 1,
          quarantined_count: 1,
          latest_protected_action: {
            id: "action-2",
            agent_id: "agent-2",
            provider: "github",
            capability_name: "github.issue.create",
            action_type: "issue.create",
            status: "pending_approval",
            enforcement_decision: "REQUIRE_APPROVAL",
            explanation: "Repository access is allowed but the issue needs human approval.",
            requested_at: "2026-03-27T07:01:00Z",
            resolved_at: null,
            risk_level: "medium",
            risk_source: "rules+llm",
            risk_explanation: "Medium-risk write to GitHub requires confirmation.",
            approval_status: "pending",
            execution_status: null,
            execution_mode: null,
            provider_result_url: null,
            vault_reference: "mock://github/user-1",
          },
        },
      ],
      [
        "GET http://localhost:8000/api/connections",
        [
          {
            id: "connection-1",
            provider: "gmail",
            external_account_id: "demo-gmail-account",
            display_label: "Demo Gmail",
            scopes: ["gmail.compose", "gmail.readonly"],
            granted_scopes: ["gmail.compose", "gmail.readonly"],
            status: "connected",
            connection_health: "healthy",
            connection_mode: "mock",
            mode: "mock",
            vault_reference: "mock://gmail/demo",
            last_synced_at: "2026-03-27T07:00:00Z",
          },
        ],
      ],
      [
        "GET http://localhost:8000/api/agents",
        [
          {
            id: "agent-1",
            name: "Assistant Agent",
            agent_type: "assistant",
            description: "Drafts Gmail updates.",
            status: "active",
            metadata: {},
            quarantine_reason: null,
            capabilities: [
              {
                id: "grant-1",
                capability_id: "cap-1",
                capability_name: "gmail.draft.create",
                provider: "gmail",
                action_type: "draft.create",
                risk_level_default: "low",
                constraints: {
                  allowed_domains: ["authorizedtoact.dev"],
                },
              },
            ],
          },
        ],
      ],
      [
        "GET http://localhost:8000/api/actions",
        [
          {
            id: "action-1",
            agent_id: "agent-1",
            provider: "gmail",
            capability_name: "gmail.draft.create",
            action_type: "draft.create",
            status: "completed",
            enforcement_decision: "ALLOW",
            explanation: "Capability grant and provider access validated.",
            requested_at: "2026-03-27T07:00:00Z",
            resolved_at: "2026-03-27T07:00:01Z",
            risk_level: "low",
            risk_source: "rules",
            risk_explanation: "Low-risk draft creation.",
            approval_status: null,
            execution_status: "succeeded",
            execution_mode: "mock",
            provider_result_url: "https://example.com/draft/1",
            vault_reference: "mock://gmail/demo",
          },
          {
            id: "action-2",
            agent_id: "agent-2",
            provider: "github",
            capability_name: "github.issue.create",
            action_type: "issue.create",
            status: "pending_approval",
            enforcement_decision: "REQUIRE_APPROVAL",
            explanation: "Repository access is allowed but the issue needs human approval.",
            requested_at: "2026-03-27T07:01:00Z",
            resolved_at: null,
            risk_level: "medium",
            risk_source: "rules+llm",
            risk_explanation: "Medium-risk write to GitHub requires confirmation.",
            approval_status: "pending",
            execution_status: null,
            execution_mode: null,
            provider_result_url: null,
            vault_reference: "mock://github/user-1",
          },
        ],
      ],
      [
        "GET http://localhost:8000/api/approvals",
        [
          {
            id: "approval-1",
            action_request_id: "action-2",
            agent_id: "agent-2",
            agent_name: "Builder Agent",
            provider: "github",
            capability_name: "github.issue.create",
            status: "pending",
            explanation: "Issue creation needs approval.",
            requested_at: "2026-03-27T07:01:00Z",
            decided_at: null,
          },
        ],
      ],
      [
        "GET http://localhost:8000/api/audit",
        [
          {
            id: "audit-1",
            action_request_id: "action-1",
            agent_id: "agent-1",
            user_id: "user-1",
            event_type: "action.executed",
            message: "Created Gmail draft for 1 recipient.",
            details: {},
            occurred_at: "2026-03-27T07:00:01Z",
          },
        ],
      ],
      [
        "GET http://localhost:8000/api/actions/action-2/detail",
        {
          action: {
            id: "action-2",
            agent_id: "agent-2",
            provider: "github",
            capability_name: "github.issue.create",
            action_type: "issue.create",
            status: "pending_approval",
            enforcement_decision: "REQUIRE_APPROVAL",
            explanation: "Repository access is allowed but the issue needs human approval.",
            requested_at: "2026-03-27T07:01:00Z",
            resolved_at: null,
            risk_level: "medium",
            risk_source: "rules+llm",
            risk_explanation: "Medium-risk write to GitHub requires confirmation.",
            approval_status: "pending",
            execution_status: null,
            execution_mode: null,
            provider_result_url: null,
            vault_reference: "mock://github/user-1",
          },
          agent_name: "Builder Agent",
          approval_record: {
            status: "pending",
            reason: null,
            decided_at: null,
          },
          execution_record: null,
          connection_summary: {
            id: "connection-2",
            provider: "github",
            display_label: "Demo GitHub",
            external_account_id: "demo-github-account",
            vault_reference: "mock://github/demo",
            granted_scopes: ["repo", "issues:write"],
            mode: "mock",
          },
          audit_events: [
            {
              id: "audit-2",
              action_request_id: "action-2",
              agent_id: "agent-2",
              user_id: "user-1",
              event_type: "approval.requested",
              message: "Approval required for GitHub issue creation.",
              details: {},
              occurred_at: "2026-03-27T07:01:00Z",
            },
          ],
        },
      ],
    ]);

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL | Request, init?: RequestInit) => {
        const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
        const method = init?.method ?? "GET";
        const payload = routeMap.get(`${method} ${url}`);
        if (!payload) {
          throw new Error(`Unexpected request: ${method} ${url}`);
        }
        return mockJsonResponse(payload);
      }),
    );
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("renders the overview shell with judge-facing sections", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Authorized Agent Actions" })).toBeInTheDocument();
    expect(screen.getByText("Auto-approved")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Allow Scenario" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go To Approvals" })).toBeInTheDocument();
    expect(screen.getByText(/Repository access is allowed but the issue needs human approval/i)).toBeInTheDocument();
  });

  test("opens the action detail drawer from the overview spotlight", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole("heading", { name: "Authorized Agent Actions" });
    await user.click(screen.getAllByRole("button", { name: "Open Details" })[0]);

    expect(await screen.findByText("Connection Summary")).toBeInTheDocument();
    expect(screen.getByText("Audit Events")).toBeInTheDocument();
    expect(screen.getByText("mock://github/demo")).toBeInTheDocument();
  });
});
