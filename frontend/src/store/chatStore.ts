import { create } from 'zustand';
import type { Conversation, Message } from '../types';
import { getConversations, getConversation, deleteConversation as apiDeleteConv } from '../api/chat';

interface ChatState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  isConnected: boolean;
  statusMessage: string | null;

  setConversations: (convs: Conversation[]) => void;
  setActiveConversation: (id: string | null) => Promise<void>;
  setMessages: (msgs: Message[]) => void;
  addMessage: (msg: Message) => void;
  updateLastMessage: (content: string) => void;
  markLastMessageDone: () => void;
  dropLastIfEmptyAssistant: () => void;
  setStreaming: (streaming: boolean) => void;
  setStatus: (msg: string | null) => void;
  setConnected: (connected: boolean) => void;
  loadConversations: () => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  startNewChat: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  messages: [],
  isStreaming: false,
  isConnected: false,
  statusMessage: null,

  setConversations: (conversations) => set({ conversations }),
  setActiveConversation: async (id) => {
    set({ activeConversationId: id, messages: [] });
    if (id) {
      try {
        const detail = await getConversation(id);
        // Only set messages if this conversation is still active
        if (get().activeConversationId === id) {
          set({ messages: detail.messages || [] });
        }
      } catch {
        // Conversation may not have messages yet
      }
    }
  },
  setMessages: (messages) => set({ messages }),

  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),

  updateLastMessage: (content) =>
    set((state) => {
      const msgs = [...state.messages];
      if (msgs.length > 0) {
        const last = msgs[msgs.length - 1];
        msgs[msgs.length - 1] = { ...last, content: last.content + content };
      }
      return { messages: msgs };
    }),

  markLastMessageDone: () =>
    set((state) => {
      const msgs = [...state.messages];
      if (msgs.length > 0) {
        const last = msgs[msgs.length - 1];
        msgs[msgs.length - 1] = { ...last, isStreaming: false };
      }
      return { messages: msgs };
    }),

  dropLastIfEmptyAssistant: () =>
    set((state) => {
      const msgs = state.messages;
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant' && !last.content) {
        return { messages: msgs.slice(0, -1) };
      }
      return {};
    }),

  setStreaming: (isStreaming) => set({ isStreaming, statusMessage: isStreaming ? null : null }),
  setStatus: (statusMessage) => set({ statusMessage }),
  setConnected: (isConnected) => set({ isConnected }),

  loadConversations: async () => {
    try {
      const convs = await getConversations();
      set({ conversations: convs });
    } catch {
      // Ignore errors — conversations may not be persisted yet
    }
  },

  deleteConversation: async (id) => {
    await apiDeleteConv(id);
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      activeConversationId: state.activeConversationId === id ? null : state.activeConversationId,
      messages: state.activeConversationId === id ? [] : state.messages,
    }));
  },

  startNewChat: () => set({ activeConversationId: null, messages: [] }),
}));
