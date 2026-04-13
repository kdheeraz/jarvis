import type { WSEvent } from '../types';

export class ChatWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private onEvent: (event: WSEvent) => void;
  private onConnect: () => void;
  private onDisconnect: () => void;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private shouldReconnect = true;

  constructor(
    conversationId: string,
    onEvent: (event: WSEvent) => void,
    onConnect: () => void = () => {},
    onDisconnect: () => void = () => {},
  ) {
    const wsBase = (import.meta.env.VITE_API_URL || window.location.origin).replace(/^http/, 'ws');
    this.url = `${wsBase}/ws/chat/${conversationId}`;
    this.onEvent = onEvent;
    this.onConnect = onConnect;
    this.onDisconnect = onDisconnect;
  }

  connect() {
    this.shouldReconnect = true;
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.onConnect();
      this._startPing();
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as WSEvent;
      this.onEvent(data);
    };

    this.ws.onclose = () => {
      this.onDisconnect();
      this._stopPing();
      if (this.shouldReconnect) {
        this.reconnectTimer = setTimeout(() => this.connect(), 3000);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  send(type: string, content?: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, content }));
    }
  }

  disconnect() {
    this.shouldReconnect = false;
    this._stopPing();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.ws?.close();
  }

  private pingInterval: ReturnType<typeof setInterval> | null = null;

  private _startPing() {
    this.pingInterval = setInterval(() => {
      this.send('ping');
    }, 30000);
  }

  private _stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}
