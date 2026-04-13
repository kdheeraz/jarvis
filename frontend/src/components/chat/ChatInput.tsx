import { useState, useRef, useEffect } from 'react';
import { Send, Mic, Square } from 'lucide-react';
import { clsx } from 'clsx';

interface Props {
  onSend: (message: string) => void;
  onVoiceMode?: () => void;
  isStreaming: boolean;
  voiceSupported: boolean;
  disabled?: boolean;
}

export function ChatInput({ onSend, onVoiceMode, isStreaming, voiceSupported, disabled }: Props) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (!input.trim() || isStreaming || disabled) return;
    onSend(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  return (
    <div className="p-4">
      <div className="max-w-3xl mx-auto glass rounded-2xl p-2 flex items-end gap-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            disabled={disabled}
            className="w-full resize-none bg-transparent border-0 outline-none px-3 py-2 min-h-[44px] max-h-[200px] placeholder:text-surface-500 dark:placeholder:text-surface-400"
          />
        </div>

        {/* Voice Mode button */}
        {voiceSupported && (
          <button
            onClick={onVoiceMode}
            className="p-3 rounded-full bg-white/50 dark:bg-white/10 hover:bg-white/70 dark:hover:bg-white/20 transition-all duration-200"
            title="Voice Mode"
          >
            <Mic size={20} />
          </button>
        )}

        {/* Send button */}
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isStreaming || disabled}
          className={clsx(
            'p-3 rounded-full transition-all duration-200',
            input.trim() && !isStreaming
              ? 'bg-gradient-to-br from-primary-500 to-primary-700 text-white shadow-lg shadow-primary-900/25 hover:from-primary-400 hover:to-primary-600'
              : 'bg-white/40 dark:bg-white/10 text-surface-400',
          )}
        >
          {isStreaming ? <Square size={20} /> : <Send size={20} />}
        </button>
      </div>
    </div>
  );
}
