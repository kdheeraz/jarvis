import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { ChatWindow } from '../components/chat/ChatWindow';
import { ChatInput } from '../components/chat/ChatInput';
import { VoiceModeOverlay } from '../components/chat/VoiceModeOverlay';
import { useWebSocket } from '../hooks/useWebSocket';
import { useVoiceMode } from '../hooks/useVoiceMode';
import { useChatStore } from '../store/chatStore';

export function ChatPage() {
  const [searchParams] = useSearchParams();
  const embed = searchParams.get('embed') === 'true';
  const { isStreaming, activeConversationId, setActiveConversation, loadConversations } = useChatStore();
  const { sendMessage } = useWebSocket();
  const voiceMode = useVoiceMode({
    conversationId: activeConversationId,
    onConversationCreated: (id) => {
      setActiveConversation(id);
      loadConversations();
    },
  });

  // Rebind voice to the newly selected conversation when the user switches
  // chats in the sidebar while voice mode is active.
  const lastBoundRef = useRef<string | null>(null);
  const wasActiveRef = useRef(false);
  useEffect(() => {
    if (!voiceMode.isActive) {
      // Voice just stopped — messages were written directly to the DB by
      // the backend handler, so refetch the active conversation to pull
      // them into the UI, and refresh the sidebar list.
      if (wasActiveRef.current) {
        wasActiveRef.current = false;
        if (activeConversationId) {
          setActiveConversation(activeConversationId);
        }
        loadConversations();
      }
      lastBoundRef.current = null;
      return;
    }
    wasActiveRef.current = true;
    if (activeConversationId && activeConversationId !== lastBoundRef.current) {
      lastBoundRef.current = activeConversationId;
      voiceMode.rebind(activeConversationId);
    }
  }, [voiceMode.isActive, activeConversationId, voiceMode, setActiveConversation, loadConversations]);

  return (
    <AppLayout embed={embed}>
      <ChatWindow />
      <ChatInput
        onSend={sendMessage}
        onVoiceMode={voiceMode.start}
        isStreaming={isStreaming}
        voiceSupported={voiceMode.isSupported}
      />
      <VoiceModeOverlay
        isActive={voiceMode.isActive}
        state={voiceMode.state}
        micStream={voiceMode.micStream}
        onStop={voiceMode.stop}
      />
    </AppLayout>
  );
}
