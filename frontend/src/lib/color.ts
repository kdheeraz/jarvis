export type RGB = [number, number, number];

export const hexToRgb = (hex: string): RGB => {
  const h = hex.replace('#', '');
  const n = h.length === 3
    ? h.split('').map((c) => c + c).join('')
    : h.padEnd(6, '0');
  const v = parseInt(n, 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
};

export const rgbToHsl = ([r, g, b]: RGB): [number, number, number] => {
  const rn = r / 255, gn = g / 255, bn = b / 255;
  const max = Math.max(rn, gn, bn), min = Math.min(rn, gn, bn);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = 0;
  switch (max) {
    case rn: h = (gn - bn) / d + (gn < bn ? 6 : 0); break;
    case gn: h = (bn - rn) / d + 2; break;
    case bn: h = (rn - gn) / d + 4; break;
  }
  return [h / 6, s, l];
};

export const hslToRgb = (h: number, s: number, l: number): RGB => {
  if (s === 0) { const v = l * 255; return [v, v, v]; }
  const hue = (p: number, q: number, t: number) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  return [hue(p, q, h + 1 / 3) * 255, hue(p, q, h) * 255, hue(p, q, h - 1 / 3) * 255];
};

export const adjust = (base: RGB, dH: number, dS: number, dL: number): RGB => {
  const [h, s, l] = rgbToHsl(base);
  return hslToRgb(
    (h + dH + 1) % 1,
    Math.max(0, Math.min(1, s + dS)),
    Math.max(0, Math.min(1, l + dL)),
  );
};

// Tailwind-style 50..950 shade scale derived from one hex.
// Each shade is an [R, G, B] triplet (0-255). Lightness is pinned per-shade
// so shade 500 stays close to the input hex's lightness band.
const SHADE_LIGHTNESS: Record<string, number> = {
  '50':  0.97,
  '100': 0.93,
  '200': 0.85,
  '300': 0.75,
  '400': 0.65,
  '500': 0.55,
  '600': 0.47,
  '700': 0.39,
  '800': 0.30,
  '900': 0.22,
  '950': 0.13,
};

export const shadeScale = (hex: string): Record<string, RGB> => {
  const [h, s] = rgbToHsl(hexToRgb(hex));
  const out: Record<string, RGB> = {};
  for (const [shade, l] of Object.entries(SHADE_LIGHTNESS)) {
    // Dial saturation down a touch at the extremes so 50 doesn't look neon
    // and 950 doesn't lose the hue entirely.
    const sAdj = s * (l > 0.9 || l < 0.2 ? 0.55 : 1);
    out[shade] = hslToRgb(h, Math.max(0, Math.min(1, sAdj)), l);
  }
  return out;
};

export const rgbTriplet = (rgb: RGB): string =>
  `${rgb[0] | 0} ${rgb[1] | 0} ${rgb[2] | 0}`;

// Write --primary-<shade> CSS vars on :root, in "R G B" form so Tailwind
// can consume them via `rgb(var(--primary-500) / <alpha-value>)`.
export const applyThemeVars = (hex: string) => {
  const scale = shadeScale(hex);
  const root = document.documentElement;
  for (const [shade, rgb] of Object.entries(scale)) {
    root.style.setProperty(`--primary-${shade}`, rgbTriplet(rgb));
  }
};
