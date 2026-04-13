export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  toolName?: string;
  createdAt?: string;
  isStreaming?: boolean;
}

export interface Conversation {
  id: string;
  title: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ToolInfo {
  name: string;
  description: string;
  enabled: boolean;
}

export interface DocumentInfo {
  id: string;
  collectionName: string;
  filename: string;
  fileType: string;
  fileSize: number | null;
  chunkCount: number | null;
  status: string;
  errorMessage: string | null;
  createdAt: string;
  completedAt: string | null;
}

export interface UserInfo {
  id: string;
  username: string;
  role: string;
  createdAt: string;
}

export interface WSEvent {
  type: 'chunk' | 'tool_call' | 'tool_result' | 'done' | 'error' | 'pong' | 'conversation_created' | 'status';
  content?: string;
  name?: string;
  args?: Record<string, unknown>;
  messageId?: string;
  fullContent?: string;
  conversationId?: string;
  message?: string;
}
