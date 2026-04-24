import { create } from 'zustand';
import { api } from '../api/client';
import { applyThemeVars } from '../lib/color';

interface AppState {
  agentName: string;
  themeColor: string;
  loaded: boolean;
  loadAppInfo: () => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  agentName: 'Jarvis',
  themeColor: '#3b82f6',
  loaded: false,

  loadAppInfo: async () => {
    if (get().loaded) return;
    try {
      const { data } = await api.get('/api/health');
      const themeColor = data?.theme ?? get().themeColor;
      applyThemeVars(themeColor);
      set({
        agentName: data?.name ?? get().agentName,
        themeColor,
        loaded: true,
      });
    } catch {
      set({ loaded: true });
    }
  },
}));
