import React, { useState } from 'react';
import { ShieldCheck, ChevronRight, CheckCircle, XCircle } from 'lucide-react';
import { cn } from '../lib/utils';
import type { ApprovalQueueItem } from '../types';

interface ApprovalsProps {
  approvals: ApprovalQueueItem[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
}

export function Approvals({ approvals, onApprove, onReject }: ApprovalsProps) {
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const pending = approvals.filter((a) => a.status === 'pending');
  const resolved = approvals.filter((a) => a.status !== 'pending');

  async function handle(id: string, action: 'approve' | 'reject') {
    setLoadingId(id);
    try {
      action === 'approve' ? onApprove(id) : onReject(id);
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <div className="p-8 flex-1 flex flex-col gap-8">
      <div className="flex justify-between items-end mb-4">
        <div>
          <span className="text-[10px] font-headline uppercase tracking-[0.2em] text-neutral-500">Human-in-the-Loop</span>
          <h2 className="text-4xl font-headline font-bold text-white tracking-tight">Approvals</h2>
        </div>
        {pending.length > 0 && (
          <div className="px-4 py-2 bg-amber-500/10 border border-amber-500/20 rounded-full">
            <span className="text-amber-400 font-headline text-xs uppercase tracking-widest">{pending.length} pending</span>
          </div>
        )}
      </div>

      {/* Pending */}
      <div className="space-y-4">
        <h3 className="text-xs font-headline uppercase tracking-widest text-neutral-500">Pending Decision</h3>
        {pending.length === 0 && (
          <div className="text-neutral-600 font-body p-8 bg-surface-container-lowest rounded-xl border border-neutral-800/50">
            No pending approvals.
          </div>
        )}
        {pending.map((item) => (
          <div key={item.id} className="bg-surface-container-lowest p-6 rounded-xl border border-amber-500/20 hover:border-amber-500/40 transition-all">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
              <div className="flex items-center gap-6">
                <div className="w-12 h-12 rounded-lg bg-amber-500/10 flex items-center justify-center flex-shrink-0">
                  <ShieldCheck className="w-6 h-6 text-amber-500" />
                </div>
                <div>
                  <h3 className="text-lg font-headline font-bold text-white">{item.agent_name}</h3>
                  <p className="text-sm text-neutral-500 font-mono">{item.capability_name} · {item.provider.toUpperCase()}</p>
                  {item.explanation && (
                    <p className="text-xs text-neutral-400 mt-2 max-w-lg">{item.explanation}</p>
                  )}
                  <p className="text-[10px] text-neutral-600 mt-1">Requested: {new Date(item.requested_at).toLocaleString()}</p>
                </div>
              </div>
              <div className="flex gap-3 flex-shrink-0">
                <button
                  onClick={() => handle(item.id, 'approve')}
                  disabled={loadingId === item.id}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-headline text-xs uppercase tracking-widest rounded-full hover:bg-emerald-500/20 transition-all disabled:opacity-50"
                >
                  <CheckCircle className="w-4 h-4" />
                  Approve
                </button>
                <button
                  onClick={() => handle(item.id, 'reject')}
                  disabled={loadingId === item.id}
                  className="flex items-center gap-2 px-4 py-2 bg-rose-500/10 border border-rose-500/30 text-rose-400 font-headline text-xs uppercase tracking-widest rounded-full hover:bg-rose-500/20 transition-all disabled:opacity-50"
                >
                  <XCircle className="w-4 h-4" />
                  Reject
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Resolved */}
      {resolved.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-xs font-headline uppercase tracking-widest text-neutral-500">Resolved</h3>
          {resolved.map((item) => (
            <div key={item.id} className="bg-surface-container-lowest p-6 rounded-xl border border-neutral-800/50 opacity-60">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center">
                    {item.status === 'approved' ? <CheckCircle className="w-5 h-5 text-emerald-500" /> : <XCircle className="w-5 h-5 text-rose-500" />}
                  </div>
                  <div>
                    <span className="text-sm font-headline text-white">{item.agent_name}</span>
                    <span className="text-xs text-neutral-500 ml-3 font-mono">{item.capability_name}</span>
                  </div>
                </div>
                <span className={cn('text-[10px] font-headline uppercase tracking-widest', item.status === 'approved' ? 'text-emerald-500' : 'text-rose-500')}>
                  {item.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
