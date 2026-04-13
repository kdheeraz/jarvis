import { api } from './client';

export async function login(username: string, password: string): Promise<string> {
  const { data } = await api.post('/api/auth/login', { username, password });
  return data.access_token;
}

export async function getCurrentUser(): Promise<{ username: string; role: string }> {
  const { data } = await api.get('/api/auth/me');
  return data;
}
