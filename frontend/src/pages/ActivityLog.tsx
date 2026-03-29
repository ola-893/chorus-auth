import React from 'react';
import { Search, Filter } from 'lucide-react';
import { cn } from '../lib/utils';
import type { AuditEvent } from '../types';

interface ActivityLogProps {
  events: AuditEvent[];
}

function eventColor(eventType: string): string {
  if (eventType.includes('quarantine')) return 'text-rose-500 font-bold';
  if (eventType.includes('block')) return 'text-rose-400';
  if (eventType.includes('approval')) return 'text-amber-500';
  if (eventType.includes('allow') || eventType.includes('complete')) return 'text-emerald-500 opacity-80';
  return 'text-neutral-400 opacity-60';
}

export function ActivityLog({ events }: ActivityLogProps) {
  const [search, setSearch] = React.useState('');

  const filtered = events.filter(
    (e) =>
      !search ||
      e.message.toLowerCase().includes(search.toLowerCase()) ||
      e.event_type.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="p-8 flex-1 flex flex-col gap-6 h-full overflow-hidden">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <span className="text-[10px] font-headline uppercase tracking-[0.2em] text-neutral-500">Immutable History</span>
          <h2 className="text-4xl font-headline font-bold text-white tracking-tight">Activity Log</h2>
        </div>
        <div className="flex gap-4 w-full sm:w-auto">
          <div className="relative flex-1 sm:flex-none">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" />
            <input
              type="text"
              placeholder="Search events..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 pr-4 py-2 bg-white/5 border border-neutral-800 rounded-full text-xs font-headline focus:outline-none focus:border-white/20 w-full sm:w-64 text-white"
            />
          </div>
          <button className="p-2 bg-white/5 border border-neutral-800 rounded-full hover:bg-white/10 transition-all">
            <Filter className="w-4 h-4 text-neutral-400" />
          </button>
        </div>
      </div>

      <div className="flex-1 bg-black border border-neutral-800/50 rounded-xl overflow-hidden flex flex-col">
        <div className="grid grid-cols-12 gap-4 px-6 py-3 border-b border-neutral-800/50 bg-neutral-900/30 text-[10px] font-headline uppercase tracking-widest text-neutral-500">
          <div className="col-span-3 sm:col-span-2">Timestamp</div>
          <div className="col-span-4 sm:col-span-3">Event Type</div>
          <div className="col-span-5 sm:col-span-7">Message</div>
        </div>
        <div className="flex-1 overflow-y-auto no-scrollbar p-6 font-mono text-[11px] space-y-2">
          {filtered.length === 0 && (
            <div className="text-neutral-600">No events found.</div>
          )}
          {filtered.map((event) => (
            <div key={event.id} className={cn('grid grid-cols-12 gap-4 py-1 border-b border-white/5 last:border-0', eventColor(event.event_type))}>
              <div className="col-span-3 sm:col-span-2 text-neutral-600">{new Date(event.occurred_at).toLocaleTimeString()}</div>
              <div className="col-span-4 sm:col-span-3 truncate">{event.event_type}</div>
              <div className="col-span-5 sm:col-span-7 truncate">{event.message}</div>
            </div>
          ))}
          <div className="text-neutral-400 opacity-60 animate-pulse cursor-default">_</div>
        </div>
      </div>

      {/* Live indicator */}
      <div className="bg-surface-container-low border border-neutral-800/50 rounded-full px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></div>
          <span className="text-[10px] font-headline font-bold uppercase tracking-widest text-white">Live</span>
          <span className="text-[10px] font-mono text-neutral-500">{filtered.length} events</span>
        </div>
        <span className="text-[10px] font-headline uppercase text-neutral-500">WebSocket: /ws/dashboard</span>
      </div>
    </div>
  );
}
