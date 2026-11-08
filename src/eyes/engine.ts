/**
 * NEX eye animation engine.
 *
 * A single requestAnimationFrame loop drives both eyes. The engine never
 * triggers React re-renders — it writes straight to SVG attributes, which keeps
 * the animation at 60fps on mid-range Android phones and stays battery friendly.
 */
import { DEFAULT_EYE, EXPRESSIONS, type Behavior, type EyeState } from './expressions';

export interface EyeDraw {
  bodyPath: string;
  haloPath: string;
  pupilPath: string;
  heartPath: string;
  tearPath: string;
  pupilOpacity: number;
  heartOpacity: number;
  highlightOpacity: number;
  tearOpacity: number;
  pupilColor: string;
  tint: string;
  glow: string;
  haloOpacity: number;
  strokeOpacity: number;
  pupilCx: number;
  pupilCy: number;
  pupilRadius: number;
  translateX: number;
  translateY: number;
  scale: number;
  rotate: number;
}

export type EyeRenderer = (draw: EyeDraw) => void;

const VB = 240;
const EYE_SIZE = 186;
const EYE_RADIUS = 56;
const MAX_CLOSE = 0.47;

function clamp(v: number, min: number, max: number): number {
  return v < min ? min : v > max ? max : v;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '');
  const full =
    clean.length === 3
      ? clean
          .split('')
          .map((c) => c + c)
          .join('')
      : clean;
  const num = parseInt(full, 16);
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
}

function lerpColor(a: string, b: string, t: number): string {
  const [r1, g1, b1] = hexToRgb(a);
  const [r2, g2, b2] = hexToRgb(b);
  const r = Math.round(lerp(r1, r2, t));
  const g = Math.round(lerp(g1, g2, t));
  const bl = Math.round(lerp(b1, b2, t));
  return `rgb(${r},${g},${bl})`;
}

/** Rounded-rect eye outline whose top/bottom edges can close like eyelids. */
function eyeBodyPath(topInset: number, bottomInset: number, tiltPx: number): string {
  const cx = VB / 2;
  const cy = VB / 2;
  const x0 = cx - EYE_SIZE / 2;
  const x1 = cx + EYE_SIZE / 2;
  const y0 = cy - EYE_SIZE / 2;
  const y1 = cy + EYE_SIZE / 2;

  const top = y0 + topInset * EYE_SIZE;
  const bottom = y1 - bottomInset * EYE_SIZE;
  const height = Math.max(4, bottom - top);
  const r = Math.max(1.5, Math.min(EYE_RADIUS, height / 2));
  const tilt = clamp(tiltPx, -EYE_SIZE * 0.16, EYE_SIZE * 0.16);

  const tl = top + tilt;
  const tr = top - tilt;
  const bl = bottom - tilt;
  const br = bottom + tilt;

  return [
    `M ${(x0 + r).toFixed(2)} ${tl.toFixed(2)}`,
    `L ${(x1 - r).toFixed(2)} ${tr.toFixed(2)}`,
    `Q ${x1.toFixed(2)} ${tr.toFixed(2)} ${x1.toFixed(2)} ${(tr + r).toFixed(2)}`,
    `L ${x1.toFixed(2)} ${(br - r).toFixed(2)}`,
    `Q ${x1.toFixed(2)} ${br.toFixed(2)} ${(x1 - r).toFixed(2)} ${br.toFixed(2)}`,
    `L ${(x0 + r).toFixed(2)} ${bl.toFixed(2)}`,
    `Q ${x0.toFixed(2)} ${bl.toFixed(2)} ${x0.toFixed(2)} ${(bl - r).toFixed(2)}`,
    `L ${x0.toFixed(2)} ${(tl + r).toFixed(2)}`,
    `Q ${x0.toFixed(2)} ${tl.toFixed(2)} ${(x0 + r).toFixed(2)} ${tl.toFixed(2)}`,
    'Z',
  ].join(' ');
}

