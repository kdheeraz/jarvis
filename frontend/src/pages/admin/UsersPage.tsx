import { useEffect, useState } from 'react';
import { UserPlus, Trash2, Users } from 'lucide-react';
import { getUsers, createUser, deleteUser } from '../../api/admin';
import type { UserInfo } from '../../types';

export function UsersPage() {
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const refresh = () => getUsers().then(setUsers).catch(() => {});

  useEffect(() => { refresh(); }, []);

  const handleCreate = async () => {
    if (!username || !password) return;
    setError('');
    try {
      await createUser(username, password);
      setUsername('');
      setPassword('');
      refresh();
    } catch {
      setError('Failed to create user. Username may already exist.');
    }
  };

  const handleDelete = async (id: string) => {
    await deleteUser(id);
    refresh();
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Users</h1>

      {/* Create user */}
      <div className="card p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Add Admin User</h2>
        {error && <div className="mb-3 text-red-600 text-sm">{error}</div>}
        <div className="flex gap-3">
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" className="input-field flex-1" />
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" className="input-field flex-1" />
          <button onClick={handleCreate} disabled={!username || !password} className="btn-primary flex items-center gap-2">
            <UserPlus size={16} />
            Add
          </button>
        </div>
      </div>

      {/* User list */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold mb-4">Admin Users</h2>
        <div className="space-y-2">
          {users.map((user) => (
            <div key={user.id} className="flex items-center justify-between p-3 bg-white/40 dark:bg-white/5 border border-white/40 dark:border-white/10 rounded-xl">
              <div className="flex items-center gap-3">
                <Users size={18} className="text-surface-400" />
                <div>
                  <p className="font-medium">{user.username}</p>
                  <p className="text-xs text-surface-500">
                    {user.role} | Created {new Date(user.createdAt).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <button onClick={() => handleDelete(user.id)} className="p-2 hover:bg-red-100 dark:hover:bg-red-900 rounded-lg transition-colors">
                <Trash2 size={16} className="text-red-500" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
