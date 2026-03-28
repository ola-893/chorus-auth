import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { Landing } from './pages/Landing';
import { Dashboard } from './pages/Dashboard';
import { ConnectedAccounts } from './pages/ConnectedAccounts';
import { Agents } from './pages/Agents';
import { Approvals } from './pages/Approvals';
import { ActivityLog } from './pages/ActivityLog';
import { Quarantine } from './pages/Quarantine';
import { RegisterAgent } from './pages/RegisterAgent';
import { api, connectDashboardSocket } from './api';
import type {
  Agent,
  ActionRequest,
  ApprovalQueueItem,
  AuditEvent,
  ConnectedAccount,
  DashboardEvent,
} from './types';

function AppLayout({ children, pendingApprovals }: { children: React.ReactNode; pendingApprovals: number }) {
  const location = useLocation();
  const isLanding = location.pathname === '/';

  if (isLanding) return <>{children}</>;

  return (
    <div className="flex min-h-screen bg-background text-on-background">
      <Sidebar />
      <div className="flex-1 flex flex-col md:ml-64">
        <TopBar pendingApprovals={pendingApprovals} />
        <main className="mt-16 flex-1 flex flex-col overflow-y-auto no-scrollbar">
          {children}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [actions, setActions] = useState<ActionRequest[]>([]);
  const [approvals, setApprovals] = useState<ApprovalQueueItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);

  useEffect(() => {
    Promise.all([
      api.getAgents(),
      api.getActions(),
      api.getApprovals(),
      api.getAudit(),
      api.getConnections(),
    ]).then(([a, ac, ap, au, co]) => {
      setAgents(a);
      setActions(ac);
      setApprovals(ap);
      setAuditEvents(au);
      setAccounts(co);
    }).catch(console.error);

    const socket = connectDashboardSocket((event: DashboardEvent) => {
      if (event.type === 'action_updated') {
        api.getActions().then(setActions).catch(console.error);
      }
      if (event.type === 'approval_updated') {
        api.getApprovals().then(setApprovals).catch(console.error);
      }
      if (event.type === 'agent_updated') {
        api.getAgents().then(setAgents).catch(console.error);
      }
      if (event.type === 'audit_event') {
        api.getAudit().then(setAuditEvents).catch(console.error);
      }
    });

    return () => socket.close();
  }, []);

  async function handleApprove(id: string) {
    await api.approve(id);
    const updated = await api.getApprovals();
    setApprovals(updated);
    const updatedActions = await api.getActions();
    setActions(updatedActions);
  }

  async function handleReject(id: string) {
    await api.reject(id);
    const updated = await api.getApprovals();
    setApprovals(updated);
  }

  const pendingApprovals = approvals.filter((a) => a.status === 'pending').length;

  return (
    <Router>
      <AppLayout pendingApprovals={pendingApprovals}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/dashboard" element={<Dashboard agents={agents} actions={actions} approvals={approvals} auditEvents={auditEvents} />} />
          <Route path="/accounts" element={<ConnectedAccounts accounts={accounts} />} />
          <Route path="/agents" element={<Agents agents={agents} />} />
          <Route path="/approvals" element={<Approvals approvals={approvals} onApprove={handleApprove} onReject={handleReject} />} />
          <Route path="/activity" element={<ActivityLog events={auditEvents} />} />
          <Route path="/quarantine" element={<Quarantine agents={agents} />} />
          <Route path="/agents/new" element={<RegisterAgent />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppLayout>
    </Router>
  );
}