/** Superellipse — smoothly morphs from a circle (n=2) to a rounded square (n=8). */
function superellipsePath(cx: number, cy: number, rx: number, ry: number, n: number): string {
  const steps = 40;
  const e = 2 / clamp(n, 2, 10);
  const parts: string[] = [];
  for (let i = 0; i < steps; i++) {
    const t = (i / steps) * Math.PI * 2;
    const c = Math.cos(t);
    const s = Math.sin(t);
    const x = cx + rx * Math.sign(c) * Math.pow(Math.abs(c), e);
    const y = cy + ry * Math.sign(s) * Math.pow(Math.abs(s), e);
    parts.push(`${x.toFixed(2)} ${y.toFixed(2)}`);
  }
  return `M ${parts.join(' L ')} Z`;
}

function heartPath(cx: number, cy: number, r: number): string {
  return [
    `M ${cx.toFixed(2)} ${(cy + r * 0.95).toFixed(2)}`,
    `C ${(cx - r * 1.3).toFixed(2)} ${(cy - r * 0.15).toFixed(2)} ${(cx - r * 0.75).toFixed(2)} ${(cy - r * 1.2).toFixed(2)} ${cx.toFixed(2)} ${(cy - r * 0.45).toFixed(2)}`,
    `C ${(cx + r * 0.75).toFixed(2)} ${(cy - r * 1.2).toFixed(2)} ${(cx + r * 1.3).toFixed(2)} ${(cy - r * 0.15).toFixed(2)} ${cx.toFixed(2)} ${(cy + r * 0.95).toFixed(2)}`,
    'Z',
  ].join(' ');
}

function tearPath(cx: number, cy: number, r: number): string {
  return [
    `M ${cx.toFixed(2)} ${(cy - r).toFixed(2)}`,
    `C ${(cx + r * 0.75).toFixed(2)} ${(cy + r * 0.35).toFixed(2)} ${(cx + r * 0.55).toFixed(2)} ${(cy + r).toFixed(2)} ${cx.toFixed(2)} ${(cy + r).toFixed(2)}`,
    `C ${(cx - r * 0.55).toFixed(2)} ${(cy + r).toFixed(2)} ${(cx - r * 0.75).toFixed(2)} ${(cy + r * 0.35).toFixed(2)} ${cx.toFixed(2)} ${(cy - r).toFixed(2)}`,
    'Z',
  ].join(' ');
}

function stateFromPreset(expression: string, eyeIndex: number): EyeState {
  const preset = EXPRESSIONS[expression] ?? EXPRESSIONS.neutral;
  const state: EyeState = { ...DEFAULT_EYE, ...preset.base };
  const override = eyeIndex === 0 ? preset.eye0 : preset.eye1;
  if (override) Object.assign(state, override);
  if (preset.mirrorTilt !== false && eyeIndex === 1) {
    state.tilt = -state.tilt;
  }
  return state;
}

export class EyeEngine {
  private renderers: Array<EyeRenderer | null> = [null, null];
  private current: EyeState[] = [stateFromPreset('neutral', 0), stateFromPreset('neutral', 1)];
  private targets: EyeState[] = [stateFromPreset('neutral', 0), stateFromPreset('neutral', 1)];
  private expression = 'neutral';
  private behavior: Behavior = 'lookAround';
  private colorFrom = { tint: DEFAULT_EYE.tint, glow: DEFAULT_EYE.glow, pupil: DEFAULT_EYE.pupilColor };
  private colorTo = { ...this.colorFrom };
  private colorBlend = 1;

  private time = 0;
  private lastFrame = 0;
  private raf = 0;
  private running = false;

  private blinkPhase = 0;
  private nextBlink = 2.4;
  private lookX = 0;
  private lookY = 0;
  private lookTargetX = 0;
  private lookTargetY = 0;
  private nextLook = 1.5;
  private thinkX = -0.4;
  private thinkY = -0.35;
  private nextThink = 1.6;

  register(index: number, renderer: EyeRenderer): void {
    this.renderers[index] = renderer;
  }

