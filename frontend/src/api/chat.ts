import { api } from './client';
import type { Conversation, ConversationDetail } from '../types';

export async function sendMessage(message: string, conversationId?: string) {
  const { data } = await api.post('/api/chat', { message, conversation_id: conversationId });
  return data;
}

export async function getConversations(): Promise<Conversation[]> {
  const { data } = await api.get('/api/conversations');
  return data;
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  const { data } = await api.get(`/api/conversations/${id}`);
  return data;
}

export async function deleteConversation(id: string): Promise<void> {
  await api.delete(`/api/conversations/${id}`);
}
