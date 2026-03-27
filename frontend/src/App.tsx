import { FormEvent, useEffect, useState } from "react";

import { api, connectDashboardSocket } from "./api";
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

type CapabilityDefinition = {
  name: string;
  provider: Provider;
  label: string;
  risk: string;
  constraintHint: string;
};

const capabilityCatalog: CapabilityDefinition[] = [
  {
    name: "gmail.draft.create",
    provider: "gmail",
    label: "Gmail Draft Create",
    risk: "Low",
    constraintHint: "Allowed email domain",
  },
  {
    name: "github.issue.create",
    provider: "github",
    label: "GitHub Issue Create",
    risk: "Medium",
    constraintHint: "Approved repository",
  },
  {
    name: "github.pull_request.merge",
    provider: "github",
    label: "GitHub Pull Request Merge",
    risk: "High",
    constraintHint: "Approved repository",
  },
];

const defaultCapabilityByProvider: Record<Provider, string> = {
  gmail: "gmail.draft.create",
  github: "github.issue.create",
};

function formatDate(value: string | null): string {
  if (!value) {
    return "Waiting";
  }
  return new Date(value).toLocaleString();
}

function summarizeConnectionScopes(scopes: string[]): string {
  if (scopes.length === 0) {
    return "No scopes recorded";
  }
  return scopes.join(", ");
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

function buildActionPayload(
  capabilityName: string,
  fields: {
    recipient: string;
    subject: string;
    message: string;
    repository: string;
    title: string;
    prNumber: string;
  },
): Record<string, unknown> {
  if (capabilityName === "gmail.draft.create") {
    return {
      to: fields.recipient
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
      subject: fields.subject,
      body: fields.message,
    };
  }

  if (capabilityName === "github.issue.create") {
    return {
      repository: fields.repository,
      title: fields.title,
      body: fields.message,
    };
  }

  return {
    repository: fields.repository,
    pull_request_number: Number(fields.prNumber || "0"),
    summary: fields.message,
  };
}

export default function App() {
  const [me, setMe] = useState<User | null>(null);
  const [connections, setConnections] = useState<ConnectedAccount[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [actions, setActions] = useState<ActionRequest[]>([]);
  const [approvals, setApprovals] = useState<ApprovalQueueItem[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsState, setWsState] = useState("connecting");
  const [lastEvent, setLastEvent] = useState("Waiting for dashboard activity");
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const [connectionProvider, setConnectionProvider] = useState<Provider>("gmail");
  const [connectionExternalId, setConnectionExternalId] = useState("");
  const [connectionScopes, setConnectionScopes] = useState("gmail.compose gmail.readonly");

  const [agentName, setAgentName] = useState("");
  const [agentType, setAgentType] = useState("assistant");
  const [agentDescription, setAgentDescription] = useState("");

  const [grantSelections, setGrantSelections] = useState<Record<string, string>>({});
  const [grantConstraints, setGrantConstraints] = useState<Record<string, string>>({});

  const [actionAgentId, setActionAgentId] = useState("");
  const [actionCapabilityName, setActionCapabilityName] = useState("gmail.draft.create");
  const [recipient, setRecipient] = useState("judge@authorizedtoact.dev");
  const [subject, setSubject] = useState("Chorus delegated action summary");
  const [message, setMessage] = useState("Draft prepared by Chorus with scoped delegated access.");
  const [repository, setRepository] = useState("chorus/secure-demo");
  const [issueTitle, setIssueTitle] = useState("Audit the approval path");
  const [prNumber, setPrNumber] = useState("18");

  async function refreshDashboard() {
    const [meResponse, connectionResponse, agentResponse, actionResponse, approvalResponse, auditResponse] =
      await Promise.all([
        api.getMe(),
        api.getConnections(),
        api.getAgents(),
        api.getActions(),
        api.getApprovals(),
        api.getAudit(),
      ]);

    setMe(meResponse);
    setConnections(connectionResponse);
    setAgents(agentResponse);
    setActions(actionResponse);
    setApprovals(approvalResponse);
    setAudit(auditResponse);
    setActionAgentId((current) => current || agentResponse[0]?.id || "");
  }

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        await refreshDashboard();
        if (active) {
          setError(null);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load dashboard");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();

    const socket = connectDashboardSocket((event: DashboardEvent) => {
      setLastEvent(`${event.type} at ${formatDate(event.timestamp)}`);
      void refreshDashboard();
    });

    socket.onopen = () => setWsState("live");
    socket.onerror = () => setWsState("degraded");
    socket.onclose = () => setWsState("offline");

    return () => {
      active = false;
      socket.close();
    };
  }, []);

  const quarantinedAgents = agents.filter((agent) => agent.status === "quarantined");
  const pendingApprovals = approvals.filter((approval) => approval.status === "pending");

  const selectedCapability =
    capabilityCatalog.find((capability) => capability.name === actionCapabilityName) ?? capabilityCatalog[0];

  async function handleConnectionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("connection");
    try {
      await api.createConnection({
        provider: connectionProvider,
        external_account_id: connectionExternalId || undefined,
        scopes: connectionScopes
          .split(/[,\s]+/)
          .map((value) => value.trim())
          .filter(Boolean),
      });
      setConnectionExternalId("");
      if (connectionProvider === "gmail") {
        setConnectionScopes("gmail.compose gmail.readonly");
      } else {
        setConnectionScopes("repo issues:write pull_requests:write");
      }
      await refreshDashboard();
      setError(null);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to save connection");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleAgentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("agent");
    try {
      await api.createAgent({
        name: agentName,
        agent_type: agentType,
        description: agentDescription,
      });
      setAgentName("");
      setAgentDescription("");
      await refreshDashboard();
      setError(null);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Failed to create agent");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleGrant(agentId: string) {
    const capabilityName = grantSelections[agentId] ?? "gmail.draft.create";
    const constraintValue =
      grantConstraints[agentId] ??
      (capabilityName === "gmail.draft.create" ? "authorizedtoact.dev" : "chorus/secure-demo");

    setBusyKey(`grant-${agentId}`);
    try {
      await api.grantCapability(agentId, {
        capability_name: capabilityName,
        constraints: buildGrantConstraints(capabilityName, constraintValue),
      });
      await refreshDashboard();
      setError(null);
    } catch (grantError) {
      setError(grantError instanceof Error ? grantError.message : "Failed to grant capability");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleActionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusyKey("action");
    try {
      await api.createAction({
        agent_id: actionAgentId,
        provider: selectedCapability.provider,
        capability_name: actionCapabilityName,
        payload: buildActionPayload(actionCapabilityName, {
          recipient,
          subject,
          message,
          repository,
          title: issueTitle,
          prNumber,
        }),
      });
      await refreshDashboard();
      setError(null);
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Failed to submit action");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleApproval(approvalId: string, decision: "approve" | "reject") {
    setBusyKey(`${decision}-${approvalId}`);
    try {
      if (decision === "approve") {
        await api.approve(approvalId, "Approved from the control plane dashboard.");
      } else {
        await api.reject(approvalId, "Rejected from the control plane dashboard.");
      }
      await refreshDashboard();
      setError(null);
    } catch (approvalError) {
      setError(approvalError instanceof Error ? approvalError.message : "Failed to resolve approval");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="app-shell">
      <div className="background-orb background-orb-left" />
      <div className="background-orb background-orb-right" />
      <header className="hero">
        <div>
          <p className="eyebrow">Authorized Agent Actions</p>
          <h1>Chorus turns delegated AI actions into a visible, approval-aware control plane.</h1>
          <p className="hero-copy">
            Connect Gmail and GitHub, scope each agent to the smallest safe capability, and watch policy,
            risk, approval, block, and quarantine decisions move through a single timeline.
          </p>
        </div>
        <div className="hero-status-card">
          <span className={`status-pill status-${wsState}`}>Realtime {wsState}</span>
          <p className="hero-stat-label">Last dashboard event</p>
          <p className="hero-stat-value">{lastEvent}</p>
          <p className="hero-stat-label">Signed in as</p>
          <p className="hero-stat-value">{me ? `${me.display_name} (${me.email})` : "Loading identity"}</p>
        </div>
      </header>

      <section className="summary-grid">
        <article className="summary-card">
          <span>Connected accounts</span>
          <strong>{connections.length}</strong>
          <p>Mock-first Auth0 and Token Vault adapters stay server-side.</p>
        </article>
        <article className="summary-card">
          <span>Registered agents</span>
          <strong>{agents.length}</strong>
          <p>Each agent carries its own capability grants and quarantine state.</p>
        </article>
        <article className="summary-card">
          <span>Pending approvals</span>
          <strong>{pendingApprovals.length}</strong>
          <p>Medium-risk actions pause for human confirmation before execution.</p>
        </article>
        <article className="summary-card summary-card-alert">
          <span>Quarantine alerts</span>
          <strong>{quarantinedAgents.length}</strong>
          <p>Repeated blocked behavior escalates into automatic isolation.</p>
        </article>
      </section>

      {error ? (
        <section className="banner banner-error">
          <strong>Dashboard needs attention.</strong>
          <span>{error}</span>
        </section>
      ) : null}

      {loading ? <section className="banner">Loading dashboard state...</section> : null}

      <main className="dashboard-grid">
        <section className="panel panel-form">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Connected Accounts</p>
              <h2>Vault-backed provider links</h2>
            </div>
          </div>
          <form className="stack" onSubmit={handleConnectionSubmit}>
            <label>
              Provider
              <select
                value={connectionProvider}
                onChange={(event) => {
                  const nextProvider = event.target.value as Provider;
                  setConnectionProvider(nextProvider);
                  setConnectionScopes(
                    nextProvider === "gmail"
                      ? "gmail.compose gmail.readonly"
                      : "repo issues:write pull_requests:write",
                  );
                }}
              >
                <option value="gmail">Gmail</option>
                <option value="github">GitHub</option>
              </select>
            </label>
            <label>
              External account id
              <input
                value={connectionExternalId}
                onChange={(event) => setConnectionExternalId(event.target.value)}
                placeholder="demo-account"
              />
            </label>
            <label>
              Scopes
              <input
                value={connectionScopes}
                onChange={(event) => setConnectionScopes(event.target.value)}
                placeholder="repo issues:write"
              />
            </label>
            <button className="primary-button" disabled={busyKey === "connection"} type="submit">
              {busyKey === "connection" ? "Saving..." : "Connect account"}
            </button>
          </form>
          <div className="card-list">
            {connections.map((connection) => (
              <article className="mini-card" key={connection.id}>
                <div className="row-between">
                  <strong>{connection.provider}</strong>
                  <span className={`status-pill status-${connection.status}`}>{connection.status}</span>
                </div>
                <p>{summarizeConnectionScopes(connection.scopes)}</p>
                <small>{connection.vault_reference}</small>
              </article>
            ))}
            {connections.length === 0 ? <p className="empty-state">No provider accounts connected yet.</p> : null}
          </div>
        </section>

        <section className="panel panel-form">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Agents</p>
              <h2>Create and scope agents</h2>
            </div>
          </div>
          <form className="stack" onSubmit={handleAgentSubmit}>
            <label>
              Agent name
              <input value={agentName} onChange={(event) => setAgentName(event.target.value)} placeholder="Assistant Agent" />
            </label>
            <label>
              Agent type
              <input value={agentType} onChange={(event) => setAgentType(event.target.value)} placeholder="assistant" />
            </label>
            <label>
              Description
              <textarea
                rows={3}
                value={agentDescription}
                onChange={(event) => setAgentDescription(event.target.value)}
                placeholder="Handles low-risk drafting tasks."
              />
            </label>
            <button className="primary-button" disabled={busyKey === "agent"} type="submit">
              {busyKey === "agent" ? "Creating..." : "Create agent"}
            </button>
          </form>
          <div className="card-list">
            {agents.map((agent) => {
              const selectedGrant = grantSelections[agent.id] ?? defaultCapabilityByProvider.gmail;
              const capability = capabilityCatalog.find((item) => item.name === selectedGrant) ?? capabilityCatalog[0];
              const constraintValue =
                grantConstraints[agent.id] ??
                (selectedGrant === "gmail.draft.create" ? "authorizedtoact.dev" : "chorus/secure-demo");
              return (
                <article className="agent-card" key={agent.id}>
                  <div className="row-between">
                    <div>
                      <h3>{agent.name}</h3>
                      <p>{agent.description || agent.agent_type}</p>
                    </div>
                    <span className={`status-pill status-${agent.status}`}>{agent.status}</span>
                  </div>
                  {agent.quarantine_reason ? <div className="alert-chip">{agent.quarantine_reason}</div> : null}
                  <div className="capability-list">
                    {agent.capabilities.map((grant) => (
                      <span className="capability-chip" key={grant.id}>
                        {grant.capability_name}
                      </span>
                    ))}
                    {agent.capabilities.length === 0 ? <p className="empty-state">No capabilities granted yet.</p> : null}
                  </div>
                  <div className="inline-form">
                    <select
                      value={selectedGrant}
                      onChange={(event) =>
                        setGrantSelections((current) => ({
                          ...current,
                          [agent.id]: event.target.value,
                        }))
                      }
                    >
                      {capabilityCatalog.map((item) => (
                        <option key={item.name} value={item.name}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                    <input
                      value={constraintValue}
                      onChange={(event) =>
                        setGrantConstraints((current) => ({
                          ...current,
                          [agent.id]: event.target.value,
                        }))
                      }
                      placeholder={capability.constraintHint}
                    />
                    <button
                      className="secondary-button"
                      disabled={busyKey === `grant-${agent.id}`}
                      onClick={() => void handleGrant(agent.id)}
                      type="button"
                    >
                      Grant
                    </button>
                  </div>
                </article>
              );
            })}
            {agents.length === 0 ? <p className="empty-state">Create your first agent to start shaping permissions.</p> : null}
          </div>
        </section>

        <section className="panel panel-wide">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Action Studio</p>
              <h2>Submit demo actions through the new pipeline</h2>
            </div>
          </div>
          <form className="action-form" onSubmit={handleActionSubmit}>
            <label>
              Agent
              <select value={actionAgentId} onChange={(event) => setActionAgentId(event.target.value)}>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Capability
              <select value={actionCapabilityName} onChange={(event) => setActionCapabilityName(event.target.value)}>
                {capabilityCatalog.map((capability) => (
                  <option key={capability.name} value={capability.name}>
                    {capability.label} ({capability.risk})
                  </option>
                ))}
              </select>
            </label>
            {actionCapabilityName === "gmail.draft.create" ? (
              <>
                <label>
                  Recipients
                  <input value={recipient} onChange={(event) => setRecipient(event.target.value)} />
                </label>
                <label>
                  Subject
                  <input value={subject} onChange={(event) => setSubject(event.target.value)} />
                </label>
              </>
            ) : (
              <>
                <label>
                  Repository
                  <input value={repository} onChange={(event) => setRepository(event.target.value)} />
                </label>
                {actionCapabilityName === "github.issue.create" ? (
                  <label>
                    Issue title
                    <input value={issueTitle} onChange={(event) => setIssueTitle(event.target.value)} />
                  </label>
                ) : (
                  <label>
                    Pull request number
                    <input value={prNumber} onChange={(event) => setPrNumber(event.target.value)} />
                  </label>
                )}
              </>
            )}
            <label className="full-width">
              Message
              <textarea rows={4} value={message} onChange={(event) => setMessage(event.target.value)} />
            </label>
            <button className="primary-button full-width" disabled={busyKey === "action"} type="submit">
              {busyKey === "action" ? "Submitting..." : "Submit action request"}
            </button>
          </form>
          <div className="action-grid">
            {actions.map((action) => {
              const agent = agents.find((candidate) => candidate.id === action.agent_id);
              return (
                <article className="timeline-card" key={action.id}>
                  <div className="row-between">
                    <strong>{agent?.name ?? action.agent_id}</strong>
                    <span className={`status-pill status-${action.status}`}>{action.status}</span>
                  </div>
                  <p>{action.capability_name}</p>
                  <div className="tag-row">
                    {action.enforcement_decision ? (
                      <span className="decision-badge">{action.enforcement_decision}</span>
                    ) : null}
                    {action.risk_level ? <span className="decision-badge">{action.risk_level} risk</span> : null}
                    {action.execution_status ? (
                      <span className="decision-badge">{action.execution_status}</span>
                    ) : null}
                  </div>
                  <small>{action.explanation || "Waiting for decision details."}</small>
                </article>
              );
            })}
            {actions.length === 0 ? <p className="empty-state">No action requests have been submitted yet.</p> : null}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Pending Approvals</p>
              <h2>Human checkpoints</h2>
            </div>
          </div>
          <div className="card-list">
            {pendingApprovals.map((approval) => (
              <article className="mini-card" key={approval.id}>
                <div className="row-between">
                  <strong>{approval.agent_name}</strong>
                  <span className="status-pill status-pending">{approval.status}</span>
                </div>
                <p>{approval.capability_name}</p>
                <small>{approval.explanation || "Approval required."}</small>
                <div className="button-row">
                  <button
                    className="primary-button"
                    disabled={busyKey === `approve-${approval.id}`}
                    onClick={() => void handleApproval(approval.id, "approve")}
                    type="button"
                  >
                    Approve
                  </button>
                  <button
                    className="secondary-button"
                    disabled={busyKey === `reject-${approval.id}`}
                    onClick={() => void handleApproval(approval.id, "reject")}
                    type="button"
                  >
                    Reject
                  </button>
                </div>
              </article>
            ))}
            {pendingApprovals.length === 0 ? <p className="empty-state">No pending approvals right now.</p> : null}
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Quarantine State</p>
              <h2>Escalation watchlist</h2>
            </div>
          </div>
          <div className="card-list">
            {quarantinedAgents.map((agent) => (
              <article className="mini-card mini-card-alert" key={agent.id}>
                <div className="row-between">
                  <strong>{agent.name}</strong>
                  <span className="status-pill status-quarantined">quarantined</span>
                </div>
                <p>{agent.quarantine_reason}</p>
              </article>
            ))}
            {quarantinedAgents.length === 0 ? (
              <p className="empty-state">No agents are quarantined. Blocks are contained so far.</p>
            ) : null}
          </div>
        </section>

        <section className="panel panel-wide">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Activity Timeline</p>
              <h2>Decision and audit trail</h2>
            </div>
          </div>
          <div className="timeline">
            {audit.map((event) => (
              <article className="timeline-entry" key={event.id}>
                <div className="row-between">
                  <strong>{event.event_type}</strong>
                  <span>{formatDate(event.occurred_at)}</span>
                </div>
                <p>{event.message}</p>
              </article>
            ))}
            {audit.length === 0 ? <p className="empty-state">Audit events will appear here as actions move through the pipeline.</p> : null}
          </div>
        </section>
      </main>
    </div>
  );
}