  unregister(index: number): void {
    this.renderers[index] = null;
  }

  setExpression(expression: string): void {
    if (expression === this.expression) return;
    this.expression = expression;
    const preset = EXPRESSIONS[expression] ?? EXPRESSIONS.neutral;
    this.behavior = preset.behavior ?? 'idle';
    for (let i = 0; i < 2; i++) {
      const next = stateFromPreset(expression, i);
      this.targets[i] = next;
      const cur = this.current[i];
      this.colorFrom = { tint: cur.tint, glow: cur.glow, pupil: cur.pupilColor };
      this.colorTo = { tint: next.tint, glow: next.glow, pupil: next.pupilColor };
      this.colorBlend = 0;
    }
  }

  getExpression(): string {
    return this.expression;
  }

  start(): void {
    if (this.running) return;
    this.running = true;
    this.lastFrame = performance.now();
    const loop = (now: number) => {
      if (!this.running) return;
      const dt = Math.min(0.05, (now - this.lastFrame) / 1000);
      this.lastFrame = now;
      this.update(dt);
      this.raf = requestAnimationFrame(loop);
    };
    this.raf = requestAnimationFrame(loop);
  }

  stop(): void {
    this.running = false;
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
  }

  private update(dt: number): void {
    this.time += dt;

    // ---- blinking -----------------------------------------------------
    const blinkSuppressed = this.expression === 'blink' || this.expression === 'sleep';
    if (!blinkSuppressed) {
      this.nextBlink -= dt;
      if (this.nextBlink <= 0) {
        this.blinkPhase = 1;
        this.nextBlink = 2.1 + Math.random() * 3.6;
      }
    }
    if (this.blinkPhase > 0) this.blinkPhase = Math.max(0, this.blinkPhase - dt / 0.17);
    const blinkAmt = blinkSuppressed ? 0 : Math.sin(this.blinkPhase * Math.PI);

    // ---- colour blending ---------------------------------------------
    this.colorBlend = Math.min(1, this.colorBlend + dt * 2.4);

    // ---- idle look-around --------------------------------------------
    if (this.behavior === 'lookAround') {
      this.nextLook -= dt;
      if (this.nextLook <= 0) {
        this.lookTargetX = (Math.random() * 2 - 1) * 0.55;
        this.lookTargetY = (Math.random() * 2 - 1) * 0.35;
        this.nextLook = 1.6 + Math.random() * 3.2;
      }
      const k = 1 - Math.exp(-dt * 3.2);
      this.lookX += (this.lookTargetX - this.lookX) * k;
      this.lookY += (this.lookTargetY - this.lookY) * k;
    }

    // ---- thinking eye darts -------------------------------------------
    if (this.behavior === 'think') {
      this.nextThink -= dt;
      if (this.nextThink <= 0) {
        const flip = Math.random() > 0.5;
        this.thinkX = flip ? 0.42 : -0.42;
        this.thinkY = flip ? -0.1 : -0.4;
        this.nextThink = 1.4 + Math.random() * 0.9;
      }
    }

    for (let eye = 0; eye < 2; eye++) {
      const cur = this.current[eye];
      const tgt = this.targets[eye];
      const k = 1 - Math.exp(-dt * 6.5);

      cur.topInset += (tgt.topInset - cur.topInset) * k;
      cur.bottomInset += (tgt.bottomInset - cur.bottomInset) * k;
      cur.tilt += (tgt.tilt - cur.tilt) * k;
      cur.pupilScale += (tgt.pupilScale - cur.pupilScale) * k;
      cur.pupilExponent += (tgt.pupilExponent - cur.pupilExponent) * k;
      cur.heart += (tgt.heart - cur.heart) * k;
      cur.tear += (tgt.tear - cur.tear) * k;
      cur.halo += (tgt.halo - cur.halo) * k;

      let pupilX = tgt.pupilX;
      let pupilY = tgt.pupilY;

      switch (this.behavior) {
        case 'lookAround':
          pupilX = cur.pupilX * 0.25 + this.lookX;
          pupilY = cur.pupilY * 0.25 + this.lookY;
          break;
        case 'think':
          pupilX = this.thinkX;
          pupilY = this.thinkY;
          break;
        case 'game': {
          const step = Math.floor(this.time / 0.55) % 4;
          const xs = [-0.45, 0.45, 0.45, -0.45];
          const ys = [-0.38, -0.38, 0.3, 0.3];
          pupilX = xs[step];
          pupilY = ys[step];
          break;
        }
        default:
          break;
      }

      // ---- behaviour motion -------------------------------------------
      let translateX = 0;
      let translateY = 0;
      let scale = 1;
      let rotate = 0;
      let pupilScale = cur.pupilScale;

      switch (this.behavior) {
        case 'talk': {
          const bob = Math.sin(this.time * 9.4) * 1.4 + Math.sin(this.time * 15.1) * 0.9;
          translateY += bob;
          pupilScale *= 1 + Math.sin(this.time * 11.3) * 0.045;
          break;
        }
        case 'dance': {
          const phase = this.time * 6.1 + (eye === 0 ? 0 : Math.PI);
          const bounce = Math.abs(Math.sin(phase));
          translateY -= bounce * 15;
          translateX += Math.sin(phase * 0.5) * 5;
          rotate = Math.sin(phase) * 7;
          pupilScale *= 1 + bounce * 0.12;
          break;
        }
        case 'sleep': {
          scale = 1 + Math.sin(this.time * 1.5) * 0.016;
          break;
        }
        case 'happyBounce': {
          const b = Math.sin(this.time * 3.3);
          translateY += b * 4.5;
          scale = 1 + b * 0.032;
          break;
        }
        default:
          break;
      }

      // ---- assemble the frame ----------------------------------------
      let topInset = cur.topInset;
      let bottomInset = cur.bottomInset;
      if (blinkAmt > 0) {
        topInset = lerp(topInset, MAX_CLOSE, blinkAmt);
        bottomInset = lerp(bottomInset, MAX_CLOSE, blinkAmt);
      }

      const bodyPath = eyeBodyPath(topInset, bottomInset, cur.tilt * 15);
      const haloPath = eyeBodyPath(cur.topInset, cur.bottomInset, cur.tilt * 15);

      const cx = VB / 2 + pupilX * EYE_SIZE * 0.2;
      const cy = VB / 2 + pupilY * EYE_SIZE * 0.2;
      const radius = pupilScale * EYE_SIZE * 0.3;
      const pupilPath = superellipsePath(cx, cy, radius, radius, cur.pupilExponent);
      const heart = heartPath(cx, cy, radius * 1.12);
      const tear = tearPath(VB / 2 - EYE_SIZE * 0.24, VB / 2 + EYE_SIZE * 0.3, 7);

      const draw: EyeDraw = {
        bodyPath,
        haloPath,
        pupilPath,
        heartPath: heart,
        tearPath: tear,
        pupilOpacity: 1 - cur.heart,
        heartOpacity: cur.heart,
        highlightOpacity: (1 - cur.heart) * (blinkAmt > 0.6 ? 0 : 1),
        tearOpacity: cur.tear * (1 - blinkAmt),
        pupilColor: lerpColor(this.colorFrom.pupil, this.colorTo.pupil, this.colorBlend),
        tint: lerpColor(this.colorFrom.tint, this.colorTo.tint, this.colorBlend),
        glow: lerpColor(this.colorFrom.glow, this.colorTo.glow, this.colorBlend),
        haloOpacity: cur.halo * (this.behavior === 'sleep' ? 0.7 : 1),
        strokeOpacity: 0.35 + cur.halo * 0.25,
        pupilCx: cx,
        pupilCy: cy,
        pupilRadius: radius,
        translateX,
        translateY,
        scale,
        rotate,
      };

      this.renderers[eye]?.(draw);
    }
  }
}

export const eyeEngine = new EyeEngine();
