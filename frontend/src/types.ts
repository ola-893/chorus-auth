export type Provider = "gmail" | "github";
export type AgentStatus = "active" | "disabled" | "quarantined";
export type ConnectedAccountStatus = "connected" | "disconnected" | "error";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type ApprovalStatus = "pending" | "approved" | "rejected";
export type ActionStatus =
  | "received"
  | "policy_blocked"
  | "pending_approval"
  | "approved"
  | "rejected"
  | "executing"
  | "completed"
  | "failed"
  | "quarantined";
export type ExecutionStatus = "pending" | "succeeded" | "failed" | "blocked";
export type EnforcementDecision =
  | "ALLOW"
  | "ALLOW_WITH_AUDIT"
  | "REQUIRE_APPROVAL"
  | "BLOCK"
  | "QUARANTINE";

export interface User {
  id: string;
  email: string;
  display_name: string;
  auth_mode: string;
  connected_account_count: number;
}

export interface ConnectedAccount {
  id: string;
  provider: Provider;
  external_account_id: string | null;
  scopes: string[];
  status: ConnectedAccountStatus;
  connection_mode: string;
  vault_reference: string;
}

export interface CapabilityGrant {
  id: string;
  capability_id: string;
  capability_name: string;
  provider: Provider;
  action_type: string;
  risk_level_default: RiskLevel;
  constraints: Record<string, unknown>;
}

export interface Agent {
  id: string;
  name: string;
  agent_type: string;
  description: string | null;
  status: AgentStatus;
  metadata: Record<string, unknown>;
  quarantine_reason: string | null;
  capabilities: CapabilityGrant[];
}

export interface ActionRequest {
  id: string;
  agent_id: string;
  provider: Provider;
  capability_name: string;
  action_type: string;
  status: ActionStatus;
  enforcement_decision: EnforcementDecision | null;
  explanation: string | null;
  requested_at: string;
  resolved_at: string | null;
  risk_level: RiskLevel | null;
  approval_status: ApprovalStatus | null;
  execution_status: ExecutionStatus | null;
}

export interface ApprovalQueueItem {
  id: string;
  action_request_id: string;
  agent_id: string;
  agent_name: string;
  provider: Provider;
  capability_name: string;
  status: ApprovalStatus;
  explanation: string | null;
  requested_at: string;
  decided_at: string | null;
}

export interface AuditEvent {
  id: string;
  action_request_id: string | null;
  agent_id: string | null;
  user_id: string | null;
  event_type: string;
  message: string;
  details: Record<string, unknown>;
  occurred_at: string;
}

export interface DashboardEvent {
  type: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

