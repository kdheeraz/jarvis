import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Settings, Wrench, Database, Users, MessageSquare, LayoutDashboard, ArrowLeft } from 'lucide-react';
import { clsx } from 'clsx';

const navItems = [
  { path: '/admin', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { path: '/admin/config', icon: Settings, label: 'Configuration', end: false },
  { path: '/admin/tools', icon: Wrench, label: 'Tools', end: false },
  { path: '/admin/rag', icon: Database, label: 'RAG / Documents', end: false },
  { path: '/admin/users', icon: Users, label: 'Users', end: false },
  { path: '/admin/conversations', icon: MessageSquare, label: 'Conversations', end: false },
];

export function AdminLayout() {
  const navigate = useNavigate();

  return (
    <div className="h-screen flex">
      {/* Sidebar */}
      <div className="w-64 m-3 rounded-2xl glass-strong flex flex-col">
        <div className="p-4 border-b border-white/30 dark:border-white/10">
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/')}
              className="p-1.5 rounded-lg hover:bg-white/40 dark:hover:bg-white/10 transition-colors"
            >
              <ArrowLeft size={18} />
            </button>
            <h1 className="font-bold text-lg">Admin Panel</h1>
          </div>
        </div>

        <nav className="flex-1 p-3">
          {navItems.map(({ path, icon: Icon, label, end }) => (
            <NavLink
              key={path}
              to={path}
              end={end}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 transition-colors text-sm',
                  isActive
                    ? 'bg-white/60 dark:bg-white/10 text-primary-700 dark:text-primary-300 font-medium shadow-sm'
                    : 'hover:bg-white/40 dark:hover:bg-white/5 text-surface-600 dark:text-surface-300',
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto p-6">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
