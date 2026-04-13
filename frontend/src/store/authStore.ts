import { create } from 'zustand';
import { login as apiLogin, getCurrentUser } from '../api/auth';

interface AuthState {
  token: string | null;
  username: string | null;
  role: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('jarvis_token'),
  username: null,
  role: null,
  isAuthenticated: !!localStorage.getItem('jarvis_token'),
  isLoading: false,

  login: async (username, password) => {
    set({ isLoading: true });
    try {
      const token = await apiLogin(username, password);
      localStorage.setItem('jarvis_token', token);
      const user = await getCurrentUser();
      set({ token, username: user.username, role: user.role, isAuthenticated: true, isLoading: false });
    } catch {
      set({ isLoading: false });
      throw new Error('Invalid credentials');
    }
  },

  logout: () => {
    localStorage.removeItem('jarvis_token');
    set({ token: null, username: null, role: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    const token = localStorage.getItem('jarvis_token');
    if (!token) {
      set({ isAuthenticated: false });
      return;
    }
    try {
      const user = await getCurrentUser();
      set({ token, username: user.username, role: user.role, isAuthenticated: true });
    } catch {
      localStorage.removeItem('jarvis_token');
      set({ token: null, username: null, role: null, isAuthenticated: false });
    }
  },
}));
