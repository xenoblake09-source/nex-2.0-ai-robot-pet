/**
 * Sound playback for NEX.
 *
 * Animal voices are original, procedurally synthesised audio files that ship
 * inside the app (see `tools/generate_animal_sounds.py`) — no third party
 * recordings, so there are no licensing problems.
 *
 * If an asset is missing the player falls back to a short synthesised chirp so
 * NEX never pretends to play a sound that is not there.
 */

const cache = new Map<string, HTMLAudioElement>();
let audioUnlocked = false;

function assetUrl(name: string): string {
  const base = import.meta.env.BASE_URL || './';
  return `${base.endsWith('/') ? base : `${base}/`}sounds/${name}.wav`;
}

function getAudio(name: string): HTMLAudioElement {
  let audio = cache.get(name);
  if (!audio) {
    audio = new Audio(assetUrl(name));
    audio.preload = 'auto';
    cache.set(name, audio);
  }
  return audio;
}

/** Browsers require a user gesture before audio can play; call this on tap. */
export function unlockAudio(): void {
  if (audioUnlocked) return;
  audioUnlocked = true;
  try {
    const Ctor =
      window.AudioContext ||
      (window as never as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const ctx = new Ctor();
    void ctx.resume();
    const buffer = ctx.createBuffer(1, 1, 22050);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.start(0);
  } catch {
    /* ignore */
  }
}

function playFile(name: string): Promise<boolean> {
  return new Promise((resolve) => {
    let settled = false;
    const audio = getAudio(name);
    const done = (ok: boolean) => {
      if (settled) return;
      settled = true;
      audio.removeEventListener('ended', onEnd);
      audio.removeEventListener('error', onError);
      resolve(ok);
    };
    const onEnd = () => done(true);
    const onError = () => done(false);
    audio.addEventListener('ended', onEnd);
    audio.addEventListener('error', onError);
    try {
      audio.currentTime = 0;
      const p = audio.play();
      if (p && typeof p.catch === 'function') {
        p.catch(() => done(false));
      }
    } catch {
      done(false);
    }
    // Never hang: if the file cannot play we report failure after 4s.
    setTimeout(() => done(false), 4000);
  });
}

/** Tiny Web Audio chirp used only when a real asset is unavailable. */
function synthChirp(): Promise<boolean> {
  return new Promise((resolve) => {
    try {
      const Ctor =
        window.AudioContext ||
        (window as never as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new Ctor();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(520, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.16);
      gain.gain.setValueAtTime(0.0001, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.22, ctx.currentTime + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.3);
      osc.connect(gain).connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.32);
      setTimeout(() => {
        ctx.close?.().catch(() => undefined);
        resolve(true);
      }, 360);
    } catch {
      resolve(false);
    }
  });
}

export interface SoundResult {
  ok: boolean;
  fallback: boolean;
}

/** Plays an animal voice. `animal` is e.g. "dog". */
export async function playAnimalSound(animal: string): Promise<SoundResult> {
  const name = animal.toLowerCase().trim().replace(/[^a-z]/g, '');
  if (!name) return { ok: false, fallback: false };
  const played = await playFile(name);
  if (played) return { ok: true, fallback: false };
  const fallback = await synthChirp();
  return { ok: fallback, fallback: true };
}

/** Plays a short interface sound (start / error / chime). */
export async function playUiSound(name: 'start' | 'error' | 'chime'): Promise<SoundResult> {
  const played = await playFile(name);
  if (played) return { ok: true, fallback: false };
  return { ok: false, fallback: false };
}

export const SUPPORTED_ANIMALS = [
  'dog',
  'cat',
  'cow',
  'lion',
  'tiger',
  'monkey',
  'elephant',
  'duck',
  'chicken',
  'horse',
  'sheep',
  'goat',
  'wolf',
  'frog',
  'bird',
  'pig',
  'donkey',
  'rooster',
  'owl',
  'bee',
];
