import { clsx } from 'clsx';
import { Bot, User, Wrench } from 'lucide-react';
import type { Message } from '../../types';
import { MarkdownRenderer } from './MarkdownRenderer';

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';
  const isTool = message.role === 'tool';
  const isSystem = message.role === 'system';

  return (
    <div
      className={clsx('flex gap-3 py-4 px-4', {
        'justify-end': isUser,
      })}
    >
      {!isUser && (
        <div
          className={clsx('flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center', {
            'bg-primary-600 text-white': message.role === 'assistant',
            'bg-amber-500 text-white': isTool,
            'bg-surface-400 text-white': isSystem,
          })}
        >
          {message.role === 'assistant' && <Bot size={16} />}
          {isTool && <Wrench size={16} />}
        </div>
      )}

      <div
        className={clsx('max-w-[75%] rounded-2xl px-4 py-3', {
          'bg-gradient-to-br from-primary-500 to-primary-700 text-white shadow-lg shadow-primary-900/20': isUser,
          'glass': message.role === 'assistant',
          'glass-subtle border border-amber-300/50 dark:border-amber-500/30 text-sm': isTool,
          'glass-subtle border border-red-300/60 dark:border-red-500/30 text-red-700 dark:text-red-300 text-sm': isSystem,
        })}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <MarkdownRenderer content={message.content || (message.isStreaming ? '...' : '')} />
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-surface-700 text-white flex items-center justify-center">
          <User size={16} />
        </div>
      )}
    </div>
  );
}
