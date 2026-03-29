import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { api, connectDashboardSocket } from "./api";
import { beginAuth0Login, clearStoredAccessToken, completeAuth0Callback, isDemoModeEnabled, setDemoModeEnabled } from "./auth";
import type {
  ActionDetail,
  ActionRequest,
  ApprovalQueueItem,
  AuditEvent,
  AuthConfig,
  AuthSession,
  ConnectedAccount,
  DashboardEvent,
  DashboardSummary,
  EnforcementDecision,
  Provider,
  ScenarioRunResult,
  User,
} from "./types";

type CapabilityDefinition = {
  name: string;
  provider: Provider;
  label: string;
  risk: string;
  constraintHint: string;
  defaultConstraints: string;
};

type AppRoute = "/login" | "/overview" | "/connections" | "/agents" | "/approvals" | "/activity" | "/demo";
type BannerTone = "info" | "error";
type ConnectionsTab = "accounts" | "scopes" | "health";
type AgentsTab = "registry" | "capability-grants" | "quarantine";
type ApprovalsTab = "pending" | "resolved";
type ActivityTab = "timeline" | "by-action" | "by-agent";
type DecisionFilter = "ALL" | EnforcementDecision;

const appRoutes: AppRoute[] = ["/login", "/overview", "/connections", "/agents", "/approvals", "/activity", "/demo"];

const capabilityCatalog: CapabilityDefinition[] = [
  {
    name: "gmail.draft.create",
    provider: "gmail",
    label: "Gmail Draft Create",
    risk: "Low",
    constraintHint: "Allowed email domains",
    defaultConstraints: "authorizedtoact.dev",
  },
  {
    name: "github.issue.create",
    provider: "github",
    label: "GitHub Issue Create",
    risk: "Medium",
    constraintHint: "Approved repository",
    defaultConstraints: "chorus/secure-demo",
  },
  {
    name: "github.pull_request.merge",
    provider: "github",
    label: "GitHub Pull Request Merge",
    risk: "High",
    constraintHint: "Approved repository",
    defaultConstraints: "chorus/secure-demo",
  },
];

const defaultScopes: Record<Provider, string[]> = {
  gmail: ["gmail.compose", "gmail.readonly"],
  github: ["repo", "issues:write", "pull_requests:write"],
};

function readLocation(): { pathname: string; search: string } {
  return {
    pathname: window.location.pathname,
    search: window.location.search,
  };
}

function normalizeRoute(pathname: string): AppRoute {
  if (pathname.startsWith("/login")) {
    return "/login";
  }
  const route = appRoutes.find((candidate) => candidate === pathname);
  return route ?? "/overview";
}

function replaceLocation(path: string): { pathname: string; search: string } {
  window.history.replaceState({}, "", path);
  return readLocation();
}

function pushLocation(path: string): { pathname: string; search: string } {
  window.history.pushState({}, "", path);
  return readLocation();
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Waiting";
  }
  return new Date(value).toLocaleString();
}

function summarizeScopes(scopes: string[]): string {
  if (scopes.length === 0) {
    return "No scopes recorded";
  }
  return scopes.join(", ");
}

function actionTitle(action: ActionRequest): string {
  return `${action.capability_name} on ${action.provider}`;
}

function buildGrantConstraints(capabilityName: string, constraintValue: string): Record<string, unknown> {
  if (capabilityName === "gmail.draft.create") {
    return {
      allowed_domains: constraintValue
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
    };
  }

  return {
    repo: constraintValue.trim(),
  };
}

function matchesDecisionFilter(action: ActionRequest, filter: DecisionFilter): boolean {
  if (filter === "ALL") {
    return true;
  }
  return action.enforcement_decision === filter;
}

function copyText(value: string): Promise<void> {
  if (!navigator.clipboard) {
    return Promise.reject(new Error("Clipboard access is not available in this browser."));
  }
  return navigator.clipboard.writeText(value);
}

function decisionDescription(decision: EnforcementDecision | null): string {
  if (decision === "ALLOW_WITH_AUDIT") {
    return "Allowed with audit";
  }
  if (decision === "REQUIRE_APPROVAL") {
    return "Approval required";
  }
  if (decision === "BLOCK") {
    return "Blocked";
  }
  if (decision === "QUARANTINE") {
    return "Quarantined";
  }
  if (decision === "ALLOW") {
    return "Allowed";
  }
  return "Pending";
}

function connectionModeSummary(connections: ConnectedAccount[]): string {
  if (connections.length === 0) {
    return "No provider connections yet.";
  }
  const liveCount = connections.filter((connection) => connection.mode === "live").length;
  const mockCount = connections.filter((connection) => connection.mode !== "live").length;
  return `${liveCount} live / ${mockCount} mock`;
}

function fullDemoScript(): string {
  return [
    "1. Open the Overview page and confirm summary metrics are visible.",
    "2. Open Connections and verify Gmail and GitHub are connected through Token Vault.",
    "3. Open Agents and show scoped grants per agent.",
    "4. Run the allow scenario so Chorus auto-creates a Gmail draft.",
    "5. Run the approval scenario, then approve the pending GitHub issue.",
    "6. Run the quarantine scenario to block and quarantine the merge attempt.",
    "7. Finish in Activity and open the action detail drawer for the protected action.",
  ].join("\n");
}

function SummaryCard(props: { label: string; value: number; note: string }) {
  return (
    <article className="panel summary-card">
      <p className="eyebrow">{props.label}</p>
      <strong>{props.value}</strong>
      <p className="muted">{props.note}</p>
    </article>
  );
}

function SectionHeader(props: {
  title: string;
  subtitle: string;
  actions?: JSX.Element;
}) {
  return (
    <div className="section-header">
      <div>
        <h2>{props.title}</h2>
        <p className="muted">{props.subtitle}</p>
      </div>
      {props.actions}
    </div>
  );
}

