import { useEffect, useState } from 'react';
import { Wrench } from 'lucide-react';
import { getTools, updateTool } from '../../api/admin';
import type { ToolInfo } from '../../types';

export function ToolsPage() {
  const [tools, setTools] = useState<ToolInfo[]>([]);

  useEffect(() => {
    getTools().then(setTools).catch(() => {});
  }, []);

  const handleToggle = async (name: string, enabled: boolean) => {
    await updateTool(name, enabled);
    setTools((prev) => prev.map((t) => (t.name === name ? { ...t, enabled } : t)));
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Tools</h1>

      <div className="space-y-3">
        {tools.map((tool) => (
          <div key={tool.name} className="card p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900 flex items-center justify-center">
                <Wrench size={18} className="text-amber-600" />
              </div>
              <div>
                <h3 className="font-medium">{tool.name}</h3>
                <p className="text-sm text-surface-500">{tool.description}</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={tool.enabled}
                onChange={(e) => handleToggle(tool.name, e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-surface-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary-500 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600" />
            </label>
          </div>
        ))}

        {tools.length === 0 && (
          <p className="text-surface-500 text-center py-8">No tools discovered. Make sure the backend is running.</p>
        )}
      </div>
    </div>
  );
}
