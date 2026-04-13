import { api } from './client';
import type { ToolInfo, UserInfo, DocumentInfo, Conversation } from '../types';

// Config
export async function getConfig() {
  const { data } = await api.get('/api/admin/config');
  return data;
}

export async function updateConfig(updates: Record<string, unknown>) {
  const { data } = await api.put('/api/admin/config', updates);
  return data;
}

export async function reloadConfig() {
  const { data } = await api.post('/api/admin/config/reload');
  return data;
}

// Tools
export async function getTools(): Promise<ToolInfo[]> {
  const { data } = await api.get('/api/admin/tools');
  return data;
}

export async function updateTool(name: string, enabled: boolean) {
  const { data } = await api.put(`/api/admin/tools/${name}`, { enabled });
  return data;
}

// Users
export async function getUsers(): Promise<UserInfo[]> {
  const { data } = await api.get('/api/admin/users');
  return data;
}

export async function createUser(username: string, password: string, role = 'admin') {
  const { data } = await api.post('/api/admin/users', { username, password, role });
  return data;
}

export async function deleteUser(id: string) {
  await api.delete(`/api/admin/users/${id}`);
}

// RAG
export async function getCollections() {
  const { data } = await api.get('/api/admin/rag/collections');
  return data;
}

export async function createCollection(name: string) {
  const { data } = await api.post('/api/admin/rag/collections', { name });
  return data;
}

export async function deleteCollection(name: string) {
  await api.delete(`/api/admin/rag/collections/${name}`);
}

export async function ingestFiles(collectionName: string, files: File[]) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  const { data } = await api.post(`/api/admin/rag/ingest?collection_name=${collectionName}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function getDocuments(collectionName?: string): Promise<DocumentInfo[]> {
  const params = collectionName ? { collection_name: collectionName } : {};
  const { data } = await api.get('/api/admin/rag/documents', { params });
  return data;
}

// Conversations (admin)
export async function getAdminConversations(limit = 100): Promise<Conversation[]> {
  const { data } = await api.get('/api/admin/conversations', { params: { limit } });
  return data;
}

export async function deleteAdminConversation(id: string) {
  await api.delete(`/api/admin/conversations/${id}`);
}
