import { render, screen } from "@testing-library/react";
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

describe("App", () => {
  beforeEach(() => {
    const responses = [
      {
        id: "user-1",
        email: "demo@chorus.local",
        display_name: "Chorus Demo User",
        auth_mode: "mock",
        connected_account_count: 2,
      },
      [
        {
          id: "connection-1",
          provider: "gmail",
          external_account_id: "demo-gmail-account",
          scopes: ["gmail.compose", "gmail.readonly"],
          status: "connected",
          connection_mode: "mock",
          vault_reference: "vault://gmail/demo",
        },
      ],
      [
        {
          id: "agent-1",
          name: "Assistant Agent",
          agent_type: "assistant",
          description: "Drafts routine Gmail updates inside an approved domain boundary.",
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
          approval_status: null,
          execution_status: "succeeded",
        },
      ],
      [],
      [
        {
          id: "audit-1",
          action_request_id: "action-1",
          agent_id: "agent-1",
          user_id: "user-1",
          event_type: "action.executed",
          message: "Created Gmail draft for 1 recipient(s).",
          details: {},
          occurred_at: "2026-03-27T07:00:01Z",
        },
      ],
    ];

    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(responses.shift()),
        }),
      ),
    );
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("renders seeded dashboard data", async () => {
    render(<App />);

    expect(await screen.findByText(/Chorus Demo User/)).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Assistant Agent" })).toBeInTheDocument();
    expect(screen.getByText("gmail.compose, gmail.readonly")).toBeInTheDocument();
    expect(screen.getByText("action.executed")).toBeInTheDocument();
  });
});
