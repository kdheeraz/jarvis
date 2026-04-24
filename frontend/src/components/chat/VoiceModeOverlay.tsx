import { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';
import type { VoiceState } from '../../hooks/useVoiceMode';
import { useAppStore } from '../../store/appStore';
import { hexToRgb, adjust, type RGB } from '../../lib/color';

interface Props {
  isActive: boolean;
  state: VoiceState;
  micStream: MediaStream | null;
  onStop: () => void;
}

const STATE_LABELS: Record<VoiceState, string> = {
  idle: 'Starting',
  connecting: 'Connecting',
  listening: 'Listening',
  processing: 'Thinking',
  speaking: 'Speaking',
};

type Palette = { inner: RGB; outer: RGB; halo: RGB };

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerpColor = (a: RGB, b: RGB, t: number): RGB => [
  lerp(a[0], b[0], t),
  lerp(a[1], b[1], t),
  lerp(a[2], b[2], t),
];
const rgba = (c: RGB, alpha: number) =>
  `rgba(${c[0] | 0}, ${c[1] | 0}, ${c[2] | 0}, ${alpha})`;

// Build a per-state palette from a single theme hex (e.g. "#3b82f6").
// State variation is expressed as hue/lightness shifts so any theme color works.
const paletteFor = (baseHex: string, state: VoiceState): Palette => {
  const base = hexToRgb(baseHex);
  switch (state) {
    case 'listening':
      return {
        inner: adjust(base, 0, -0.05, 0.35),
        outer: base,
        halo: adjust(base, 0, 0, 0.1),
      };
    case 'processing':
      // Slight hue rotation to read as "thinking" without needing a second theme color
      return {
        inner: adjust(base, 0.05, -0.1, 0.3),
        outer: adjust(base, 0.05, 0, -0.05),
        halo: adjust(base, 0.05, 0, 0.05),
      };
    case 'speaking':
      return {
        inner: adjust(base, 0, -0.1, 0.4),
        outer: adjust(base, 0, 0.05, -0.05),
        halo: adjust(base, 0, 0, 0.1),
      };
    case 'idle':
    case 'connecting':
    default:
      return {
        inner: adjust(base, 0, -0.1, 0.3),
        outer: adjust(base, 0, -0.05, 0.05),
        halo: adjust(base, 0, 0, 0.05),
      };
  }
};

export function VoiceModeOverlay({ isActive, state, micStream, onStop }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const agentName = useAppStore((s) => s.agentName);
  const themeColor = useAppStore((s) => s.themeColor);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const animationRef = useRef<number>(0);

  // Smoothed values for organic motion
  const amplitudeRef = useRef(0);
  const paletteRef = useRef<Palette>(paletteFor(themeColor, 'idle'));

  useEffect(() => {
    if (!micStream) {
      analyserRef.current = null;
      return;
    }

    const audioCtx = new AudioContext();
    audioCtxRef.current = audioCtx;
    const source = audioCtx.createMediaStreamSource(micStream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0.85;
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
    const t = performance.now() / 1000;

    ctx.clearRect(0, 0, width, height);

    // --- Sample audio amplitude (listening only — speaking uses synthetic breath) ---
    let rawAmp = 0;
    const analyser = analyserRef.current;
    if (analyser && state === 'listening') {
      const data = new Uint8Array(analyser.frequencyBinCount) as Uint8Array<ArrayBuffer>;
      analyser.getByteFrequencyData(data);
      let sum = 0;
      // Focus on speech band (rough low/mid)
      const span = Math.min(data.length, 64);
      for (let i = 2; i < span; i++) sum += data[i];
      rawAmp = sum / (span * 255);
      rawAmp = Math.min(1, rawAmp * 2.2);
    } else if (state === 'speaking') {
      // Gentle wave while Samantha-style speaking
      rawAmp = 0.45 + Math.sin(t * 3.1) * 0.18 + Math.sin(t * 5.7) * 0.08;
    } else if (state === 'processing') {
      rawAmp = 0.25 + Math.sin(t * 1.6) * 0.08;
    } else {
      // idle breath
      rawAmp = 0.15 + Math.sin(t * 0.9) * 0.05;
    }

    // Smooth towards target for organic feel
    amplitudeRef.current = lerp(amplitudeRef.current, rawAmp, 0.12);
    const amp = amplitudeRef.current;

    // Smoothly crossfade palette (derived from theme color each state)
    const target = paletteFor(themeColor, state);
    paletteRef.current = {
      inner: lerpColor(paletteRef.current.inner, target.inner, 0.05),
      outer: lerpColor(paletteRef.current.outer, target.outer, 0.05),
      halo:  lerpColor(paletteRef.current.halo,  target.halo,  0.05),
    };
    const pal = paletteRef.current;

    // --- Outer halos (three layered, breathing) ---
    // Cap total halo extent so it always fades to 0 inside the canvas,
    // otherwise the gradient hits the canvas edge and shows a square clip.
    const maxExtent = Math.min(centerX, centerY) - 4;
    const breath = 1 + Math.sin(t * 0.7) * 0.04;
    const baseRadius = 110;
    const reactive = baseRadius + amp * 38;

    for (let i = 3; i >= 1; i--) {
      const r = Math.min(reactive * (1 + i * 0.5) * breath, maxExtent);
      const alpha = (0.16 / i) * (0.6 + amp * 0.8);
      const g = ctx.createRadialGradient(centerX, centerY, reactive * 0.6, centerX, centerY, r);
      g.addColorStop(0, rgba(pal.halo, alpha));
      g.addColorStop(1, rgba(pal.halo, 0));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(centerX, centerY, r, 0, Math.PI * 2);
      ctx.fill();
    }

    // --- The orb: morphing closed path driven by soft noise ---
    const points = 96;
    const path: Array<[number, number]> = [];
    for (let i = 0; i < points; i++) {
      const theta = (i / points) * Math.PI * 2;
      // Layered sine "noise" — cheap, smooth, organic
      const n =
        Math.sin(theta * 3 + t * 0.9) * 0.5 +
        Math.sin(theta * 5 - t * 1.3) * 0.3 +
        Math.sin(theta * 2 + t * 0.4) * 0.4;
      const wobble = 1 + n * 0.045 + amp * 0.11 * Math.sin(theta * 4 + t * 2.1);
      const r = reactive * wobble;
      path.push([centerX + Math.cos(theta) * r, centerY + Math.sin(theta) * r]);
    }

    // Fill the orb with a radial gradient (cream core → warm coral edge)
    const orbGrad = ctx.createRadialGradient(
      centerX - reactive * 0.25,
      centerY - reactive * 0.3,
      reactive * 0.1,
      centerX,
      centerY,
      reactive * 1.05,
    );
    orbGrad.addColorStop(0, rgba(pal.inner, 0.95));
    orbGrad.addColorStop(0.55, rgba(pal.outer, 0.85));
    orbGrad.addColorStop(1, rgba(pal.outer, 0.55));

    ctx.save();
    ctx.shadowColor = rgba(pal.halo, 0.5);
    ctx.shadowBlur = Math.min(50 + amp * 30, maxExtent - reactive);
    ctx.beginPath();
    ctx.moveTo(path[0][0], path[0][1]);
    for (let i = 1; i < points; i++) {
      const [x0, y0] = path[i - 1];
      const [x1, y1] = path[i];
      ctx.quadraticCurveTo(x0, y0, (x0 + x1) / 2, (y0 + y1) / 2);
    }
    ctx.closePath();
    ctx.fillStyle = orbGrad;
    ctx.fill();
    ctx.restore();

    // --- Inner highlight (soft, offset — gives the orb dimensionality) ---
    const highlight = ctx.createRadialGradient(
      centerX - reactive * 0.3,
      centerY - reactive * 0.35,
      0,
      centerX - reactive * 0.3,
      centerY - reactive * 0.35,
      reactive * 0.8,
    );
    highlight.addColorStop(0, 'rgba(240, 248, 255, 0.5)');
    highlight.addColorStop(1, 'rgba(240, 248, 255, 0)');
    ctx.fillStyle = highlight;
    ctx.beginPath();
    ctx.arc(centerX, centerY, reactive * 1.05, 0, Math.PI * 2);
    ctx.fill();

    animationRef.current = requestAnimationFrame(draw);
  }, [state, themeColor]);

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
      className="fixed inset-0 z-50 flex flex-col items-center justify-center transition-all duration-1000"
      style={{
        background:
          'radial-gradient(ellipse at 50% 40%, #172033 0%, #0f172a 45%, #020617 100%)',
      }}
    >
      {/* Subtle theme glow overlay */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.14]"
        style={{
          backgroundImage: `radial-gradient(circle at 30% 20%, ${rgba(hexToRgb(themeColor), 0.35)}, transparent 50%), radial-gradient(circle at 70% 80%, ${rgba(adjust(hexToRgb(themeColor), 0.05, 0, -0.05), 0.25)}, transparent 50%)`,
        }}
      />

      {/* Close button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onStop();
        }}
        className="absolute top-6 right-6 z-10 p-3 rounded-full bg-white/5 hover:bg-white/10 text-white/70 hover:text-white transition-colors backdrop-blur-sm"
      >
        <X size={22} />
      </button>

      {/* Title */}
      <div className="absolute top-10 left-0 right-0 text-center">
        <h1 className="text-white/50 text-sm font-light tracking-[0.3em] uppercase">
          {agentName}
        </h1>
      </div>

      {/* Visualizer */}
      <canvas
        ref={canvasRef}
        width={900}
        height={900}
        className="w-[420px] h-[420px] md:w-[560px] md:h-[560px]"
      />

      {/* State label */}
      <div className="mt-4 text-center">
        <p className="text-white/70 text-xs font-light tracking-[0.4em] uppercase">
          {STATE_LABELS[state]}
        </p>
      </div>

      {/* Bottom hint */}
      <div className="absolute bottom-10 text-center">
        <p className="text-white/25 text-xs font-light tracking-widest">
          speak naturally
        </p>
      </div>
    </div>
  );
}
