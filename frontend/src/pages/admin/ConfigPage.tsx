import { useEffect, useState } from 'react';
import { Save, RefreshCw } from 'lucide-react';
import { getConfig, updateConfig, reloadConfig } from '../../api/admin';

export function ConfigPage() {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [editing, setEditing] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    getConfig().then(setConfig).catch(() => {});
  }, []);

  const handleSave = async () => {
    if (!editing) return;
    setSaving(true);
    setMessage('');
    try {
      const updates = JSON.parse(editing);
      await updateConfig(updates);
      setMessage('Configuration saved and reloaded');
      const fresh = await getConfig();
      setConfig(fresh);
    } catch (err) {
      setMessage(`Error: ${err instanceof Error ? err.message : 'Failed to save'}`);
    }
    setSaving(false);
  };

  const handleReload = async () => {
    try {
      await reloadConfig();
      const fresh = await getConfig();
      setConfig(fresh);
      setMessage('Configuration reloaded');
    } catch {
      setMessage('Failed to reload configuration');
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Configuration</h1>
        <button onClick={handleReload} className="btn-secondary flex items-center gap-2">
          <RefreshCw size={16} />
          Reload
        </button>
      </div>

      {message && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm ${message.startsWith('Error') ? 'bg-red-50 dark:bg-red-950 text-red-600' : 'bg-green-50 dark:bg-green-950 text-green-600'}`}>
          {message}
        </div>
      )}

      <div className="card p-6 mb-6">
        <h2 className="text-lg font-semibold mb-3">Current Configuration</h2>
        <pre className="bg-white/40 dark:bg-black/30 border border-white/40 dark:border-white/10 p-4 rounded-xl overflow-auto text-sm max-h-96">
          {config ? JSON.stringify(config, null, 2) : 'Loading...'}
        </pre>
      </div>

      <div className="card p-6">
        <h2 className="text-lg font-semibold mb-3">Update Configuration</h2>
        <p className="text-sm text-surface-500 mb-3">
          Paste a JSON object with the config keys you want to update (partial update supported).
        </p>
        <textarea
          value={editing}
          onChange={(e) => setEditing(e.target.value)}
          className="input-field font-mono text-sm min-h-[200px] mb-4"
          placeholder='{"llm": {"provider": "openai"}}'
        />
        <button onClick={handleSave} disabled={saving || !editing} className="btn-primary flex items-center gap-2">
          <Save size={16} />
          {saving ? 'Saving...' : 'Save & Apply'}
        </button>
      </div>
    </div>
  );
}
