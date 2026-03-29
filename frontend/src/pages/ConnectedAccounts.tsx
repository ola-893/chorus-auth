import React from 'react';
import { Link2, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { cn } from '../lib/utils';
import type { ConnectedAccount } from '../types';

interface ConnectedAccountsProps {
  accounts: ConnectedAccount[];
}

const providerLabels: Record<string, string> = {
  gmail: 'Gmail',
  github: 'GitHub',
};

export function ConnectedAccounts({ accounts }: ConnectedAccountsProps) {
  return (
    <div className="p-8 flex-1 flex flex-col gap-8">
      <div className="flex justify-between items-end mb-4">
        <div>
          <span className="text-[10px] font-headline uppercase tracking-[0.2em] text-neutral-500">Provider Connections</span>
          <h2 className="text-4xl font-headline font-bold text-white tracking-tight">Connected Accounts</h2>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {accounts.length === 0 && (
          <div className="col-span-2 text-neutral-600 font-body p-8 bg-surface-container-lowest rounded-xl border border-neutral-800/50">
            No accounts connected yet.
          </div>
        )}
        {accounts.map((account) => {
          const StatusIcon = account.status === 'connected' ? CheckCircle : account.status === 'error' ? XCircle : AlertCircle;
          const statusColor = account.status === 'connected' ? 'text-emerald-500' : account.status === 'error' ? 'text-rose-500' : 'text-amber-500';
          return (
            <div key={account.id} className="bg-surface-container-lowest p-6 rounded-xl border border-neutral-800/50 hover:border-white/20 transition-all">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-lg bg-white/5 flex items-center justify-center">
                    <Link2 className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-lg font-headline font-bold text-white">{providerLabels[account.provider] ?? account.provider}</h3>
                    <p className="text-xs text-neutral-500 font-mono">{account.external_account_id ?? 'mock-account'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusIcon className={cn('w-4 h-4', statusColor)} />
                  <span className={cn('text-[10px] font-headline uppercase tracking-widest', statusColor)}>{account.status}</span>
                </div>
              </div>
              <div className="mt-4">
                <div className="text-[10px] font-headline uppercase tracking-widest text-neutral-500 mb-2">Scopes</div>
                <div className="flex flex-wrap gap-2">
                  {account.scopes.map((scope) => (
                    <span key={scope} className="px-2 py-1 bg-white/5 border border-white/10 rounded text-[10px] font-mono text-neutral-400">{scope}</span>
                  ))}
                </div>
              </div>
              <div className="mt-4 flex justify-between text-[10px] font-headline uppercase text-neutral-600">
                <span>Mode: {account.connection_mode}</span>
                <span>Vault: {account.vault_reference}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
