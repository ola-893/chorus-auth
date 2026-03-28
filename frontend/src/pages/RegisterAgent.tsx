import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Brain } from 'lucide-react';
import { api } from '../api';

export function RegisterAgent() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', agent_type: '', description: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.createAgent({
        name: form.name,
        agent_type: form.agent_type,
        description: form.description || undefined,
      });
      navigate('/agents');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to register agent');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-2xl mx-auto w-full">
      <div className="mb-12">
        <span className="font-headline text-xs uppercase tracking-[0.2em] text-neutral-500 mb-4 block">Agent Registry</span>
        <h2 className="font-headline text-5xl font-bold tracking-tighter text-white mb-4">Register New Agent</h2>
        <p className="text-on-surface-variant text-lg">Add an agent to the control plane. Capabilities can be granted after registration.</p>
      </div>

      <form onSubmit={handleSubmit} className="glass-panel p-10 rounded-lg relative overflow-hidden space-y-8">
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />

        <div className="flex flex-col gap-2">
          <label className="font-headline text-[10px] uppercase tracking-widest text-on-surface-variant">Agent Name *</label>
          <input
            required
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            className="bg-surface-container-low border-b border-outline-variant text-white p-4 focus:outline-none focus:border-primary transition-all font-mono tracking-wider"
            placeholder="e.g. Assistant Agent"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className="font-headline text-[10px] uppercase tracking-widest text-on-surface-variant">Agent Type *</label>
          <input
            required
            value={form.agent_type}
            onChange={(e) => setForm((f) => ({ ...f, agent_type: e.target.value }))}
            className="bg-surface-container-low border-b border-outline-variant text-white p-4 focus:outline-none focus:border-primary transition-all font-mono tracking-wider"
            placeholder="e.g. assistant"
          />
        </div>

        <div className="flex flex-col gap-2">
          <label className="font-headline text-[10px] uppercase tracking-widest text-on-surface-variant">Description</label>
          <input
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            className="bg-surface-container-low border-b border-outline-variant text-white p-4 focus:outline-none focus:border-primary transition-all font-mono tracking-wider"
            placeholder="Optional description"
          />
        </div>

        {error && (
          <div className="px-4 py-3 bg-rose-500/10 border border-rose-500/20 rounded text-xs text-rose-400">{error}</div>
        )}

        <div className="flex gap-4 pt-4">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 py-4 bg-primary text-on-primary rounded-full font-headline font-bold text-sm tracking-widest uppercase hover:bg-neutral-200 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Brain className="w-4 h-4" />
            {loading ? 'Registering...' : 'Register Agent'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/agents')}
            className="px-8 py-4 border border-outline-variant text-on-surface-variant rounded-full font-headline font-bold text-xs uppercase hover:text-white hover:border-white transition-all"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
