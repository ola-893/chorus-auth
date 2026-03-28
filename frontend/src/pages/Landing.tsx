import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import { ShieldCheck, GitBranch, Lock, ClipboardList } from 'lucide-react';

export function Landing() {
  return (
    <div className="min-h-screen bg-background text-on-background">
      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-6 md:px-[120px] py-[24px] bg-black/40 backdrop-blur-xl">
        <div className="text-[20px] font-bold tracking-tighter text-white uppercase italic font-headline">CHORUS</div>
        <div className="hidden md:flex gap-8 items-center">
          <a className="text-white opacity-100 font-semibold font-headline text-[14px] tracking-tight uppercase px-4 py-2 hover:bg-white/5 rounded-full transition-all duration-300" href="#problem">The Problem</a>
          <a className="text-white/60 hover:text-white transition-opacity duration-300 font-headline text-[14px] tracking-tight uppercase px-4 py-2 hover:bg-white/5 rounded-full" href="#solution">The Solution</a>
          <a className="text-white/60 hover:text-white transition-opacity duration-300 font-headline text-[14px] tracking-tight uppercase px-4 py-2 hover:bg-white/5 rounded-full" href="#capabilities">Capabilities</a>
          <a className="text-white/60 hover:text-white transition-opacity duration-300 font-headline text-[14px] tracking-tight uppercase px-4 py-2 hover:bg-white/5 rounded-full" href="#flow">Decision Flow</a>
        </div>
        <Link to="/dashboard" className="bg-primary text-on-primary font-headline font-bold text-[14px] tracking-tight uppercase px-8 py-3 rounded-full hover:scale-95 transition-transform duration-200">
          Open Console
        </Link>
      </nav>

      <main>
        {/* Hero Section */}
        <section className="relative h-screen w-full flex items-center justify-center overflow-hidden">
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover opacity-60 mix-blend-screen">
            <source src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260217_030345_246c0224-10a4-422c-b324-070b7c0eceda.mp4" type="video/mp4" />
          </video>

          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <img
              alt=""
              className="w-[140%] max-w-none md:w-[100%] lg:w-[80%] h-auto object-contain transform -translate-y-12 rotate-12 scale-125 brightness-[0.7] contrast-[1.2] opacity-[0.25] mix-blend-screen"
              src="https://lh3.googleusercontent.com/aida/ADBb0uhlCuI9lWP3rocTT5OBrKqpt75R6W7bZR8IVjQmvFOTJT-OfAplgrRnqdkuYiqHHdp_6fiUlg7fDTUxnOMiT-G1CIpDBc4x7xOklAsZ21Gl6uXzW7g-hrccQQWWJlT5fD0wPM1C8MCBRA88j95LzVh3wAVWkIa8gRwSLRvbEKynkimOgUfl1UrPixdB7jmOA96oDaJw_Tml4bDAxf0AKpOSAVwuk3iAWHwuBgigKAflbLu4jxGmhxJoD5yZgPcJA2HYg_pR00bFlQ"
              referrerPolicy="no-referrer"
            />
          </div>

          <div className="absolute inset-0 pointer-events-none bg-gradient-to-b from-transparent via-background/20 to-background"></div>

          <div className="relative z-10 container mx-auto px-6 text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 mb-8 glass-panel px-4 py-2 rounded-full border border-neutral-800/30"
            >
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
              <span className="font-headline text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">Control Plane: Active</span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="font-headline text-5xl md:text-[5rem] lg:text-[7rem] leading-[0.9] font-black tracking-tighter text-white mb-8"
            >
              THE PERMISSION LAYER<br />FOR AI AGENTS.
            </motion.h1>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              className="max-w-2xl mx-auto font-body text-lg md:text-xl text-on-surface-variant font-light mb-12"
            >
              Connect accounts, grant scoped capabilities, enforce policy, and audit every agent action — before it executes.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="flex flex-col sm:flex-row gap-6 justify-center"
            >
              <Link to="/dashboard" className="bg-primary text-on-primary font-headline font-bold text-sm tracking-widest uppercase px-10 py-5 rounded-full light-streak shadow-[0_0_30px_rgba(255,255,255,0.1)] hover:shadow-[0_0_50px_rgba(255,255,255,0.2)] transition-all">
                Open Console
              </Link>
              <button className="glass-panel border border-neutral-800/50 text-white font-headline font-bold text-sm tracking-widest uppercase px-10 py-5 rounded-full hover:bg-white/10 transition-all">
                View Docs
              </button>
            </motion.div>
          </div>
        </section>

        {/* The Problem */}
        <section id="problem" className="py-32 container mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-24 items-start">
            <div className="sticky top-32 bg-background">
              <label className="font-headline text-xs uppercase tracking-[0.3em] text-primary/60 mb-6 block">01 // THE PROBLEM</label>
              <h2 className="font-headline text-4xl md:text-6xl font-black text-white leading-tight mb-8">
                Agents Acting Without Boundaries.
              </h2>
              <p className="text-on-surface-variant text-xl leading-relaxed max-w-lg">
                AI agents connected to real services — Gmail, GitHub, APIs — can take actions with real consequences. Without a control layer, there's no way to know what they did, why, or whether they should have.
              </p>
            </div>
            <div className="space-y-12">
              <div className="obsidian-card p-12 rounded-lg border border-neutral-800/10 group">
                <Lock className="w-10 h-10 text-primary mb-6" />
                <h3 className="font-headline text-2xl font-bold text-white mb-4">No Least-Privilege</h3>
                <p className="text-on-surface-variant font-light leading-relaxed">Agents with raw token access can do anything the token allows — far beyond what the task requires.</p>
              </div>
              <div className="obsidian-card p-12 rounded-lg border border-neutral-800/10 group">
                <GitBranch className="w-10 h-10 text-primary mb-6" />
                <h3 className="font-headline text-2xl font-bold text-white mb-4">No Approval Workflow</h3>
                <p className="text-on-surface-variant font-light leading-relaxed">Sensitive actions like merging PRs or sending emails execute immediately, with no human checkpoint.</p>
              </div>
              <div className="obsidian-card p-12 rounded-lg border border-neutral-800/10 group">
                <ClipboardList className="w-10 h-10 text-primary mb-6" />
                <h3 className="font-headline text-2xl font-bold text-white mb-4">No Audit Trail</h3>
                <p className="text-on-surface-variant font-light leading-relaxed">When something goes wrong, there's no record of what the agent requested, what was decided, or what ran.</p>
              </div>
            </div>
          </div>
        </section>

        {/* The Solution */}
        <section id="solution" className="py-40 bg-surface-container-lowest relative overflow-hidden">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/20 to-transparent"></div>
          <div className="container mx-auto px-6 text-center relative z-10">
            <label className="font-headline text-xs uppercase tracking-[0.3em] text-primary/60 mb-10 block">02 // THE SOLUTION</label>
            <h2 className="font-headline text-5xl md:text-8xl font-black text-white mb-12 tracking-tighter">Controlled Execution.</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-1 px-4 lg:px-24">
              <div className="p-12 border-b md:border-b-0 md:border-r border-white/5">
                <div className="font-headline text-5xl font-black text-white/20 mb-4 italic">01</div>
                <h4 className="font-headline text-xl font-bold text-white mb-4 uppercase">Grant</h4>
                <p className="text-on-surface-variant text-sm uppercase tracking-wider leading-loose">Assign scoped capabilities to each agent. No raw tokens. No over-permission.</p>
              </div>
              <div className="p-12 border-b md:border-b-0 md:border-r border-white/5">
                <div className="font-headline text-5xl font-black text-white/20 mb-4 italic">02</div>
                <h4 className="font-headline text-xl font-bold text-white mb-4 uppercase">Enforce</h4>
                <p className="text-on-surface-variant text-sm uppercase tracking-wider leading-loose">Every action passes through policy, risk scoring, and enforcement before it runs.</p>
              </div>
              <div className="p-12">
                <div className="font-headline text-5xl font-black text-white/20 mb-4 italic">03</div>
                <h4 className="font-headline text-xl font-bold text-white mb-4 uppercase">Audit</h4>
                <p className="text-on-surface-variant text-sm uppercase tracking-wider leading-loose">Every decision — allow, approve, block, quarantine — is written to an immutable log.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Capabilities */}
        <section id="capabilities" className="py-32 container mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-end mb-24 gap-8">
            <div className="max-w-xl">
              <label className="font-headline text-xs uppercase tracking-[0.3em] text-primary/60 mb-6 block">03 // CAPABILITIES</label>
              <h2 className="font-headline text-4xl md:text-6xl font-black text-white leading-none">Scoped Permissions Per Agent.</h2>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { capability: 'gmail.draft.create', provider: 'Gmail', desc: 'Agent can create email drafts. Constrained to approved domains only.', risk: 'Low', icon: ShieldCheck },
              { capability: 'github.issue.create', provider: 'GitHub', desc: 'Agent can open issues. Requires human approval before execution.', risk: 'Medium', icon: GitBranch },
              { capability: 'github.pull_request.merge', provider: 'GitHub', desc: 'Agent can merge pull requests. High risk — blocked or quarantined on violation.', risk: 'High', icon: Lock },
            ].map((item, i) => (
              <div key={i} className="obsidian-card p-10 rounded-lg flex flex-col justify-between h-[320px]">
                <div>
                  <div className="w-12 h-12 glass-panel flex items-center justify-center rounded-lg mb-8 border border-neutral-800/30">
                    <item.icon className="w-6 h-6 text-primary" />
                  </div>
                  <div className="font-mono text-xs text-neutral-500 mb-2">{item.capability}</div>
                  <h3 className="font-headline text-xl font-bold text-white mb-4">{item.provider}</h3>
                  <p className="text-on-surface-variant text-sm leading-relaxed">{item.desc}</p>
                </div>
                <div className={`text-[10px] font-headline uppercase tracking-widest ${item.risk === 'Low' ? 'text-emerald-500' : item.risk === 'Medium' ? 'text-amber-500' : 'text-rose-500'}`}>
                  Risk: {item.risk}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Decision Flow */}
        <section id="flow" className="py-32 bg-[#0e0e0e] relative">
          <div className="container mx-auto px-6">
            <div className="flex flex-col items-center mb-24 text-center">
              <label className="font-headline text-xs uppercase tracking-[0.3em] text-primary/60 mb-6 block">04 // DECISION FLOW</label>
              <h2 className="font-headline text-4xl md:text-6xl font-black text-white mb-8">Every Action. Evaluated.</h2>
            </div>
            <div className="max-w-5xl mx-auto">
              <div className="flex flex-col md:flex-row items-center justify-between gap-12 relative">
                <div className="hidden md:block absolute top-1/2 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-neutral-800 to-transparent -translate-y-1/2 -z-10"></div>
                {[
                  { label: 'POLICY CHECK', desc: 'Capability grant + scope' },
                  { label: 'RISK SCORE', desc: 'Low / Medium / High / Critical', active: true },
                  { label: 'ENFORCEMENT', desc: 'Allow / Approve / Block' },
                  { label: 'AUDIT LOG', desc: 'Immutable trail' },
                ].map((node, i) => (
                  <div key={i} className="flex flex-col items-center gap-4 text-center">
                    <div className={`w-24 h-24 rounded-full glass-panel border flex items-center justify-center relative ${node.active ? 'border-primary/40' : 'border-primary/20'}`}>
                      {node.active && <div className="absolute inset-0 rounded-full border border-primary animate-ping opacity-20"></div>}
                      <span className={`font-headline font-black text-lg ${node.active ? 'text-primary' : 'text-neutral-400'}`}>{String(i + 1).padStart(2, '0')}</span>
                    </div>
                    <span className={`font-headline text-[10px] uppercase tracking-widest ${node.active ? 'text-primary' : 'text-neutral-500'}`}>{node.label}</span>
                    <span className="text-[10px] text-neutral-600 max-w-[100px]">{node.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-48 relative overflow-hidden bg-background">
          <div className="container mx-auto px-6 text-center relative z-10">
            <h2 className="font-headline text-5xl md:text-8xl font-black text-white mb-12 tracking-tighter">
              READY TO CONTROL<br />YOUR AGENTS?
            </h2>
            <div className="flex flex-col items-center gap-8">
              <p className="text-on-surface-variant max-w-md mx-auto text-lg">Register agents. Grant capabilities. Enforce policy. Audit everything.</p>
              <Link to="/dashboard" className="bg-primary text-on-primary font-headline font-bold text-sm tracking-[0.2em] uppercase px-16 py-6 rounded-full light-streak shadow-[0_20px_50px_rgba(255,255,255,0.1)] hover:scale-105 transition-all">
                Open Console
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-[#0e0e0e] border-t border-white/5 py-16">
        <div className="max-w-7xl mx-auto px-12 flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex flex-col gap-4">
            <div className="text-xl font-black text-white tracking-tighter font-headline">CHORUS</div>
            <div className="font-headline text-[11px] uppercase tracking-[0.2em] font-light text-white/40">
              © 2026 CHORUS. THE PERMISSION LAYER FOR AI AGENTS.
            </div>
          </div>
          <div className="flex gap-8">
            {[
              { label: 'The Problem', href: '#problem' },
              { label: 'The Solution', href: '#solution' },
              { label: 'Capabilities', href: '#capabilities' },
              { label: 'Decision Flow', href: '#flow' },
            ].map((link) => (
              <a key={link.label} className="font-headline text-[11px] uppercase tracking-[0.2em] font-light text-white/40 hover:text-white transition-colors" href={link.href}>{link.label}</a>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
