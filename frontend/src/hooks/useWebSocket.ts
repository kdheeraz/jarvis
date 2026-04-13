import { useCallback, useEffect, useRef } from 'react';
import { ChatWebSocket } from '../api/websocket';
import { useChatStore } from '../store/chatStore';
import type { WSEvent } from '../types';

export function useWebSocket() {
  const wsRef = useRef<ChatWebSocket | null>(null);
  const {
    activeConversationId,
    setActiveConversation,
    addMessage,
    updateLastMessage,
    markLastMessageDone,
    dropLastIfEmptyAssistant,
    setStreaming,
    setStatus,
    setConnected,
    loadConversations,
  } = useChatStore();

  const connect = useCallback(
    (conversationId: string) => {
      wsRef.current?.disconnect();

      const ws = new ChatWebSocket(
        conversationId,
        (event: WSEvent) => {
          switch (event.type) {
            case 'conversation_created':
              if (event.conversationId) {
                setActiveConversation(event.conversationId);
              }
              break;
            case 'status':
              setStatus(event.message || null);
              break;
            case 'chunk':
              setStatus(null);
              updateLastMessage(event.content || '');
              break;
            case 'tool_call':
              // If the current assistant bubble is still empty (tool call came
              // before any text chunk), drop it so we don't render a blank one.
              dropLastIfEmptyAssistant();
              markLastMessageDone();
              addMessage({
                id: `tool-call-${Date.now()}`,
                role: 'tool',
                content: `Using ${event.name}...`,
                toolName: event.name,
              });
              // Add new assistant placeholder for the response after tool
              addMessage({ id: `assistant-${Date.now()}`, role: 'assistant', content: '', isStreaming: true });
              break;
            case 'tool_result':
              // Update tool message with result summary
              break;
            case 'done':
              markLastMessageDone();
              setStreaming(false);
              setStatus(null);
              loadConversations();
              break;
            case 'error':
              setStreaming(false);
              setStatus(null);
              addMessage({
                id: `error-${Date.now()}`,
                role: 'system',
                content: `Error: ${event.message}`,
              });
              break;
          }
        },
        () => setConnected(true),
        () => setConnected(false),
      );

      ws.connect();
      wsRef.current = ws;
    },
    [setActiveConversation, addMessage, updateLastMessage, markLastMessageDone, dropLastIfEmptyAssistant, setStreaming, setStatus, setConnected, loadConversations],
  );

  const sendMessage = useCallback(
    (content: string) => {
      const convId = activeConversationId || 'new';

      if (!wsRef.current) {
        connect(convId);
      }

      // Add user message to UI immediately
      addMessage({ id: `user-${Date.now()}`, role: 'user', content });

      // Add placeholder for assistant response
      addMessage({ id: `assistant-${Date.now()}`, role: 'assistant', content: '', isStreaming: true });
      setStreaming(true);

      // Small delay to ensure WS is connected
      setTimeout(() => {
        wsRef.current?.send('message', content);
      }, 100);
    },
    [activeConversationId, connect, addMessage, setStreaming],
  );

  const disconnect = useCallback(() => {
    wsRef.current?.disconnect();
    wsRef.current = null;
  }, []);

  // Connect when conversation changes
  useEffect(() => {
    if (activeConversationId) {
      connect(activeConversationId);
    }
    return () => disconnect();
  }, [activeConversationId, connect, disconnect]);

  return { sendMessage, connect, disconnect };
}
