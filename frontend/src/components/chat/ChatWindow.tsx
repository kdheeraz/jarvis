import { useEffect, useRef } from 'react';
import { Bot, Loader2 } from 'lucide-react';
import { useChatStore } from '../../store/chatStore';
import { MessageBubble } from './MessageBubble';

export function ChatWindow() {
  const { messages, statusMessage } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or status change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, statusMessage]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-20 h-20 mx-auto mb-6 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center">
            <Bot size={40} className="text-primary-600 dark:text-primary-400" />
          </div>
          <h2 className="text-2xl font-semibold mb-2">Hello! I'm Jarvis</h2>
          <p className="text-surface-500 dark:text-surface-400 max-w-md">
            Your AI assistant. Ask me anything, or use the microphone for voice chat.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto py-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Status indicator */}
        {statusMessage && (
          <div className="flex gap-3 py-3 px-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-600 text-white flex items-center justify-center">
              <Loader2 size={16} className="animate-spin" />
            </div>
            <div className="flex items-center">
              <span className="text-sm text-surface-500 dark:text-surface-400 italic">
                {statusMessage}
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
