import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Link2, Bot, ShieldCheck, Clock, AlertOctagon, Plus, Menu, X } from 'lucide-react';
import { cn } from '../lib/utils';

const navItems = [
  { name: 'Dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { name: 'Connected Accounts', icon: Link2, path: '/accounts' },
  { name: 'Agents', icon: Bot, path: '/agents' },
  { name: 'Approvals', icon: ShieldCheck, path: '/approvals' },
  { name: 'Activity Log', icon: Clock, path: '/activity' },
  { name: 'Quarantine', icon: AlertOctagon, path: '/quarantine' },
];

export function Sidebar() {
  const [open, setOpen] = useState(false);

  const navContent = (
    <>
      <div className="flex items-center justify-between p-8">
        <div>
          <div className="text-xl font-bold tracking-tighter text-white mb-1">CHORUS</div>
          <div className="text-[10px] uppercase tracking-widest text-neutral-500 opacity-80">Auth Control Plane</div>
        </div>
        <button className="md:hidden text-neutral-400 hover:text-white" onClick={() => setOpen(false)}>
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex-1 px-4 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            onClick={() => setOpen(false)}
            className={({ isActive }) => cn(
              'flex items-center gap-4 px-4 py-3 rounded-lg transition-all duration-300',
              isActive
                ? 'text-white font-bold border-r-2 border-white bg-white/5'
                : 'text-neutral-500 hover:text-neutral-300 hover:bg-white/5'
            )}
          >
            <item.icon className="w-5 h-5" />
            <span>{item.name}</span>
          </NavLink>
        ))}
      </div>

      <div className="p-6">
        <NavLink
          to="/agents/new"
          onClick={() => setOpen(false)}
          className="w-full py-3 bg-white text-black font-bold rounded-full hover:bg-neutral-200 transition-colors flex items-center justify-center gap-2 group"
        >
          Register Agent
          <Plus className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </NavLink>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        className="md:hidden fixed top-4 left-4 z-50 p-2 bg-neutral-900 border border-neutral-800 rounded-lg text-white"
        onClick={() => setOpen(true)}
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Mobile overlay */}
      {open && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Mobile drawer */}
      <nav className={cn(
        'fixed left-0 top-0 h-full z-50 flex flex-col w-64 border-r border-neutral-800/50 bg-neutral-950 font-headline tracking-tight text-sm shadow-[20px_0px_40px_rgba(0,0,0,0.5)] transition-transform duration-300 md:hidden',
        open ? 'translate-x-0' : '-translate-x-full'
      )}>
        {navContent}
      </nav>

      {/* Desktop sidebar */}
      <nav className="hidden md:flex fixed left-0 top-0 h-full z-40 flex-col w-64 border-r border-neutral-800/50 bg-neutral-950/40 backdrop-blur-xl font-headline tracking-tight text-sm shadow-[20px_0px_40px_rgba(0,0,0,0.5)]">
        {navContent}
      </nav>
    </>
  );
}
