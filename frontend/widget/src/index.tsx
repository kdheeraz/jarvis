import React from 'react';
import ReactDOM from 'react-dom/client';
import { Widget } from './Widget';

// Auto-initialize when script loads
(function () {
  const script = document.currentScript as HTMLScriptElement | null;
  // Default: derive server URL from where this script was loaded
  const scriptOrigin = script?.src ? new URL(script.src).origin : '';
  const serverUrl = script?.getAttribute('data-server') || scriptOrigin;
  const position = script?.getAttribute('data-position') || 'bottom-right';
  const theme = script?.getAttribute('data-theme') || 'auto';

  // Create container
  const container = document.createElement('div');
  container.id = 'jarvis-widget-root';
  document.body.appendChild(container);

  // Mount React app
  const root = ReactDOM.createRoot(container);
  root.render(
    <React.StrictMode>
      <Widget serverUrl={serverUrl} position={position} theme={theme} />
    </React.StrictMode>,
  );
})();
