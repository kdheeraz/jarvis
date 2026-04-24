import { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';
import type { VoiceState } from '../../hooks/useVoiceMode';
import { useAppStore } from '../../store/appStore';

interface Props {
  isActive: boolean;
  state: VoiceState;
  micStream: MediaStream | null;
  onStop: () => void;
}

const STATE_LABELS: Record<VoiceState, string> = {
  idle: 'Starting...',
  connecting: 'Connecting...',
  listening: 'Listening...',
  processing: 'Processing...',
  speaking: 'Speaking...',
};

const STATE_COLORS: Record<VoiceState, string> = {
  idle: 'from-surface-900 to-surface-950',
  connecting: 'from-surface-900 to-surface-950',
  listening: 'from-blue-950 to-surface-950',
  processing: 'from-indigo-950 to-surface-950',
  speaking: 'from-primary-950 to-surface-950',
};

export function VoiceModeOverlay({ isActive, state, micStream, onStop }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const agentName = useAppStore((s) => s.agentName);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const animationRef = useRef<number>(0);

  // Create analyser from the existing mic stream (no second getUserMedia)
  useEffect(() => {
    if (!micStream) {
      analyserRef.current = null;
      return;
    }

    const audioCtx = new AudioContext();
    audioCtxRef.current = audioCtx;
    const source = audioCtx.createMediaStreamSource(micStream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.7;
    source.connect(analyser);
    analyserRef.current = analyser;

    return () => {
      audioCtx.close();
      audioCtxRef.current = null;
      analyserRef.current = null;
    };
  }, [micStream]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;

    ctx.clearRect(0, 0, width, height);

    const barCount = 64;
    const analyser = analyserRef.current;
    let dataArray: Uint8Array<ArrayBuffer> | null = null;

    if (analyser && state === 'listening') {
      dataArray = new Uint8Array(analyser.frequencyBinCount) as Uint8Array<ArrayBuffer>;
      analyser.getByteFrequencyData(dataArray);
    }

    for (let i = 0; i < barCount; i++) {
      const angle = (i / barCount) * Math.PI * 2 - Math.PI / 2;

      let amplitude = 0;
      if (state === 'listening' && dataArray) {
        const dataIndex = Math.floor((i / barCount) * dataArray.length);
        amplitude = dataArray[dataIndex] / 255;
      } else if (state === 'speaking') {
        amplitude = 0.3 + Math.sin(Date.now() / 200 + i * 0.3) * 0.3;
      } else if (state === 'connecting') {
        amplitude = 0.15 + Math.sin(Date.now() / 400 + i * 0.5) * 0.15;
      }

      const baseRadius = 80;
      const maxBarHeight = 60;
      const barHeight = maxBarHeight * amplitude;

      const innerX = centerX + Math.cos(angle) * baseRadius;
      const innerY = centerY + Math.sin(angle) * baseRadius;
      const outerX = centerX + Math.cos(angle) * (baseRadius + barHeight);
      const outerY = centerY + Math.sin(angle) * (baseRadius + barHeight);

      ctx.beginPath();
      ctx.moveTo(innerX, innerY);
      ctx.lineTo(outerX, outerY);
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';

      if (state === 'listening') {
        ctx.strokeStyle = `rgba(59, 130, 246, ${0.4 + amplitude * 0.6})`;
      } else if (state === 'speaking') {
        ctx.strokeStyle = `rgba(99, 102, 241, ${0.4 + amplitude * 0.6})`;
      } else {
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.2)';
      }

      ctx.stroke();
    }

    // Center orb
    const orbRadius = state === 'listening' ? 70 : state === 'speaking' ? 75 : 65;
    const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, orbRadius);

    if (state === 'listening') {
      gradient.addColorStop(0, 'rgba(59, 130, 246, 0.3)');
      gradient.addColorStop(1, 'rgba(59, 130, 246, 0.05)');
    } else if (state === 'speaking') {
      gradient.addColorStop(0, 'rgba(99, 102, 241, 0.3)');
      gradient.addColorStop(1, 'rgba(99, 102, 241, 0.05)');
    } else {
      gradient.addColorStop(0, 'rgba(148, 163, 184, 0.15)');
      gradient.addColorStop(1, 'rgba(148, 163, 184, 0.02)');
    }

    ctx.beginPath();
    ctx.arc(centerX, centerY, orbRadius, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();

    // Mic icon in center
    ctx.fillStyle = state === 'listening' ? '#3b82f6' : state === 'speaking' ? '#6366f1' : '#94a3b8';
    ctx.font = '28px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('\uD83C\uDF99', centerX, centerY);

    animationRef.current = requestAnimationFrame(draw);
  }, [state]);

  useEffect(() => {
    if (isActive) {
      animationRef.current = requestAnimationFrame(draw);
    }
    return () => {
      cancelAnimationFrame(animationRef.current);
    };
  }, [isActive, draw]);

  if (!isActive) return null;

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center bg-gradient-to-b ${STATE_COLORS[state]} transition-all duration-700`}
    >
      {/* Close button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onStop();
        }}
        className="absolute top-6 right-6 z-10 p-3 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
      >
        <X size={24} />
      </button>

      {/* Title */}
      <div className="absolute top-8 left-0 right-0 text-center">
        <h1 className="text-white/80 text-lg font-medium">{agentName} Voice Mode</h1>
      </div>

      {/* Visualizer */}
      <canvas
        ref={canvasRef}
        width={400}
        height={400}
        className="w-[300px] h-[300px] md:w-[400px] md:h-[400px]"
      />

      {/* State label */}
      <div className="mt-6 text-center">
        <p className="text-white/60 text-sm uppercase tracking-widest mb-3">{STATE_LABELS[state]}</p>
        {state === 'listening' && (
          <p className="text-white/40 text-sm">Speak naturally — I'm listening</p>
        )}
        {state === 'connecting' && (
          <p className="text-white/40 text-sm">Setting up voice connection...</p>
        )}
      </div>

      {/* Bottom hint */}
      <div className="absolute bottom-8 text-center">
        <p className="text-white/30 text-xs">Full duplex voice via WebRTC</p>
      </div>
    </div>
  );
}
