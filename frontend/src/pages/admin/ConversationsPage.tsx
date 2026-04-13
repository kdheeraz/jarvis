import { useEffect, useState } from 'react';
import { MessageSquare, Trash2 } from 'lucide-react';
import { getAdminConversations, deleteAdminConversation } from '../../api/admin';
import type { Conversation } from '../../types';

export function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);

  const refresh = () => getAdminConversations().then(setConversations).catch(() => {});

  useEffect(() => { refresh(); }, []);

  const handleDelete = async (id: string) => {
    await deleteAdminConversation(id);
    refresh();
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Conversations</h1>

      <div className="card">
        <div className="divide-y divide-surface-200 dark:divide-surface-700">
          {conversations.map((conv) => (
            <div key={conv.id} className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <MessageSquare size={18} className="text-surface-400" />
                <div>
                  <p className="font-medium">{conv.title || 'Untitled'}</p>
                  <p className="text-xs text-surface-500">
                    {new Date(conv.createdAt).toLocaleString()} | ID: {conv.id.slice(0, 8)}
                  </p>
                </div>
              </div>
              <button onClick={() => handleDelete(conv.id)} className="p-2 hover:bg-red-100 dark:hover:bg-red-900 rounded-lg transition-colors">
                <Trash2 size={16} className="text-red-500" />
              </button>
            </div>
          ))}

          {conversations.length === 0 && (
            <p className="text-surface-500 text-center py-8">No conversations yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
