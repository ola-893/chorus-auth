export type Provider = "gmail" | "github";
export type AgentStatus = "active" | "disabled" | "quarantined";
export type ConnectedAccountStatus = "connected" | "disconnected" | "error";
export type ConnectionHealth = "healthy" | "pending" | "degraded" | "error";
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
  auth_subject: string | null;
  auth_mode: string;
  connected_account_count: number;
}

export interface AuthConfig {
  auth_mode: string;
  allow_demo_mode: boolean;
  auth0_domain: string | null;
  auth0_issuer: string | null;
  auth0_client_id: string | null;
  auth0_audience: string | null;
  auth0_scope: string;
  login_path: string;
  callback_path: string;
}

export interface AuthSession {
  authenticated: boolean;
  auth_mode: string;
  allow_demo_mode: boolean;
  user: User | null;
}

export interface ConnectedAccount {
  id: string;
  provider: Provider;
  external_account_id: string | null;
  display_label: string | null;
  scopes: string[];
  granted_scopes: string[];
  status: ConnectedAccountStatus;
  connection_health: ConnectionHealth;
  connection_mode: string;
  mode: string;
  vault_reference: string;
  last_synced_at: string | null;
}

export interface ConnectionStartResponse {
  provider: Provider;
  mode: string;
  authorization_url: string | null;
  state: string;
  auth_session: string | null;
  redirect_uri: string;
  message: string;
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
  risk_source: string | null;
  risk_explanation: string | null;
  approval_status: ApprovalStatus | null;
  execution_status: ExecutionStatus | null;
  execution_mode: string | null;
  provider_result_url: string | null;
  vault_reference: string | null;
}

export interface ActionApprovalRecord {
  status: ApprovalStatus;
  reason: string | null;
  decided_at: string | null;
}

export interface ActionExecutionRecord {
  status: ExecutionStatus;
  summary: string | null;
  external_reference_id: string | null;
  provider_result_url: string | null;
  vault_reference: string | null;
  execution_mode: string | null;
  executed_at: string | null;
  result: Record<string, unknown>;
}

export interface ActionConnectionSummary {
  id: string | null;
  provider: Provider;
  display_label: string | null;
  external_account_id: string | null;
  vault_reference: string | null;
  granted_scopes: string[];
  mode: string | null;
}

export interface ActionDetail {
  action: ActionRequest;
  agent_name: string;
  approval_record: ActionApprovalRecord | null;
  execution_record: ActionExecutionRecord | null;
  connection_summary: ActionConnectionSummary | null;
  audit_events: AuditEvent[];
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

export interface DashboardSummary {
  auto_approved_count: number;
  approval_requested_count: number;
  blocked_count: number;
  quarantined_count: number;
  latest_protected_action: ActionRequest | null;
}

export interface DemoResetResponse {
  user_id: string;
  email: string;
  connection_count: number;
  agent_count: number;
}

export interface ScenarioRunResult {
  scenario_id: "allow" | "approval" | "quarantine";
  created_action_ids: string[];
  final_statuses: string[];
  highlight_action_id: string | null;
}

export interface DashboardEvent {
  type: string;
  payload: Record<string, unknown>;
  timestamp: string;
}
