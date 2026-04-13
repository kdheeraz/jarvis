import { useEffect, useState } from 'react';
import { Bot, MessageSquare, Database, Wrench } from 'lucide-react';
import { api } from '../../api/client';

interface HealthData {
  status: string;
  name: string;
  version: string;
  llm_provider: string;
  rag_enabled: boolean;
  voice_enabled: boolean;
}

export function DashboardPage() {
  const [health, setHealth] = useState<HealthData | null>(null);

  useEffect(() => {
    api.get('/api/health').then(({ data }) => setHealth(data)).catch(() => {});
  }, []);

  const stats = [
    { label: 'LLM Provider', value: health?.llm_provider || '...', icon: Bot, color: 'bg-primary-100 dark:bg-primary-900 text-primary-600' },
    { label: 'RAG', value: health?.rag_enabled ? 'Enabled' : 'Disabled', icon: Database, color: 'bg-green-100 dark:bg-green-900 text-green-600' },
    { label: 'Voice', value: health?.voice_enabled ? 'Enabled' : 'Disabled', icon: MessageSquare, color: 'bg-purple-100 dark:bg-purple-900 text-purple-600' },
    { label: 'Version', value: health?.version || '...', icon: Wrench, color: 'bg-amber-100 dark:bg-amber-900 text-amber-600' },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card p-5">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
                <Icon size={20} />
              </div>
              <div>
                <p className="text-sm text-surface-500">{label}</p>
                <p className="font-semibold capitalize">{value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="card p-6">
        <h2 className="text-lg font-semibold mb-4">System Status</h2>
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${health?.status === 'ok' ? 'bg-green-500' : 'bg-red-500'}`} />
          <span>{health?.status === 'ok' ? 'All systems operational' : 'Connecting...'}</span>
        </div>
      </div>
    </div>
  );
}
