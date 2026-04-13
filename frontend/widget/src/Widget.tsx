import { useState } from 'react';

interface WidgetProps {
  serverUrl: string;
  position: string;
  theme: string;
}

export function Widget({ serverUrl, position }: WidgetProps) {
  const [isOpen, setIsOpen] = useState(false);

  // serverUrl should point to the frontend app, not the backend API
  // e.g., data-server="http://localhost:5173" or data-server="https://jarvis.example.com"
  const chatUrl = `${serverUrl.replace(/\/$/, '')}/?embed=true`;

  const positionStyles: Record<string, React.CSSProperties> = {
    'bottom-right': { bottom: '20px', right: '20px' },
    'bottom-left': { bottom: '20px', left: '20px' },
  };

  return (
    <div style={{ position: 'fixed', zIndex: 99999, ...positionStyles[position] || positionStyles['bottom-right'] }}>
      {/* Chat iframe - only render when open to avoid loading the app eagerly */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            bottom: '70px',
            right: position === 'bottom-left' ? 'auto' : '0',
            left: position === 'bottom-left' ? '0' : 'auto',
            width: '400px',
            height: '600px',
            borderRadius: '16px',
            overflow: 'hidden',
            boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
            border: '1px solid rgba(0,0,0,0.1)',
          }}
        >
          <iframe
            src={chatUrl}
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              colorScheme: 'normal',
            }}
            title="Jarvis Chat"
            allow="microphone"
          />
        </div>
      )}

      {/* Floating button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '56px',
          height: '56px',
          borderRadius: '28px',
          background: '#2563eb',
          color: '#fff',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 4px 16px rgba(37, 99, 235, 0.4)',
          transition: 'transform 0.2s',
          fontSize: '24px',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.1)')}
        onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
      >
        {isOpen ? (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        )}
      </button>
    </div>
  );
}
