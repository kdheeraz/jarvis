import { useState, useEffect } from 'react';
import { MessageSquare, Plus, Trash2, Moon, Sun, Settings, LogIn, LogOut } from 'lucide-react';
import { clsx } from 'clsx';
import { useChatStore } from '../../store/chatStore';
import { useAuthStore } from '../../store/authStore';
import { useNavigate } from 'react-router-dom';

interface Props {
  children: React.ReactNode;
  embed?: boolean;
}

export function AppLayout({ children, embed }: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('jarvis_theme') === 'dark' ||
        (!localStorage.getItem('jarvis_theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
    }
    return false;
  });
  const { conversations, activeConversationId, setActiveConversation, startNewChat, loadConversations, deleteConversation } = useChatStore();
  const { isAuthenticated, role, logout } = useAuthStore();
  const isAdmin = isAuthenticated && role === 'admin';
  const navigate = useNavigate();

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('jarvis_theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  if (embed) {
    return <div className="h-screen flex flex-col">{children}</div>;
  }

  return (
    <div className="h-screen flex">
      {/* Sidebar */}
      <div
        className={clsx(
          'glass-strong m-3 rounded-2xl text-surface-900 dark:text-surface-100 flex flex-col transition-all duration-300',
          sidebarOpen ? 'w-72' : 'w-0 m-0 overflow-hidden',
        )}
      >
        <div className="p-4">
          <button
            onClick={startNewChat}
            className="w-full flex items-center gap-2 px-4 py-3 rounded-xl text-white bg-gradient-to-br from-primary-500 to-primary-700 shadow-lg shadow-primary-900/25 hover:from-primary-400 hover:to-primary-600 transition-all"
          >
            <Plus size={18} />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={clsx(
                'flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer group transition-colors mb-1',
                activeConversationId === conv.id
                  ? 'bg-white/60 dark:bg-white/10 shadow-sm'
                  : 'hover:bg-white/40 dark:hover:bg-white/5',
              )}
              onClick={() => setActiveConversation(conv.id)}
            >
              <MessageSquare size={16} className="flex-shrink-0 opacity-60" />
              <span className="flex-1 text-sm truncate">{conv.title || 'New Chat'}</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteConversation(conv.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-white/40 dark:hover:bg-white/10 rounded transition-all"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>

        <div className="min-h-[83px] border-t border-white/30 dark:border-white/10 flex items-center gap-2 px-4">
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-lg hover:bg-white/40 dark:hover:bg-white/10 transition-colors"
          >
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          {isAdmin && (
            <button
              onClick={() => navigate('/admin')}
              className="p-2 rounded-lg hover:bg-white/40 dark:hover:bg-white/10 transition-colors"
              title="Admin Panel"
            >
              <Settings size={18} />
            </button>
          )}
          {isAuthenticated ? (
            <button
              onClick={logout}
              className="p-2 rounded-lg hover:bg-white/40 dark:hover:bg-white/10 transition-colors"
              title="Logout"
            >
              <LogOut size={18} />
            </button>
          ) : (
            <button
              onClick={() => navigate('/login')}
              className="p-2 rounded-lg hover:bg-white/40 dark:hover:bg-white/10 transition-colors"
              title="Login"
            >
              <LogIn size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="h-14 mt-3 mr-3 glass rounded-2xl flex items-center px-4 gap-3">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 rounded-lg hover:bg-white/40 dark:hover:bg-white/10 transition-colors"
          >
            <MessageSquare size={20} />
          </button>
          <h1 className="font-semibold">Jarvis</h1>
        </div>

        {children}
      </div>
    </div>
  );
}
