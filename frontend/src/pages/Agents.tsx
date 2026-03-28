import React from 'react';
import { Bot, AlertOctagon, CheckCircle, AlertTriangle, ChevronRight } from 'lucide-react';
import { cn } from '../lib/utils';
import type { Agent } from '../types';

interface AgentsProps {
  agents: Agent[];
}

const riskColors: Record<string, string> = {
  low: 'text-emerald-500',
  medium: 'text-amber-500',
  high: 'text-rose-500',
  critical: 'text-rose-600',
};

export function Agents({ agents }: AgentsProps) {
  return (
    <div className="p-8 flex-1 flex flex-col gap-8">
      <div className="flex justify-between items-end mb-4">
        <div>
          <span className="text-[10px] font-headline uppercase tracking-[0.2em] text-neutral-500">Agent Registry</span>
          <h2 className="text-4xl font-headline font-bold text-white tracking-tight">Agents</h2>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          {agents.length === 0 && (
            <div className="text-neutral-600 font-body p-8 bg-surface-container-lowest rounded-xl border border-neutral-800/50">
              No agents registered yet.
            </div>
          )}
          {agents.map((agent) => {
            const StatusIcon = agent.status === 'quarantined' ? AlertOctagon : agent.status === 'active' ? CheckCircle : AlertTriangle;
            const statusColor = agent.status === 'quarantined' ? 'text-rose-500' : agent.status === 'active' ? 'text-emerald-500' : 'text-amber-500';
            return (
              <div key={agent.id} className="bg-surface-container-lowest p-6 rounded-xl border border-neutral-800/50 hover:border-white/20 transition-all cursor-pointer group">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-6">
                    <div className="w-12 h-12 rounded-lg bg-white/5 flex items-center justify-center">
                      <Bot className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                      <h3 className="text-lg font-headline font-bold text-white">{agent.name}</h3>
                      <p className="text-sm text-neutral-500 font-body">{agent.description ?? agent.agent_type}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <StatusIcon className={cn('w-4 h-4', statusColor)} />
                    <span className={cn('text-[10px] font-headline uppercase tracking-widest', statusColor)}>{agent.status}</span>
                    <ChevronRight className="w-5 h-5 text-neutral-700 group-hover:text-white transition-colors" />
                  </div>
                </div>

                {agent.quarantine_reason && (
                  <div className="mt-4 px-4 py-2 bg-rose-500/10 border border-rose-500/20 rounded text-xs text-rose-400 font-body">
                    Quarantine reason: {agent.quarantine_reason}
                  </div>
                )}

                {agent.capabilities.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {agent.capabilities.map((cap) => (
                      <span key={cap.id} className={cn('px-2 py-1 bg-white/5 border border-white/10 rounded text-[10px] font-mono', riskColors[cap.risk_level_default] ?? 'text-neutral-400')}>
                        {cap.capability_name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div className="space-y-6">
          <div className="bg-surface-container-low p-8 rounded-xl border border-neutral-800/50">
            <h3 className="text-sm font-headline font-bold text-white uppercase tracking-widest mb-6">Summary</h3>
            <div className="space-y-4">
              {[
                { label: 'Active', value: agents.filter((a) => a.status === 'active').length, color: 'text-emerald-500' },
                { label: 'Disabled', value: agents.filter((a) => a.status === 'disabled').length, color: 'text-neutral-400' },
                { label: 'Quarantined', value: agents.filter((a) => a.status === 'quarantined').length, color: 'text-rose-500' },
              ].map((stat) => (
                <div key={stat.label} className="flex justify-between items-center">
                  <span className="text-[10px] font-headline uppercase text-neutral-500">{stat.label}</span>
                  <span className={cn('text-xl font-headline font-bold', stat.color)}>{stat.value}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-surface-container-low p-8 rounded-xl border border-neutral-800/50">
            <h3 className="text-sm font-headline font-bold text-white uppercase tracking-widest mb-4">Capability Risk Levels</h3>
            <div className="space-y-2 text-[10px] font-headline uppercase">
              <div className="flex justify-between"><span className="text-neutral-500">Low</span><span className="text-emerald-500">Auto-allowed</span></div>
              <div className="flex justify-between"><span className="text-neutral-500">Medium</span><span className="text-amber-500">Requires approval</span></div>
              <div className="flex justify-between"><span className="text-neutral-500">High</span><span className="text-rose-500">Blocked / Quarantine</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
