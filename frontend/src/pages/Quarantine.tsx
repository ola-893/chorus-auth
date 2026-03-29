import React from 'react';
import { AlertOctagon, ChevronRight } from 'lucide-react';
import type { Agent } from '../types';

interface QuarantineProps {
  agents: Agent[];
}

export function Quarantine({ agents }: QuarantineProps) {
  const quarantined = agents.filter((a) => a.status === 'quarantined');

  return (
    <div className="p-8 flex-1 flex flex-col gap-8">
      <div className="flex justify-between items-end mb-4">
        <div>
          <span className="text-[10px] font-headline uppercase tracking-[0.2em] text-neutral-500">Enforcement</span>
          <h2 className="text-4xl font-headline font-bold text-white tracking-tight">Quarantine</h2>
        </div>
        {quarantined.length > 0 && (
          <div className="px-4 py-2 bg-rose-500/10 border border-rose-500/20 rounded-full">
            <span className="text-rose-400 font-headline text-xs uppercase tracking-widest">{quarantined.length} quarantined</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          {quarantined.length === 0 && (
            <div className="text-neutral-600 font-body p-8 bg-surface-container-lowest rounded-xl border border-neutral-800/50">
              No agents currently quarantined.
            </div>
          )}
          {quarantined.map((agent) => (
            <div key={agent.id} className="bg-surface-container-lowest p-6 rounded-xl border border-rose-500/20 hover:border-rose-500/40 transition-all cursor-pointer group">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-6">
                  <div className="w-12 h-12 rounded-lg bg-rose-500/10 flex items-center justify-center">
                    <AlertOctagon className="w-6 h-6 text-rose-500" />
                  </div>
                  <div>
                    <h3 className="text-lg font-headline font-bold text-white">{agent.name}</h3>
                    <p className="text-sm text-neutral-500 font-body">{agent.agent_type}</p>
                    {agent.quarantine_reason && (
                      <p className="text-xs text-rose-400 mt-1">{agent.quarantine_reason}</p>
                    )}
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-neutral-700 group-hover:text-white transition-colors" />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {agent.capabilities.map((cap) => (
                  <span key={cap.id} className="px-2 py-1 bg-white/5 border border-white/10 rounded text-[10px] font-mono text-neutral-500">
                    {cap.capability_name}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-6">
          <div className="bg-rose-500/5 p-8 rounded-xl border border-rose-500/20">
            <h3 className="text-sm font-headline font-bold text-rose-500 uppercase tracking-widest mb-4">What is Quarantine?</h3>
            <p className="text-xs text-neutral-400 leading-relaxed">
              An agent is quarantined when it repeatedly attempts actions that violate policy. All further action requests from a quarantined agent are automatically blocked until the quarantine is lifted by an admin.
            </p>
          </div>

          <div className="bg-surface-container-low p-8 rounded-xl border border-neutral-800/50">
            <h3 className="text-sm font-headline font-bold text-white uppercase tracking-widest mb-4">Enforcement Decisions</h3>
            <div className="space-y-3 text-[10px] font-headline uppercase">
              <div className="flex justify-between"><span className="text-neutral-500">Allow</span><span className="text-emerald-500">Execute</span></div>
              <div className="flex justify-between"><span className="text-neutral-500">Require Approval</span><span className="text-amber-500">Pause</span></div>
              <div className="flex justify-between"><span className="text-neutral-500">Block</span><span className="text-rose-400">Deny</span></div>
              <div className="flex justify-between"><span className="text-neutral-500">Quarantine</span><span className="text-rose-600">Restrict Agent</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
