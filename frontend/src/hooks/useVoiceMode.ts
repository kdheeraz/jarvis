import { useState, useCallback, useRef, useEffect } from 'react';

export type VoiceState = 'idle' | 'connecting' | 'listening' | 'processing' | 'speaking';

interface UseVoiceModeOptions {
  conversationId: string | null;
  onConversationCreated?: (id: string) => void;
}

interface UseVoiceModeReturn {
  isActive: boolean;
  state: VoiceState;
  statusText: string | null;
  isSupported: boolean;
  micStream: MediaStream | null;
  start: () => void;
  stop: () => void;
  rebind: (conversationId: string) => void;
}

const API_BASE = import.meta.env.VITE_API_URL || window.location.origin;

export function useVoiceMode({ conversationId, onConversationCreated }: UseVoiceModeOptions): UseVoiceModeReturn {
  const [isActive, setIsActive] = useState(false);
  const [state, setState] = useState<VoiceState>('idle');
  const [statusText, setStatusText] = useState<string | null>(null);
  const [micStream, setMicStream] = useState<MediaStream | null>(null);

  const pcRef = useRef<RTCPeerConnection | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const webrtcIdRef = useRef<string>('');
  const isActiveRef = useRef(false);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const remoteAnalyserRef = useRef<AnalyserNode | null>(null);
  const remoteAudioCtxRef = useRef<AudioContext | null>(null);
  const audioMonitorRef = useRef<number>(0);
  const micAnalyserRef = useRef<AnalyserNode | null>(null);
  const micAudioCtxRef = useRef<AudioContext | null>(null);
  const micWasTalkingRef = useRef(false);

  const isSupported = typeof RTCPeerConnection !== 'undefined' && typeof navigator.mediaDevices !== 'undefined';

  const sendToServer = useCallback(async (body: Record<string, unknown>) => {
    const res = await fetch(`${API_BASE}/webrtc/offer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return res.json();
  }, []);

  const cleanup = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    cancelAnimationFrame(audioMonitorRef.current);
    if (remoteAudioCtxRef.current) {
      remoteAudioCtxRef.current.close();
      remoteAudioCtxRef.current = null;
      remoteAnalyserRef.current = null;
    }
    if (pcRef.current) {
      pcRef.current.onconnectionstatechange = null;
      pcRef.current.onicecandidate = null;
      pcRef.current.getSenders().forEach((sender) => {
        sender.track?.stop();
      });
      pcRef.current.close();
      pcRef.current = null;
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.srcObject = null;
    }
  }, []);

  const stop = useCallback(() => {
    if (!isActiveRef.current) return;
    isActiveRef.current = false;
    cleanup();
    setMicStream(null);
    setIsActive(false);
    setState('idle');
    setStatusText(null);
  }, [cleanup]);

  const start = useCallback(async () => {
    if (!isSupported) return;

    setIsActive(true);
    isActiveRef.current = true;
    setState('connecting');

    try {
      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const webrtcId = Math.random().toString(36).substring(2);
      webrtcIdRef.current = webrtcId;

      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
      });
      pcRef.current = pc;

      // Create audio element for playback
      if (!audioRef.current) {
        audioRef.current = document.createElement('audio');
        audioRef.current.autoplay = true;
        audioRef.current.volume = 1;
      }

      // Handle incoming audio from server (TTS) + monitor for speaking detection
      pc.addEventListener('track', (event) => {
        if (audioRef.current && event.streams[0]) {
          audioRef.current.srcObject = event.streams[0];
          audioRef.current.play().catch((e) => console.debug('Autoplay failed:', e));

          // Set up analyser on remote audio to detect when server is speaking
          const actx = new AudioContext();
          remoteAudioCtxRef.current = actx;
          const source = actx.createMediaStreamSource(event.streams[0]);
          const analyser = actx.createAnalyser();
          analyser.fftSize = 256;
          source.connect(analyser);
          remoteAnalyserRef.current = analyser;

          // Monitor remote audio levels
          const dataArr = new Uint8Array(analyser.frequencyBinCount);
          let wasSpeaking = false;
          const monitor = () => {
            if (!isActiveRef.current) return;
            analyser.getByteFrequencyData(dataArr);
            const avg = dataArr.reduce((a, b) => a + b, 0) / dataArr.length;
            const isSpeaking = avg > 5;

            if (isSpeaking && !wasSpeaking) {
              // Server started sending audio
              if (silenceTimerRef.current) {
                clearTimeout(silenceTimerRef.current);
                silenceTimerRef.current = null;
              }
              setState('speaking');
              setStatusText(null);
              wasSpeaking = true;
            } else if (!isSpeaking && wasSpeaking) {
              // Server stopped sending audio — back to listening
              wasSpeaking = false;
              setState('listening');
            }
            audioMonitorRef.current = requestAnimationFrame(monitor);
          };
          audioMonitorRef.current = requestAnimationFrame(monitor);
        }
      });

      // Monitor connection state
      pc.addEventListener('connectionstatechange', () => {
        switch (pc.connectionState) {
          case 'connected':
            setState('listening');
            break;
          case 'disconnected':
          case 'failed':
            if (isActiveRef.current) {
              stop();
            }
            break;
        }
      });

      // Create data channel for text messages from server
      const dataChannel = pc.createDataChannel('text');
      dataChannel.onopen = () => {
        dataChannel.send('handshake');
      };
      dataChannel.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'end_stream') {
            setState('listening');
            setStatusText(null);
          } else if (msg.type === 'status') {
            setState('processing');
            setStatusText(msg.message || 'Processing...');
          }
        } catch {
          // Plain text messages
        }
      };

      // Expose mic stream for visualization
      setMicStream(stream);

      // Add mic tracks to peer connection
      stream.getTracks().forEach((track) => {
        pc.addTrack(track, stream);
      });

      // Send ICE candidates to server
      pc.onicecandidate = ({ candidate }) => {
        if (candidate) {
          sendToServer({
            candidate: candidate.toJSON(),
            webrtc_id: webrtcId,
            type: 'ice-candidate',
          }).catch((e) => console.error('Error sending ICE candidate:', e));
        }
      };

      // Create and send offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const answer = await sendToServer({
        sdp: offer.sdp,
        type: offer.type,
        webrtc_id: webrtcId,
      });

      if (answer.status === 'failed') {
        console.error('WebRTC offer failed:', answer.meta?.error);
        stop();
        return;
      }

      await pc.setRemoteDescription(answer);

      // Bind the WebRTC session to a chat conversation so voice and text
      // share the same history. If no conversation is active, the server
      // creates one and returns its id.
      try {
        const bindRes = await fetch(`${API_BASE}/api/voice/bind`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ webrtc_id: webrtcId, conversation_id: conversationId }),
        });
        if (bindRes.ok) {
          const { conversation_id: boundId } = await bindRes.json();
          if (boundId && boundId !== conversationId && onConversationCreated) {
            onConversationCreated(boundId);
          }
        } else {
          console.error('Voice bind failed:', await bindRes.text());
        }
      } catch (e) {
        console.error('Voice bind error:', e);
      }
    } catch (e) {
      console.error('Voice mode failed to start:', e);
      stop();
    }
  }, [isSupported, sendToServer, stop, conversationId, onConversationCreated]);

  const rebind = useCallback(
    async (newConversationId: string) => {
      if (!isActiveRef.current || !webrtcIdRef.current) return;
      try {
        await fetch(`${API_BASE}/api/voice/bind`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            webrtc_id: webrtcIdRef.current,
            conversation_id: newConversationId,
          }),
        });
      } catch (e) {
        console.error('Voice rebind error:', e);
      }
    },
    [],
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isActiveRef.current = false;
      cleanup();
    };
  }, [cleanup]);

  return {
    isActive,
    state,
    statusText,
    isSupported,
    micStream,
    start,
    stop,
    rebind,
  };
}