function TabBar<T extends string>(props: {
  active: T;
  onChange: (next: T) => void;
  tabs: Array<{ id: T; label: string }>;
}) {
  return (
    <div className="tab-row" role="tablist">
      {props.tabs.map((tab) => (
        <button
          key={tab.id}
          className={tab.id === props.active ? "tab-button tab-button-active" : "tab-button"}
          onClick={() => props.onChange(tab.id)}
          role="tab"
          type="button"
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function ActionCard(props: {
  action: ActionRequest;
  agentName?: string;
  onOpenDetail: (actionId: string) => void;
  onOpenProviderResult?: (url: string) => void;
  onJumpToAgent?: (agentId: string) => void;
}) {
  const { action } = props;
  return (
    <article className="panel item-card">
      <div className="item-card-header">
        <div>
          <h3>{actionTitle(action)}</h3>
          <p className="muted">
            {props.agentName ? `${props.agentName} · ` : ""}
            {formatDate(action.requested_at)}
          </p>
        </div>
        <div className="badge-row">
          <span className="badge">{decisionDescription(action.enforcement_decision)}</span>
          <span className="badge">{action.risk_level ?? "unrated"}</span>
          <span className="badge">{action.execution_mode ?? "pending"}</span>
        </div>
      </div>
      <dl className="kv-grid">
        <div>
          <dt>Provider</dt>
          <dd>{action.provider}</dd>
        </div>
        <div>
          <dt>Capability</dt>
          <dd>{action.capability_name}</dd>
        </div>
        <div>
          <dt>Outcome</dt>
          <dd>{action.status}</dd>
        </div>
        <div>
          <dt>Execution</dt>
          <dd>{action.execution_status ?? "Waiting"}</dd>
        </div>
      </dl>
      <p>{action.explanation || action.risk_explanation || "No explanation recorded yet."}</p>
      <div className="button-row">
        <button type="button" onClick={() => props.onOpenDetail(action.id)}>
          Open Details
        </button>
        {action.provider_result_url ? (
          <button type="button" onClick={() => props.onOpenProviderResult?.(action.provider_result_url!)}>
            Open Provider Result
          </button>
        ) : null}
        {props.onJumpToAgent ? (
          <button type="button" onClick={() => props.onJumpToAgent?.(action.agent_id)}>
            Jump To Agent
          </button>
        ) : null}
      </div>
    </article>
  );
}

function EmptyState(props: { title: string; copy: string }) {
  return (
    <div className="empty-state">
      <strong>{props.title}</strong>
      <p className="muted">{props.copy}</p>
    </div>
  );
}

export default function App() {
  const bootRef = useRef(false);
  const handledConnectionCallback = useRef<string | null>(null);

  const [location, setLocation] = useState(() => readLocation());
  const route = normalizeRoute(location.pathname);

  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);
  const [authSession, setAuthSession] = useState<AuthSession | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [connections, setConnections] = useState<ConnectedAccount[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [actions, setActions] = useState<ActionRequest[]>([]);
  const [approvals, setApprovals] = useState<ApprovalQueueItem[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);

  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ tone: BannerTone; text: string } | null>(null);
  const [wsState, setWsState] = useState("offline");
  const [lastEvent, setLastEvent] = useState("Waiting for dashboard activity.");

  const [connectionsTab, setConnectionsTab] = useState<ConnectionsTab>("accounts");
  const [agentsTab, setAgentsTab] = useState<AgentsTab>("registry");
  const [approvalsTab, setApprovalsTab] = useState<ApprovalsTab>("pending");
  const [activityTab, setActivityTab] = useState<ActivityTab>("timeline");
  const [decisionFilter, setDecisionFilter] = useState<DecisionFilter>("ALL");
  const [activityAgentFilter, setActivityAgentFilter] = useState<string>("ALL");

  const [selectedConnectionId, setSelectedConnectionId] = useState<string | null>(null);
  const [selectedApprovalId, setSelectedApprovalId] = useState<string | null>(null);
  const [selectedDetailId, setSelectedDetailId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<ActionDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [agentName, setAgentName] = useState("");
  const [agentType, setAgentType] = useState("assistant");
  const [agentDescription, setAgentDescription] = useState("");
  const [grantAgentId, setGrantAgentId] = useState("");
  const [grantCapabilityName, setGrantCapabilityName] = useState("gmail.draft.create");
  const [grantConstraints, setGrantConstraints] = useState("authorizedtoact.dev");
  const [demoRuns, setDemoRuns] = useState<string[]>([]);

  const user: User | null = authSession?.user ?? null;
  const pendingApprovals = useMemo(() => approvals.filter((item) => item.status === "pending"), [approvals]);
  const resolvedApprovals = useMemo(() => approvals.filter((item) => item.status !== "pending"), [approvals]);
  const quarantinedAgents = useMemo(() => agents.filter((agent) => agent.status === "quarantined"), [agents]);
  const latestProtectedAction = summary?.latest_protected_action ?? null;

  const selectedConnection = connections.find((connection) => connection.id === selectedConnectionId) ?? connections[0] ?? null;
  const selectedApproval =
    approvals.find((approval) => approval.id === selectedApprovalId) ?? pendingApprovals[0] ?? resolvedApprovals[0] ?? null;
  const selectedCapability =
    capabilityCatalog.find((capability) => capability.name === grantCapabilityName) ?? capabilityCatalog[0];

  const filteredActions = useMemo(
    () =>
      actions.filter(
        (action) =>
          matchesDecisionFilter(action, decisionFilter) && (activityAgentFilter === "ALL" || action.agent_id === activityAgentFilter),
      ),
    [actions, decisionFilter, activityAgentFilter],
  );

  const actionsByAgent = useMemo(
    () =>
      agents
        .map((agent) => ({
          agent,
          actions: filteredActions.filter((action) => action.agent_id === agent.id),
        }))
        .filter((entry) => entry.actions.length > 0),
    [agents, filteredActions],
  );

  useEffect(() => {
    const handlePopState = () => setLocation(readLocation());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (bootRef.current) {
      return;
    }
    bootRef.current = true;

    let active = true;
    async function boot() {
      try {
        const config = await api.getAuthConfig();
        if (!active) {
          return;
        }
        setAuthConfig(config);

        let currentLocation = readLocation();
        if (currentLocation.pathname === config.callback_path) {
          try {
            await completeAuth0Callback(config);
            if (!active) {
              return;
            }
            setBanner({ tone: "info", text: "Auth0 session established. Chorus can now protect live provider actions." });
          } catch (error) {
            clearStoredAccessToken();
            setBanner({
              tone: "error",
              text: error instanceof Error ? error.message : "Auth0 callback failed.",
            });
          }
          currentLocation = replaceLocation(config.login_path);
          if (active) {
            setLocation(currentLocation);
          }
        }

        const nextSession = await refreshWorkspace(true);
        if (!active) {
          return;
        }

        if (nextSession?.authenticated) {
          if (normalizeRoute(currentLocation.pathname) === "/login") {
            setLocation(replaceLocation("/overview"));
          }
        } else if (normalizeRoute(currentLocation.pathname) !== "/login") {
          setLocation(replaceLocation(config.login_path));
        }
      } catch (error) {
        if (active) {
          setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to boot dashboard." });
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void boot();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!authSession?.authenticated) {
      setWsState("offline");
      return;
    }

    const socket = connectDashboardSocket((event: DashboardEvent) => {
      setLastEvent(`${event.type} at ${formatDate(event.timestamp)}`);
      void refreshWorkspace();
    });

    socket.onopen = () => setWsState("live");
    socket.onerror = () => setWsState("degraded");
    socket.onclose = () => setWsState("offline");

    return () => {
      socket.close();
    };
  }, [authSession?.authenticated]);

  useEffect(() => {
    if (!grantAgentId && agents[0]) {
      setGrantAgentId(agents[0].id);
    }
    if (!selectedConnectionId && connections[0]) {
      setSelectedConnectionId(connections[0].id);
    }
    if (!selectedApprovalId && approvals[0]) {
      setSelectedApprovalId(approvals[0].id);
    }
  }, [agents, approvals, connections, grantAgentId, selectedApprovalId, selectedConnectionId]);

  useEffect(() => {
    setGrantConstraints(selectedCapability.defaultConstraints);
  }, [selectedCapability.defaultConstraints]);

  useEffect(() => {
    if (!authSession?.authenticated || normalizeRoute(location.pathname) !== "/connections") {
      return;
    }

    const params = new URLSearchParams(location.search);
    const provider = params.get("provider");
    const authSessionToken = params.get("auth_session");
    const connectCode = params.get("connect_code");
    const redirectUri = params.get("redirect_uri");
    const error = params.get("error");
    const callbackKey = `${provider}:${authSessionToken}:${connectCode}:${redirectUri}`;

    if (error) {
      setBanner({ tone: "error", text: `Connection callback failed: ${error}` });
      setLocation(replaceLocation("/connections"));
      return;
    }
    if (!provider || !authSessionToken || !connectCode || !redirectUri) {
      return;
    }
    if (handledConnectionCallback.current === callbackKey) {
      return;
    }
    handledConnectionCallback.current = callbackKey;

    setBusyKey("connection-callback");
    void api
      .completeConnectionCallback({
        provider: provider as Provider,
        auth_session: authSessionToken,
        connect_code: connectCode,
        redirect_uri: redirectUri,
      })
      .then(async () => {
        setBanner({ tone: "info", text: `${provider} connection is ready for delegated execution.` });
        await refreshWorkspace();
        setLocation(replaceLocation("/connections"));
      })
      .catch((callbackError) => {
        setBanner({
          tone: "error",
          text: callbackError instanceof Error ? callbackError.message : "Failed to complete provider connection.",
        });
      })
      .finally(() => {
        setBusyKey(null);
      });
  }, [authSession?.authenticated, location.pathname, location.search]);

  async function refreshWorkspace(showBusy = false): Promise<AuthSession | null> {
    if (showBusy) {
      setBusyKey("refresh");
    }

    try {
      const sessionResponse = await api.getAuthSession();
      setAuthSession(sessionResponse);
      if (!sessionResponse.authenticated) {
        setSummary(null);
        setConnections([]);
        setAgents([]);
        setActions([]);
        setApprovals([]);
        setAudit([]);
        return sessionResponse;
      }

      const [summaryResponse, connectionResponse, agentResponse, actionResponse, approvalResponse, auditResponse] =
        await Promise.all([
          api.getDashboardSummary(),
          api.getConnections(),
          api.getAgents(),
          api.getActions(),
          api.getApprovals(),
          api.getAudit(),
        ]);

      setSummary(summaryResponse);
      setConnections(connectionResponse);
      setAgents(agentResponse);
      setActions(actionResponse);
      setApprovals(approvalResponse);
      setAudit(auditResponse);

      if (selectedDetailId) {
        try {
          const detailResponse = await api.getActionDetail(selectedDetailId);
          setSelectedDetail(detailResponse);
        } catch {
          setSelectedDetail(null);
        }
      }

      return sessionResponse;
    } finally {
      if (showBusy) {
        setBusyKey(null);
      }
    }
  }

  function navigateTo(nextRoute: AppRoute, replace = false): void {
    setLocation(replace ? replaceLocation(nextRoute) : pushLocation(nextRoute));
  }

  async function openActionDetail(actionId: string): Promise<void> {
    setSelectedDetailId(actionId);
    setDetailLoading(true);
    try {
      const detail = await api.getActionDetail(actionId);
      setSelectedDetail(detail);
      setBanner(null);
    } catch (error) {
      setBanner({
        tone: "error",
        text: error instanceof Error ? error.message : "Failed to load action detail.",
      });
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleContinueWithAuth0(): Promise<void> {
    if (!authConfig) {
      return;
    }
    setBusyKey("auth0-login");
    try {
      await beginAuth0Login(authConfig);
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to start Auth0 login." });
      setBusyKey(null);
    }
  }

  async function handleUseLocalDemoMode(): Promise<void> {
    setBusyKey("demo-login");
    setDemoModeEnabled(true);
    try {
      const sessionResponse = await refreshWorkspace();
      if (sessionResponse?.authenticated) {
        navigateTo("/overview", true);
        setBanner({ tone: "info", text: "Local demo mode is active. Provider execution will stay clearly labeled." });
      } else {
        setBanner({ tone: "error", text: "Demo mode is not available in this environment." });
      }
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to enter demo mode." });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleSignOut(): Promise<void> {
    clearStoredAccessToken();
    setDemoModeEnabled(false);
    setBusyKey("sign-out");
    try {
      await refreshWorkspace();
      setLocation(replaceLocation("/login"));
      setBanner({ tone: "info", text: "Session cleared on this device." });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to clear session." });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleStartConnection(provider: Provider): Promise<void> {
    setBusyKey(`connect-${provider}`);
    try {
      const result = await api.startConnection(provider, {
        redirect_uri: new URL("/connections", window.location.origin).toString(),
        requested_scopes: defaultScopes[provider],
      });
      if (result.authorization_url) {
        window.location.assign(result.authorization_url);
        return;
      }
      if (!result.auth_session) {
        throw new Error(result.message || "Connection flow did not return an auth session.");
      }
      await api.completeConnectionCallback({
        provider,
        auth_session: result.auth_session,
        connect_code: "mock-connect-code",
        redirect_uri: result.redirect_uri,
      });
      await refreshWorkspace();
      setBanner({ tone: "info", text: result.message });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to connect provider." });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleRefreshConnection(connectionId: string): Promise<void> {
    setBusyKey(`refresh-${connectionId}`);
    try {
      await api.refreshConnection(connectionId);
      await refreshWorkspace();
      setBanner({ tone: "info", text: "Connection refreshed from Token Vault." });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to refresh connection." });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleDisconnectConnection(connectionId: string): Promise<void> {
    setBusyKey(`disconnect-${connectionId}`);
    try {
      await api.disconnectConnection(connectionId);
      await refreshWorkspace();
      setBanner({ tone: "info", text: "Connection marked as disconnected." });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to disconnect provider." });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleCreateAgent(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setBusyKey("create-agent");
    try {
      const created = await api.createAgent({
        name: agentName,
        agent_type: agentType,
        description: agentDescription || undefined,
      });
      setAgentName("");
      setAgentDescription("");
      await refreshWorkspace();
      setGrantAgentId(created.id);
      setBanner({ tone: "info", text: `${created.name} is ready for capability grants.` });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to create agent." });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleGrantCapability(mode: "grant" | "update"): Promise<void> {
    if (!grantAgentId) {
      setBanner({ tone: "error", text: "Select an agent before editing capability grants." });
      return;
    }

    setBusyKey(`${mode}-capability`);
    try {
      await api.grantCapability(grantAgentId, {
        capability_name: grantCapabilityName,
        constraints: buildGrantConstraints(grantCapabilityName, grantConstraints),
      });
      await refreshWorkspace();
      setBanner({
        tone: "info",
        text: mode === "grant" ? "Capability grant saved for the selected agent." : "Capability constraints updated.",
      });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to save capability grant." });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleReleaseQuarantine(agentId: string): Promise<void> {
    setBusyKey(`release-${agentId}`);
    try {
      await api.releaseQuarantine(agentId);
      await refreshWorkspace();
      setBanner({ tone: "info", text: "Agent released from quarantine." });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to release quarantine." });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleApproval(approvalId: string, decision: "approve" | "reject"): Promise<void> {
    setBusyKey(`${decision}-${approvalId}`);
    try {
      if (decision === "approve") {
        await api.approve(approvalId, "Approved from Chorus dashboard.");
      } else {
        await api.reject(approvalId, "Rejected from Chorus dashboard.");
      }
      await refreshWorkspace();
      setBanner({
        tone: "info",
        text: decision === "approve" ? "Approval granted and action resumed." : "Approval request rejected.",
      });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to resolve approval." });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleRunScenario(scenarioId: ScenarioRunResult["scenario_id"]): Promise<void> {
    setBusyKey(`scenario-${scenarioId}`);
    try {
      const result = await api.runScenario(scenarioId);
      setDemoRuns((current) => [
        `${result.scenario_id}: ${result.final_statuses.join(", ")}`,
        ...current,
      ].slice(0, 6));
      await refreshWorkspace();
      if (result.highlight_action_id) {
        await openActionDetail(result.highlight_action_id);
      }
      setBanner({ tone: "info", text: `Scenario ${scenarioId} completed.` });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : `Failed to run ${scenarioId} scenario.` });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleRunFullDemo(): Promise<void> {
    setBusyKey("scenario-full");
    try {
      const allowResult = await api.runScenario("allow");
      const approvalResult = await api.runScenario("approval");
      await refreshWorkspace();
      const pending = pendingApprovals[0] ?? (await api.getApprovals()).find((item) => item.status === "pending");
      if (pending) {
        await api.approve(pending.id, "Auto-approved from the full demo flow.");
      }
      const quarantineResult = await api.runScenario("quarantine");
      setDemoRuns((current) => [
        `full-demo: ${allowResult.final_statuses.concat(approvalResult.final_statuses, quarantineResult.final_statuses).join(", ")}`,
        ...current,
      ].slice(0, 6));
      await refreshWorkspace();
      if (quarantineResult.highlight_action_id) {
        await openActionDetail(quarantineResult.highlight_action_id);
      }
      setBanner({ tone: "info", text: "Full demo flow completed." });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to run full demo." });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleResetDemo(): Promise<void> {
    setBusyKey("reset-demo");
    try {
      const result = await api.resetDemo();
      await refreshWorkspace();
      setDemoRuns([]);
      setBanner({
        tone: "info",
        text: `Demo workspace reset for ${result.email} with ${result.agent_count} agents and ${result.connection_count} connections.`,
      });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to reset demo workspace." });
    } finally {
      setBusyKey(null);
    }
  }

  async function handleCopyDemoScript(): Promise<void> {
    try {
      await copyText(fullDemoScript());
      setBanner({ tone: "info", text: "Demo script copied to the clipboard." });
    } catch (error) {
      setBanner({ tone: "error", text: error instanceof Error ? error.message : "Failed to copy the demo script." });
    }
  }

  function handleViewActionHistory(agentId: string): void {
    setActivityAgentFilter(agentId);
    navigateTo("/activity");
  }

  function handleOpenAuditTrail(actionId: string): void {
    navigateTo("/activity");
    void openActionDetail(actionId);
  }

  function handleOpenProviderResult(url: string): void {
    window.open(url, "_blank", "noopener,noreferrer");
  }

  if (loading) {
    return (
      <main className="app-shell">
        <section className="panel hero-panel">
          <p className="eyebrow">Chorus</p>
          <h1>Booting the auth control plane</h1>
          <p className="muted">Loading auth config, session state, and the latest protected actions.</p>
        </section>
      </main>
    );
  }

  if (!authSession?.authenticated || !user) {
    return (
      <main className="app-shell">
        <section className="panel hero-panel">
          <p className="eyebrow">Login</p>
          <h1>Make AI agents safe to trust with real accounts.</h1>
          <p className="muted">
            Chorus turns delegated provider access into a visible, approval-aware control plane with auditability and
            quarantine controls.
          </p>
        </section>

        {banner ? <div className={`banner banner-${banner.tone}`}>{banner.text}</div> : null}

        <section className="grid-two">
          <article className="panel">
            <SectionHeader
              title="Product Message"
              subtitle="This app protects Gmail and GitHub actions with scoped grants, risk checks, approvals, and quarantine."
            />
            <ul className="plain-list">
              <li>Low-risk actions can complete automatically.</li>
              <li>Medium-risk actions pause for explicit approval.</li>
              <li>High-risk or repeated unsafe actions are blocked and quarantined.</li>
              <li>Every decision is visible in the audit trail.</li>
            </ul>
          </article>

          <article className="panel">
            <SectionHeader
              title="Sign-In State"
              subtitle={`Auth mode: ${authConfig?.auth_mode ?? authSession?.auth_mode ?? "unknown"}. Demo fallback: ${
                authConfig?.allow_demo_mode ? "enabled" : "disabled"
              }.`}
            />
            <div className="stack">
              <button
                type="button"
                onClick={() => void handleContinueWithAuth0()}
                disabled={busyKey === "auth0-login" || authConfig?.auth_mode !== "auth0"}
              >
                Continue with Auth0
              </button>
              {authConfig?.allow_demo_mode ? (
                <button type="button" onClick={() => void handleUseLocalDemoMode()} disabled={busyKey === "demo-login"}>
                  Use local demo mode
                </button>
              ) : null}
            </div>
          </article>

          <article className="panel panel-full">
            <SectionHeader
              title="Fallback Mode Notice"
              subtitle="Local demo mode keeps the full workflow available when live auth or providers are not ready."
            />
            <p className="muted">
              Demo mode is{" "}
              <strong>{isDemoModeEnabled() ? "currently active on this device" : "currently off"}</strong>. Every mock or
              fallback action stays labeled so the demo never overstates what ran live.
            </p>
          </article>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Chorus</p>
          <h1>Authorized Agent Actions</h1>
          <p className="muted">
            {user.display_name} · {user.email} · {authSession.auth_mode} auth · {connectionModeSummary(connections)}
          </p>
        </div>
        <div className="header-actions">
          <button type="button" onClick={() => void refreshWorkspace(true)} disabled={busyKey === "refresh"}>
            Refresh
          </button>
          <button type="button" onClick={() => void handleSignOut()} disabled={busyKey === "sign-out"}>
            Sign Out
          </button>
        </div>
      </header>

      <nav className="route-nav" aria-label="Primary">
        {appRoutes
          .filter((item) => item !== "/login")
          .map((item) => (
            <button
              key={item}
              className={route === item ? "nav-button nav-button-active" : "nav-button"}
              onClick={() => navigateTo(item)}
              type="button"
            >
              {item.replace("/", "").replace("-", " ")}
              {item === "/approvals" && pendingApprovals.length > 0 ? ` (${pendingApprovals.length})` : ""}
              {item === "/agents" && quarantinedAgents.length > 0 ? ` (${quarantinedAgents.length})` : ""}
            </button>
          ))}
      </nav>

      <section className="status-strip">
        <span>WebSocket: {wsState}</span>
        <span>Last event: {lastEvent}</span>
        <span>Connected accounts: {connections.length}</span>
        <span>Pending approvals: {pendingApprovals.length}</span>
      </section>

      {banner ? <div className={`banner banner-${banner.tone}`}>{banner.text}</div> : null}

      {route === "/overview" ? (
        <section className="page-stack">
          <section className="summary-grid">
            <SummaryCard
              label="Auto-approved"
              value={summary?.auto_approved_count ?? 0}
              note="Low-risk actions completed without manual intervention."
            />
            <SummaryCard
              label="Approvals requested"
              value={summary?.approval_requested_count ?? 0}
              note="Medium-risk actions waiting on a human decision."
            />
            <SummaryCard
              label="Actions blocked"
              value={summary?.blocked_count ?? 0}
              note="Actions denied before provider execution."
            />
            <SummaryCard
              label="Agents quarantined"
              value={summary?.quarantined_count ?? 0}
              note="Agents isolated after repeated unsafe requests."
            />
          </section>

          <section className="grid-two">
            <article className="panel">
              <SectionHeader
                title="Latest Protected Action"
                subtitle="The most recent action where Chorus stepped in with approval, blocking, or quarantine."
                actions={
                  latestProtectedAction ? (
                    <button type="button" onClick={() => void openActionDetail(latestProtectedAction.id)}>
                      Open Action Details
                    </button>
                  ) : undefined
                }
              />
              {latestProtectedAction ? (
                <ActionCard action={latestProtectedAction} onOpenDetail={(actionId) => void openActionDetail(actionId)} />
              ) : (
                <EmptyState title="No protected actions yet" copy="Run an approval or quarantine scenario to populate the spotlight." />
              )}
            </article>

            <article className="panel">
              <SectionHeader
                title="Quick Demo Controls"
                subtitle="Use these controls for the 90-second judge walkthrough."
                actions={
                  <button type="button" onClick={() => navigateTo("/approvals")}>
                    Go To Approvals
                  </button>
                }
              />
              <div className="button-grid">
                <button type="button" onClick={() => void handleStartConnection("gmail")} disabled={busyKey === "connect-gmail"}>
                  Connect Gmail
                </button>
                <button type="button" onClick={() => void handleStartConnection("github")} disabled={busyKey === "connect-github"}>
                  Connect GitHub
                </button>
                <button type="button" onClick={() => void handleRunScenario("allow")} disabled={busyKey === "scenario-allow"}>
                  Run Allow Scenario
                </button>
                <button type="button" onClick={() => void handleRunScenario("approval")} disabled={busyKey === "scenario-approval"}>
                  Run Approval Scenario
                </button>
                <button
                  type="button"
                  onClick={() => void handleRunScenario("quarantine")}
                  disabled={busyKey === "scenario-quarantine"}
                >
                  Run Quarantine Scenario
                </button>
                <button type="button" onClick={() => void handleResetDemo()} disabled={busyKey === "reset-demo"}>
                  Reset Demo
                </button>
              </div>
            </article>

            <article className="panel">
              <SectionHeader
                title="Recent Pending Approvals"
                subtitle="Each request stays attached to the requesting agent, provider, and explanation."
              />
              <div className="stack">
                {pendingApprovals.slice(0, 3).map((approval) => (
                  <article key={approval.id} className="item-card item-compact">
                    <strong>{approval.agent_name}</strong>
                    <p>{approval.capability_name}</p>
                    <p className="muted">{approval.explanation || "Awaiting decision."}</p>
                    <div className="button-row">
                      <button type="button" onClick={() => void handleApproval(approval.id, "approve")}>
                        Approve
                      </button>
                      <button type="button" onClick={() => void openActionDetail(approval.action_request_id)}>
                        Open Action Details
                      </button>
                    </div>
                  </article>
                ))}
                {pendingApprovals.length === 0 ? (
                  <EmptyState title="No approvals waiting" copy="Run the approval scenario to populate this queue." />
                ) : null}
              </div>
            </article>

            <article className="panel">
              <SectionHeader
                title="Recent Blocked Or Quarantined Actions"
                subtitle="This is the fast proof that risky behavior gets interrupted before damage spreads."
              />
              <div className="stack">
                {actions
                  .filter((action) => action.enforcement_decision === "BLOCK" || action.enforcement_decision === "QUARANTINE")
                  .slice(0, 3)
                  .map((action) => (
                    <ActionCard key={action.id} action={action} onOpenDetail={(actionId) => void openActionDetail(actionId)} />
                  ))}
                {actions.filter((action) => action.enforcement_decision === "BLOCK" || action.enforcement_decision === "QUARANTINE")
                  .length === 0 ? (
                  <EmptyState title="No blocked actions yet" copy="Run the quarantine scenario to create the standout intervention moment." />
                ) : null}
              </div>
            </article>
          </section>
        </section>
      ) : null}

      {route === "/connections" ? (
        <section className="page-stack">
          <article className="panel">
            <SectionHeader
              title="Connections"
              subtitle="Provider accounts are connected through Token Vault, not handed directly to agents."
            />
            <TabBar
              active={connectionsTab}
              onChange={setConnectionsTab}
              tabs={[
                { id: "accounts", label: "Accounts" },
                { id: "scopes", label: "Scopes" },
                { id: "health", label: "Connection Health" },
              ]}
            />
          </article>

          <section className="grid-two">
            <article className="panel">
              <SectionHeader
                title="Provider Cards"
                subtitle="Each card shows mode, scopes, health, and the provider account Chorus can protect."
                actions={
                  <div className="button-row">
                    <button type="button" onClick={() => void handleStartConnection("gmail")}>
                      Connect Gmail
                    </button>
                    <button type="button" onClick={() => void handleStartConnection("github")}>
                      Connect GitHub
                    </button>
                  </div>
                }
              />
              <div className="stack">
                {connections.map((connection) => (
                  <article key={connection.id} className="item-card">
                    <div className="item-card-header">
                      <div>
                        <h3>{connection.display_label || connection.provider}</h3>
                        <p className="muted">{connection.external_account_id || "No external account id recorded"}</p>
                      </div>
                      <div className="badge-row">
                        <span className="badge">{connection.mode}</span>
                        <span className="badge">{connection.connection_health}</span>
                      </div>
                    </div>
                    <p>{summarizeScopes(connection.granted_scopes)}</p>
                    <div className="button-row">
                      <button type="button" onClick={() => void handleStartConnection(connection.provider)}>
                        Reconnect
                      </button>
                      <button type="button" onClick={() => void handleDisconnectConnection(connection.id)}>
                        Disconnect
                      </button>
                      <button type="button" onClick={() => void handleRefreshConnection(connection.id)}>
                        Refresh Connection
                      </button>
                      <button type="button" onClick={() => setSelectedConnectionId(connection.id)}>
                        View Vault Reference
                      </button>
                    </div>
                  </article>
                ))}
                {connections.length === 0 ? (
                  <EmptyState title="No accounts connected" copy="Connect Gmail and GitHub to unlock live delegated actions." />
                ) : null}
              </div>
            </article>

            <article className="panel">
              {connectionsTab === "accounts" ? (
                <>
                  <SectionHeader
                    title="Vault Mediation Notes"
                    subtitle="This panel is where you can emphasize that Chorus brokers provider access instead of passing out raw credentials."
                  />
                  {selectedConnection ? (
                    <dl className="kv-grid">
                      <div>
                        <dt>Provider</dt>
                        <dd>{selectedConnection.provider}</dd>
                      </div>
                      <div>
                        <dt>Mode</dt>
                        <dd>{selectedConnection.mode}</dd>
                      </div>
                      <div>
                        <dt>Status</dt>
                        <dd>{selectedConnection.status}</dd>
                      </div>
                      <div>
                        <dt>Last synced</dt>
                        <dd>{formatDate(selectedConnection.last_synced_at)}</dd>
                      </div>
                      <div className="kv-full">
                        <dt>Vault reference</dt>
                        <dd>{selectedConnection.vault_reference}</dd>
                      </div>
                    </dl>
                  ) : (
                    <EmptyState title="Select a connection" copy="Choose a connection card to inspect its vault reference." />
                  )}
                </>
              ) : null}

              {connectionsTab === "scopes" ? (
                <>
                  <SectionHeader
                    title="Granted Scopes View"
                    subtitle="Judges should be able to see exactly what Gmail or GitHub access was delegated."
                  />
                  <div className="stack">
                    {connections.map((connection) => (
                      <article key={`${connection.id}-scopes`} className="item-card item-compact">
                        <strong>{connection.display_label || connection.provider}</strong>
                        <p>{summarizeScopes(connection.granted_scopes)}</p>
                      </article>
                    ))}
                  </div>
                </>
              ) : null}

              {connectionsTab === "health" ? (
                <>
                  <SectionHeader
                    title="Callback And Health Status"
                    subtitle="Keep this section simple so you can layer your own visual treatment on top later."
                  />
                  <div className="stack">
                    {connections.map((connection) => (
                      <article key={`${connection.id}-health`} className="item-card item-compact">
                        <strong>{connection.provider}</strong>
                        <p className="muted">Health: {connection.connection_health}</p>
                        <p className="muted">Last synced: {formatDate(connection.last_synced_at)}</p>
                      </article>
                    ))}
                  </div>
                </>
              ) : null}
            </article>
          </section>
        </section>
      ) : null}

      {route === "/agents" ? (
        <section className="page-stack">
          <article className="panel">
            <SectionHeader
              title="Agents"
              subtitle="Chorus enforces scoped capability grants per agent and exposes quarantine state directly in the UI."
            />
            <TabBar
              active={agentsTab}
              onChange={setAgentsTab}
              tabs={[
                { id: "registry", label: "Registry" },
                { id: "capability-grants", label: "Capability Grants" },
                { id: "quarantine", label: "Quarantine" },
              ]}
            />
          </article>

          <section className="grid-two">
            <article className="panel">
              <SectionHeader title="Agent List" subtitle="This is the registry view judges can scan in a few seconds." />
              <div className="stack">
                {agents.map((agent) => (
                  <article key={agent.id} className="item-card">
                    <div className="item-card-header">
                      <div>
                        <h3>{agent.name}</h3>
                        <p className="muted">{agent.description || "No description provided."}</p>
                      </div>
                      <div className="badge-row">
                        <span className="badge">{agent.agent_type}</span>
                        <span className="badge">{agent.status}</span>
                      </div>
                    </div>
                    <div className="stack compact-gap">
                      {agent.capabilities.map((capability) => (
                        <article key={capability.id} className="item-card item-compact">
                          <strong>{capability.capability_name}</strong>
                          <p className="muted">{JSON.stringify(capability.constraints)}</p>
                        </article>
                      ))}
                      {agent.capabilities.length === 0 ? <p className="muted">No capability grants yet.</p> : null}
                    </div>
                    <div className="button-row">
                      <button type="button" onClick={() => handleViewActionHistory(agent.id)}>
                        View Action History
                      </button>
                      <button type="button" disabled>
                        Disable Agent
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleReleaseQuarantine(agent.id)}
                        disabled={agent.status !== "quarantined"}
                      >
                        Release Quarantine
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </article>

            <article className="panel">
              {agentsTab !== "quarantine" ? (
                <>
                  <SectionHeader
                    title={agentsTab === "registry" ? "Create Agent" : "Capability Editor"}
                    subtitle={
                      agentsTab === "registry"
                        ? "Create the specialist agents used in the demo story."
                        : "Grant or update provider-specific constraints for an agent."
                    }
                  />
                  {agentsTab === "registry" ? (
                    <form className="stack" onSubmit={(event) => void handleCreateAgent(event)}>
                      <label>
                        Agent name
                        <input value={agentName} onChange={(event) => setAgentName(event.target.value)} required />
                      </label>
                      <label>
                        Agent type
                        <input value={agentType} onChange={(event) => setAgentType(event.target.value)} required />
                      </label>
                      <label>
                        Description
                        <textarea value={agentDescription} onChange={(event) => setAgentDescription(event.target.value)} rows={4} />
                      </label>
                      <div className="button-row">
                        <button type="submit" disabled={busyKey === "create-agent"}>
                          Create Agent
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div className="stack">
                      <label>
                        Agent
                        <select value={grantAgentId} onChange={(event) => setGrantAgentId(event.target.value)}>
                          {agents.map((agent) => (
                            <option key={agent.id} value={agent.id}>
                              {agent.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Capability
                        <select value={grantCapabilityName} onChange={(event) => setGrantCapabilityName(event.target.value)}>
                          {capabilityCatalog.map((capability) => (
                            <option key={capability.name} value={capability.name}>
                              {capability.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Constraint editor
                        <input value={grantConstraints} onChange={(event) => setGrantConstraints(event.target.value)} />
                      </label>
                      <p className="muted">
                        Default risk: {selectedCapability.risk}. Constraint hint: {selectedCapability.constraintHint}.
                      </p>
                      <div className="button-row">
                        <button type="button" onClick={() => void handleGrantCapability("grant")}>
                          Grant Capability
                        </button>
                        <button type="button" onClick={() => void handleGrantCapability("update")}>
                          Update Constraints
                        </button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <SectionHeader
                    title="Quarantine State"
                    subtitle="This section makes the escalation path explicit: reason, current state, and manual release."
                  />
                  <div className="stack">
                    {quarantinedAgents.map((agent) => (
                      <article key={`${agent.id}-quarantine`} className="item-card">
                        <strong>{agent.name}</strong>
                        <p>{agent.quarantine_reason || "No quarantine reason recorded."}</p>
                        <div className="button-row">
                          <button type="button" onClick={() => void handleReleaseQuarantine(agent.id)}>
                            Release Quarantine
                          </button>
                          <button type="button" onClick={() => handleViewActionHistory(agent.id)}>
                            View Action History
                          </button>
                        </div>
                      </article>
                    ))}
                    {quarantinedAgents.length === 0 ? (
                      <EmptyState title="No quarantined agents" copy="Run the quarantine scenario to show the enforcement path." />
                    ) : null}
                  </div>
                </>
              )}
            </article>
          </section>
        </section>
      ) : null}

      {route === "/approvals" ? (
        <section className="page-stack">
          <article className="panel">
            <SectionHeader title="Approvals" subtitle="Approval requests stay short, human-readable, and one click away from a decision." />
            <TabBar
              active={approvalsTab}
              onChange={setApprovalsTab}
              tabs={[
                { id: "pending", label: "Pending" },
                { id: "resolved", label: "Resolved" },
              ]}
            />
          </article>

          <section className="grid-two">
            <article className="panel">
              <SectionHeader
                title="Approval Queue"
                subtitle={approvalsTab === "pending" ? "Pending requests needing a decision." : "Recently resolved approval decisions."}
              />
              <div className="stack">
                {(approvalsTab === "pending" ? pendingApprovals : resolvedApprovals).map((approval) => (
                  <article key={approval.id} className="item-card">
                    <div className="item-card-header">
                      <div>
                        <h3>{approval.agent_name}</h3>
                        <p className="muted">{approval.capability_name}</p>
                      </div>
                      <span className="badge">{approval.status}</span>
                    </div>
                    <p>{approval.explanation || "No explanation available."}</p>
                    <div className="button-row">
                      {approval.status === "pending" ? (
                        <>
                          <button type="button" onClick={() => void handleApproval(approval.id, "approve")}>
                            Approve
                          </button>
                          <button type="button" onClick={() => void handleApproval(approval.id, "reject")}>
                            Reject
                          </button>
                        </>
                      ) : null}
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedApprovalId(approval.id);
                          void openActionDetail(approval.action_request_id);
                        }}
                      >
                        Open Details
                      </button>
                      <button type="button" onClick={() => handleOpenAuditTrail(approval.action_request_id)}>
                        Open Audit Trail
                      </button>
                    </div>
                  </article>
                ))}
                {(approvalsTab === "pending" ? pendingApprovals : resolvedApprovals).length === 0 ? (
                  <EmptyState
                    title={approvalsTab === "pending" ? "No pending approvals" : "No resolved approvals yet"}
                    copy="Run the approval scenario to populate this workflow."
                  />
                ) : null}
              </div>
            </article>

            <article className="panel">
              <SectionHeader title="Approval Detail Panel" subtitle="Use this panel for the story around why the action was paused." />
              {selectedApproval ? (
                <div className="stack">
                  <dl className="kv-grid">
                    <div>
                      <dt>Agent</dt>
                      <dd>{selectedApproval.agent_name}</dd>
                    </div>
                    <div>
                      <dt>Provider</dt>
                      <dd>{selectedApproval.provider}</dd>
                    </div>
                    <div>
                      <dt>Status</dt>
                      <dd>{selectedApproval.status}</dd>
                    </div>
                    <div>
                      <dt>Requested</dt>
                      <dd>{formatDate(selectedApproval.requested_at)}</dd>
                    </div>
                  </dl>
                  <p>{selectedApproval.explanation || "No explanation recorded."}</p>
                  <div className="button-row">
                    {selectedApproval.status === "pending" ? (
                      <>
                        <button type="button" onClick={() => void handleApproval(selectedApproval.id, "approve")}>
                          Approve
                        </button>
                        <button type="button" onClick={() => void handleApproval(selectedApproval.id, "reject")}>
                          Reject
                        </button>
                      </>
                    ) : null}
                    <button type="button" onClick={() => void openActionDetail(selectedApproval.action_request_id)}>
                      Open Details
                    </button>
                    <button type="button" onClick={() => handleOpenAuditTrail(selectedApproval.action_request_id)}>
                      Open Audit Trail
                    </button>
                  </div>

                  <SectionHeader title="Recent Approval Outcomes" subtitle="Resolved requests stay visible for credibility and auditability." />
                  <div className="stack">
                    {resolvedApprovals.slice(0, 3).map((approval) => (
                      <article key={`${approval.id}-resolved`} className="item-card item-compact">
                        <strong>{approval.agent_name}</strong>
                        <p className="muted">{approval.status}</p>
                      </article>
                    ))}
                  </div>
                </div>
              ) : (
                <EmptyState title="No approval selected" copy="Select a queue item to inspect the approval context." />
              )}
            </article>
          </section>
        </section>
      ) : null}

      {route === "/activity" ? (
        <section className="page-stack">
          <article className="panel">
            <SectionHeader title="Activity" subtitle="Every action row exposes the agent, risk, decision, explanation, and final outcome." />
            <TabBar
              active={activityTab}
              onChange={setActivityTab}
              tabs={[
                { id: "timeline", label: "Timeline" },
                { id: "by-action", label: "By Action" },
                { id: "by-agent", label: "By Agent" },
              ]}
            />
          </article>

          <article className="panel">
            <SectionHeader title="Filter Bar" subtitle="These controls are here so you can layer stronger visual affordances later." />
            <div className="button-row">
              <button type="button" onClick={() => setDecisionFilter("ALLOW")}>
                Filter ALLOW
              </button>
              <button type="button" onClick={() => setDecisionFilter("REQUIRE_APPROVAL")}>
                Filter APPROVAL
              </button>
              <button type="button" onClick={() => setDecisionFilter("BLOCK")}>
                Filter BLOCK
              </button>
              <button type="button" onClick={() => setDecisionFilter("QUARANTINE")}>
                Filter QUARANTINE
              </button>
              <button type="button" onClick={() => setDecisionFilter("ALL")}>
                Clear Filters
              </button>
            </div>
            <label className="inline-field">
              Agent
              <select value={activityAgentFilter} onChange={(event) => setActivityAgentFilter(event.target.value)}>
                <option value="ALL">All agents</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            </label>
          </article>

          {activityTab === "timeline" ? (
            <article className="panel">
              <SectionHeader title="Event Timeline" subtitle="Chronological action history with buttons to inspect details or jump to live provider results." />
              <div className="stack">
                {filteredActions.map((action) => (
                  <ActionCard
                    key={action.id}
                    action={action}
                    agentName={agents.find((agent) => agent.id === action.agent_id)?.name}
                    onOpenDetail={(actionId) => void openActionDetail(actionId)}
                    onOpenProviderResult={handleOpenProviderResult}
                    onJumpToAgent={(agentId) => handleViewActionHistory(agentId)}
                  />
                ))}
                {filteredActions.length === 0 ? (
                  <EmptyState title="No actions for this filter" copy="Adjust the decision or agent filter to widen the timeline." />
                ) : null}
              </div>
            </article>
          ) : null}

          {activityTab === "by-action" ? (
            <article className="panel">
              <SectionHeader title="By Action" subtitle="Focused list of action records for detail-driven review." />
              <div className="stack">
                {filteredActions.map((action) => (
                  <article key={`${action.id}-action`} className="item-card">
                    <strong>{actionTitle(action)}</strong>
                    <p>{action.explanation || action.risk_explanation || "No explanation available."}</p>
                    <div className="button-row">
                      <button type="button" onClick={() => void openActionDetail(action.id)}>
                        Open Details
                      </button>
                      {action.provider_result_url ? (
                        <button type="button" onClick={() => handleOpenProviderResult(action.provider_result_url!)}>
                          Open Provider Result
                        </button>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            </article>
          ) : null}

          {activityTab === "by-agent" ? (
            <article className="panel">
              <SectionHeader title="By Agent" subtitle="Grouped action history makes repeated violations or healthy behavior easy to spot." />
              <div className="stack">
                {actionsByAgent.map((entry) => (
                  <article key={`${entry.agent.id}-group`} className="panel nested-panel">
                    <SectionHeader title={entry.agent.name} subtitle={entry.agent.description || "No description recorded."} />
                    <div className="stack">
                      {entry.actions.map((action) => (
                        <ActionCard key={action.id} action={action} onOpenDetail={(actionId) => void openActionDetail(actionId)} />
                      ))}
                    </div>
                  </article>
                ))}
                {actionsByAgent.length === 0 ? (
                  <EmptyState title="No grouped activity yet" copy="Run a scenario or clear the current filter to populate this view." />
                ) : null}
              </div>
            </article>
          ) : null}
        </section>
      ) : null}

      {route === "/demo" ? (
        <section className="page-stack">
          <article className="panel">
            <SectionHeader title="Guided Demo" subtitle="This page keeps the hostable walkthrough repeatable and easy to rehearse." />
          </article>

          <section className="grid-two">
            <article className="panel">
              <SectionHeader title="Guided Story Steps" subtitle="This sequence matches the 90-second pitch flow." />
              <ol className="plain-list numbered-list">
                <li>Show connected Gmail and GitHub accounts.</li>
                <li>Show scoped capability grants for each agent.</li>
                <li>Run the allow scenario.</li>
                <li>Run the approval scenario and approve the issue.</li>
                <li>Run the quarantine scenario.</li>
                <li>Finish on the action detail drawer and audit trail.</li>
              </ol>
            </article>

            <article className="panel">
              <SectionHeader title="Scenario Runner" subtitle="These buttons are the main judge-controls you asked for." />
              <div className="button-grid">
                <button type="button" onClick={() => void handleRunFullDemo()} disabled={busyKey === "scenario-full"}>
                  Run Full Demo
                </button>
                <button type="button" onClick={() => void handleRunScenario("allow")} disabled={busyKey === "scenario-allow"}>
                  Run Allow Step
                </button>
                <button
                  type="button"
                  onClick={() => void handleRunScenario("approval")}
                  disabled={busyKey === "scenario-approval"}
                >
                  Run Approval Step
                </button>
                <button
                  type="button"
                  onClick={() => void handleRunScenario("quarantine")}
                  disabled={busyKey === "scenario-quarantine"}
                >
                  Run Quarantine Step
                </button>
                <button type="button" onClick={() => void handleResetDemo()} disabled={busyKey === "reset-demo"}>
                  Reset Workspace
                </button>
                <button type="button" onClick={() => void handleCopyDemoScript()}>
                  Copy Demo Script
                </button>
              </div>
            </article>

            <article className="panel">
              <SectionHeader title="Environment Readiness" subtitle="Keep this simple so you can style live vs mock state however you want." />
              <dl className="kv-grid">
                <div>
                  <dt>Auth mode</dt>
                  <dd>{authSession.auth_mode}</dd>
                </div>
                <div>
                  <dt>WebSocket</dt>
                  <dd>{wsState}</dd>
                </div>
                <div>
                  <dt>Connections</dt>
                  <dd>{connections.length}</dd>
                </div>
                <div>
                  <dt>Providers</dt>
                  <dd>{connectionModeSummary(connections)}</dd>
                </div>
              </dl>
            </article>

            <article className="panel">
              <SectionHeader title="Live / Mock Execution Status" subtitle="The point is clarity, not pretending every call ran live." />
              <div className="stack">
                {actions.slice(0, 5).map((action) => (
                  <article key={`${action.id}-mode`} className="item-card item-compact">
                    <strong>{action.capability_name}</strong>
                    <p className="muted">
                      {action.execution_mode ?? "pending"} · {action.status}
                    </p>
                  </article>
                ))}
                {actions.length === 0 ? (
                  <EmptyState title="No recent executions" copy="Run a scenario to see live, mock, or fallback execution labels here." />
                ) : null}
              </div>
            </article>

            <article className="panel panel-full">
              <SectionHeader title="Recent Demo Runs" subtitle="A short history makes it obvious that reset and replay are deterministic." />
              <div className="stack">
                {demoRuns.map((entry) => (
                  <article key={entry} className="item-card item-compact">
                    <strong>{entry}</strong>
                  </article>
                ))}
                {demoRuns.length === 0 ? (
                  <EmptyState title="No scenarios run yet" copy="Use the scenario runner to build a repeatable judge walkthrough." />
                ) : null}
              </div>
            </article>
          </section>
        </section>
      ) : null}

      {selectedDetailId ? (
        <aside className="detail-drawer" aria-live="polite">
          <div className="detail-drawer-header">
            <div>
              <p className="eyebrow">Action Detail</p>
              <h2>{selectedDetail?.action ? actionTitle(selectedDetail.action) : "Loading action detail"}</h2>
            </div>
            <button
              type="button"
              onClick={() => {
                setSelectedDetailId(null);
                setSelectedDetail(null);
              }}
            >
              Close
            </button>
          </div>

          {detailLoading ? <p className="muted">Loading action detail…</p> : null}

          {selectedDetail ? (
            <div className="stack">
              <section className="panel nested-panel">
                <SectionHeader title="Action" subtitle="Agent, capability, risk, decision, and final outcome." />
                <dl className="kv-grid">
                  <div>
                    <dt>Agent</dt>
                    <dd>{selectedDetail.agent_name}</dd>
                  </div>
                  <div>
                    <dt>Decision</dt>
                    <dd>{decisionDescription(selectedDetail.action.enforcement_decision)}</dd>
                  </div>
                  <div>
                    <dt>Risk</dt>
                    <dd>{selectedDetail.action.risk_level ?? "unrated"}</dd>
                  </div>
                  <div>
                    <dt>Outcome</dt>
                    <dd>{selectedDetail.action.status}</dd>
                  </div>
                  <div className="kv-full">
                    <dt>Reason</dt>
                    <dd>{selectedDetail.action.risk_explanation || selectedDetail.action.explanation || "No explanation recorded."}</dd>
                  </div>
                </dl>
              </section>

              <section className="panel nested-panel">
                <SectionHeader title="Connection Summary" subtitle="Which connected account and vault reference Chorus used or would have used." />
                {selectedDetail.connection_summary ? (
                  <dl className="kv-grid">
                    <div>
                      <dt>Provider</dt>
                      <dd>{selectedDetail.connection_summary.provider}</dd>
                    </div>
                    <div>
                      <dt>Mode</dt>
                      <dd>{selectedDetail.connection_summary.mode ?? "unknown"}</dd>
                    </div>
                    <div className="kv-full">
                      <dt>Vault reference</dt>
                      <dd>{selectedDetail.connection_summary.vault_reference ?? "No vault reference recorded"}</dd>
                    </div>
                    <div className="kv-full">
                      <dt>Granted scopes</dt>
                      <dd>{summarizeScopes(selectedDetail.connection_summary.granted_scopes)}</dd>
                    </div>
                  </dl>
                ) : (
                  <p className="muted">No connection summary recorded for this action.</p>
                )}
              </section>

              <section className="panel nested-panel">
                <SectionHeader title="Approval Record" subtitle="When approval was required, this record shows who resolved it and when." />
                {selectedDetail.approval_record ? (
                  <dl className="kv-grid">
                    <div>
                      <dt>Status</dt>
                      <dd>{selectedDetail.approval_record.status}</dd>
                    </div>
                    <div>
                      <dt>Decided</dt>
                      <dd>{formatDate(selectedDetail.approval_record.decided_at)}</dd>
                    </div>
                    <div className="kv-full">
                      <dt>Reason</dt>
                      <dd>{selectedDetail.approval_record.reason || "No reason recorded."}</dd>
                    </div>
                  </dl>
                ) : (
                  <p className="muted">No approval record is attached to this action.</p>
                )}
              </section>

              <section className="panel nested-panel">
                <SectionHeader title="Execution Record" subtitle="Execution details stay explicit about live, mock, and provider result metadata." />
                {selectedDetail.execution_record ? (
                  <dl className="kv-grid">
                    <div>
                      <dt>Status</dt>
                      <dd>{selectedDetail.execution_record.status}</dd>
                    </div>
                    <div>
                      <dt>Mode</dt>
                      <dd>{selectedDetail.execution_record.execution_mode ?? "unknown"}</dd>
                    </div>
                    <div>
                      <dt>Reference</dt>
                      <dd>{selectedDetail.execution_record.external_reference_id ?? "No provider reference"}</dd>
                    </div>
                    <div>
                      <dt>Executed</dt>
                      <dd>{formatDate(selectedDetail.execution_record.executed_at)}</dd>
                    </div>
                    <div className="kv-full">
                      <dt>Summary</dt>
                      <dd>{selectedDetail.execution_record.summary || "No execution summary recorded."}</dd>
                    </div>
                  </dl>
                ) : (
                  <p className="muted">No execution record is attached to this action.</p>
                )}
              </section>

              <section className="panel nested-panel">
                <SectionHeader title="Audit Events" subtitle="This is the concise per-action timeline you can dress up visually later." />
                <div className="stack">
                  {selectedDetail.audit_events.map((event) => (
                    <article key={event.id} className="item-card item-compact">
                      <strong>{event.event_type}</strong>
                      <p>{event.message}</p>
                      <p className="muted">{formatDate(event.occurred_at)}</p>
                    </article>
                  ))}
                  {selectedDetail.audit_events.length === 0 ? <p className="muted">No audit events recorded.</p> : null}
                </div>
              </section>
            </div>
          ) : null}
        </aside>
      ) : null}
    </main>
  );
}
