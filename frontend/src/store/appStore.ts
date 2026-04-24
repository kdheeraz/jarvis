import { create } from 'zustand';
import { api } from '../api/client';

interface AppState {
  agentName: string;
  loaded: boolean;
  loadAppInfo: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  agentName: 'Jarvis',
  loaded: false,

  loadAppInfo: async () => {
    if (get().loaded) return;
    try {
      const { data } = await api.get('/api/health');
      if (data?.name) {
        set({ agentName: data.name, loaded: true });
      } else {
        set({ loaded: true });
      }
    } catch {
      set({ loaded: true });
    }
  },
}));
