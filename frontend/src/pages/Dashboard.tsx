import React from 'react';
import { TrendingUp, Bot, ShieldCheck, AlertOctagon, UserCheck, AlertTriangle, Clock } from 'lucide-react';
import { cn } from '../lib/utils';
import type { Agent, ActionRequest, ApprovalQueueItem, AuditEvent } from '../types';

interface DashboardProps {
  agents: Agent[];
  actions: ActionRequest[];
  approvals: ApprovalQueueItem[];
  auditEvents: AuditEvent[];
}

export function Dashboard({ agents, actions, approvals, auditEvents }: DashboardProps) {
  const activeAgents = agents.filter((a) => a.status === 'active').length;
  const quarantinedAgents = agents.filter((a) => a.status === 'quarantined').length;
  const pendingApprovals = approvals.filter((a) => a.status === 'pending').length;
  const completedActions = actions.filter((a) => a.status === 'completed').length;

  return (
    <div className="p-8 flex-1 flex flex-col gap-8">
      {/* Stats */}
      <section className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        <div className="lg:col-span-3 bg-surface-container-lowest p-8 rounded-xl border border-neutral-800/50 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8">
            <span className="text-[10px] font-headline uppercase tracking-[0.2em] text-neutral-500">Live Status</span>
          </div>
          <div className="flex flex-col">
            <h2 className="text-neutral-400 font-headline text-sm uppercase tracking-widest mb-2">Actions Completed</h2>
            <div className="flex items-baseline gap-4">
              <span className="text-7xl font-headline font-bold tracking-tighter text-white">{completedActions}</span>
              <span className="text-emerald-500 flex items-center gap-1 font-headline text-sm">
                <TrendingUp className="w-4 h-4" />
                All time
              </span>
            </div>
          </div>
          <div className="mt-8 h-24 w-full">
            <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 1000 100">
              <path className="wave-path" d="M0,50 C100,20 200,80 300,50 C400,20 500,80 600,50 C700,20 800,80 900,50 L1000,50" fill="none" opacity="0.4" stroke="white" strokeWidth="2" />
              <path className="wave-path" d="M0,60 C100,40 200,90 300,60 C400,40 500,90 600,60 C700,40 800,90 900,60 L1000,60" fill="none" opacity="0.1" stroke="white" strokeWidth="1" />
            </svg>
          </div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="flex-1 bg-surface-container-low p-6 rounded-xl border border-neutral-800/50 flex flex-col justify-between">
            <div className="text-[10px] font-headline uppercase tracking-widest text-neutral-500">Active Agents</div>
            <div className="text-3xl font-headline font-bold text-white">{activeAgents}</div>
            <div className="text-[10px] font-body text-neutral-600">Registered & running</div>
          </div>
          <div className="flex-1 bg-surface-container-low p-6 rounded-xl border border-neutral-800/50 flex flex-col justify-between">
            <div className="text-[10px] font-headline uppercase tracking-widest text-neutral-500">Pending Approvals</div>
            <div className={cn('text-3xl font-headline font-bold', pendingApprovals > 0 ? 'text-amber-400' : 'text-white')}>{pendingApprovals}</div>
            <div className="text-[10px] font-body text-neutral-600">Awaiting human decision</div>
          </div>
          <div className="flex-1 bg-surface-container-low p-6 rounded-xl border border-neutral-800/50 flex flex-col justify-between">
            <div className="text-[10px] font-headline uppercase tracking-widest text-neutral-500">Quarantined</div>
            <div className={cn('text-3xl font-headline font-bold', quarantinedAgents > 0 ? 'text-rose-500' : 'text-white')}>{quarantinedAgents}</div>
            <div className="text-[10px] font-body text-neutral-600">Agents restricted</div>
          </div>
        </div>
      </section>

      {/* Agents + Recent Activity */}
      <section className="grid grid-cols-1 xl:grid-cols-4 gap-8">
        {/* Recent Actions */}
        <div className="xl:col-span-3 bg-surface-container-lowest rounded-xl border border-neutral-800/50 flex flex-col">
          <div className="p-6 border-b border-neutral-800/50 flex justify-between items-center">
            <div>
              <h3 className="text-xl font-headline font-bold text-white tracking-tight">Recent Actions</h3>
              <p className="text-xs text-neutral-500 mt-1 uppercase tracking-widest">Latest agent action requests</p>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto no-scrollbar p-4 space-y-2 font-mono text-[11px]">
            {actions.length === 0 && (
              <div className="text-neutral-600 p-4">No actions yet.</div>
            )}
            {actions.slice(0, 8).map((action) => (
              <div key={action.id} className={cn(
                'flex flex-wrap gap-x-4 gap-y-1 py-2 border-b border-white/5 last:border-0',
                action.status === 'quarantined' || action.status === 'policy_blocked' ? 'text-rose-500' :
                action.status === 'pending_approval' ? 'text-amber-500' :
                action.status === 'completed' ? 'text-emerald-500 opacity-80' : 'text-neutral-400'
              )}>
                <span className="text-neutral-600 w-20">{new Date(action.requested_at).toLocaleTimeString()}</span>
                <span className="flex-1 min-w-[120px] truncate">{action.capability_name}</span>
                <span className="w-16">{action.provider.toUpperCase()}</span>
                <span className="w-24 uppercase">{action.status.replace('_', ' ')}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Agent Status */}
        <div className="xl:col-span-1 bg-surface-container-low rounded-xl border border-neutral-800/50 flex flex-col">
          <div className="p-6 border-b border-neutral-800/50">
            <h3 className="text-sm font-headline font-bold text-white uppercase tracking-widest">Agent Status</h3>
          </div>
          <div className="flex-1 overflow-y-auto no-scrollbar p-4 space-y-4">
            {agents.length === 0 && (
              <div className="text-neutral-600 text-xs p-2">No agents registered.</div>
            )}
            {agents.map((agent) => {
              const Icon = agent.status === 'quarantined' ? AlertOctagon : agent.status === 'active' ? UserCheck : AlertTriangle;
              const color = agent.status === 'quarantined' ? 'text-rose-500' : agent.status === 'active' ? 'text-emerald-500' : 'text-amber-500';
              return (
                <div key={agent.id} className="p-4 rounded-lg bg-white/5 border border-white/5 hover:border-white/20 transition-all cursor-pointer group">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[11px] font-headline text-white truncate">{agent.name}</span>
                    <Icon className={cn('w-3 h-3 flex-shrink-0', color)} />
                  </div>
                  <div className="text-[9px] text-neutral-500 uppercase">{agent.status}</div>
                  <div className="text-[9px] text-neutral-600 mt-1">{agent.capabilities.length} capabilities</div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Live Audit Stream */}
      <section className="mb-8">
        <div className="bg-surface-container-lowest border border-neutral-800/50 rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-6 py-3 border-b border-neutral-800/50 bg-neutral-900/30">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></div>
              <span className="text-[10px] font-headline font-bold uppercase tracking-[0.2em] text-white">Live Audit Stream</span>
            </div>
            <div className="flex gap-4 text-[9px] font-headline uppercase text-neutral-500">
              <span>WebSocket: /ws/dashboard</span>
            </div>
          </div>
          <div className="p-6 font-mono text-[11px] h-48 overflow-y-auto no-scrollbar space-y-1 bg-black">
            {auditEvents.length === 0 && (
              <div className="text-neutral-600">Waiting for events...</div>
            )}
            {auditEvents.slice(0, 10).map((event) => (
              <div key={event.id} className={cn(
                event.event_type.includes('quarantine') ? 'text-rose-500 font-bold' :
                event.event_type.includes('block') ? 'text-amber-500' :
                'text-emerald-500 opacity-80'
              )}>
                <span className="text-neutral-600">[{new Date(event.occurred_at).toLocaleTimeString()}]</span>{' '}
                {event.message}
              </div>
            ))}
            <div className="text-neutral-400 opacity-60 animate-pulse cursor-default">_</div>
          </div>
        </div>
      </section>
    </div>
  );
}
