import React from 'react';
import { Bell, Settings, UserCircle } from 'lucide-react';

interface TopBarProps {
  pendingApprovals?: number;
}

export function TopBar({ pendingApprovals = 0 }: TopBarProps) {
  return (
    <header className="fixed top-0 right-0 left-0 md:left-64 z-30 flex items-center justify-between px-4 md:px-8 h-16 border-b border-neutral-800/50 bg-neutral-950/40 backdrop-blur-xl">
      <div className="flex items-center gap-4 md:gap-8 font-headline uppercase text-[10px] tracking-[0.1em] ml-12 md:ml-0">
        <div className="flex items-center gap-2 text-white">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="hidden sm:inline">Control Plane: Active</span>
          <span className="sm:hidden">Active</span>
        </div>
        <div className="text-neutral-400 hidden sm:block">Mode: Mock</div>
        {pendingApprovals > 0 && (
          <div className="text-amber-400">Approvals: {pendingApprovals}</div>
        )}
      </div>

      <div className="flex items-center gap-4 md:gap-6">
        <div className="flex items-center gap-3 md:gap-4 border-r border-neutral-800/50 pr-4 md:pr-6">
          <Bell className="w-5 h-5 text-neutral-400 hover:text-white cursor-pointer transition-opacity opacity-80 hover:opacity-100" />
          <Settings className="w-5 h-5 text-neutral-400 hover:text-white cursor-pointer transition-opacity opacity-80 hover:opacity-100 hidden sm:block" />
        </div>
        <div className="flex items-center gap-2 md:gap-3 cursor-pointer opacity-80 hover:opacity-100 transition-opacity">
          <span className="text-[10px] font-headline uppercase tracking-widest text-white hidden sm:block">Admin</span>
          <UserCircle className="w-6 h-6 text-white" />
        </div>
      </div>
    </header>
  );
}
