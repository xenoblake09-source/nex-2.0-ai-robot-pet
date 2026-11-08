/**
 * Voice I/O for NEX.
 *
 * Speech recognition uses the community SpeechRecognition plugin (Android's
 * native SpeechRecognizer). On Android the recognizer stops by itself after a
 * pause, so a watchdog re-arms it — that is how NEX stays hands-free.
 *
 * Text-to-speech uses the native NexDevice plugin so NEX gets an exact
 * "speech finished" callback and never listens to its own voice.
 */
import { SpeechRecognition } from '@capacitor-community/speech-recognition';
import { NexDevice } from './native';

export type SttEvent =
  | { type: 'partial'; text: string }
  | { type: 'final'; text: string }
  | { type: 'error'; message: string }
  | { type: 'ready' };

export class SpeechInput {
  private running = false;
  private listenersRegistered = false;
  private lastPartial = '';
  private lang = 'en-IN';
  private onEvent: (event: SttEvent) => void = () => {};

  async available(): Promise<boolean> {
    try {
      const result = await SpeechRecognition.available();
      return !!result.available;
    } catch {
      return false;
    }
  }

  async hasPermission(): Promise<boolean> {
    try {
      const status = await SpeechRecognition.checkPermissions();
      return status.speechRecognition === 'granted';
    } catch {
      return false;
    }
  }

  async requestPermission(): Promise<boolean> {
    try {
      const status = await SpeechRecognition.requestPermissions();
      return status.speechRecognition === 'granted';
    } catch {
      return false;
    }
  }

  private async registerListeners(): Promise<void> {
    if (this.listenersRegistered) return;
    this.listenersRegistered = true;
    try {
      await SpeechRecognition.addListener('partialResults', (data) => {
        const text = (data.matches ?? []).join(' ').trim();
        if (text) {
          this.lastPartial = text;
          this.onEvent({ type: 'partial', text });
        }
      });
      await SpeechRecognition.addListener('listeningState', (data) => {
        if (data.status === 'stopped') {
          const text = this.lastPartial;
          this.lastPartial = '';
          if (text) this.onEvent({ type: 'final', text });
        }
      });
    } catch {
      /* listener registration is best-effort */
    }
  }

  /** Start (or restart) listening. Safe to call repeatedly. */
  async start(lang: string, onEvent: (event: SttEvent) => void): Promise<void> {
    this.onEvent = onEvent;
    this.lang = lang || 'en-IN';
    await this.registerListeners();
    if (this.running) return;
    this.running = true;

    try {
      await SpeechRecognition.start({
        language: this.lang,
        maxResults: 5,
        partialResults: true,
        popup: false,
        prompt: 'Say "Hey NEX"…',
      });
      this.onEvent({ type: 'ready' });
    } catch (error) {
      this.running = false;
      this.onEvent({ type: 'error', message: describeSttError(error) });
    }
  }

  async stop(): Promise<void> {
    this.running = false;
    this.lastPartial = '';
    try {
      await SpeechRecognition.stop();
    } catch {
      /* ignore */
    }
  }

  async isListening(): Promise<boolean> {
    try {
      const result = await SpeechRecognition.isListening();
      return !!result.listening;
    } catch {
      return false;
    }
  }

  async destroy(): Promise<void> {
    await this.stop();
    try {
      await SpeechRecognition.removeAllListeners();
    } catch {
      /* ignore */
    }
  }
}

function describeSttError(error: unknown): string {
  const raw = error instanceof Error ? error.message : String(error ?? '');
  const lowered = raw.toLowerCase();
  if (lowered.includes('permission')) {
    return 'Microphone permission is required for NEX to listen.';
  }
  if (lowered.includes('unavailable')) {
    return 'Speech recognition is not available on this device.';
  }
  return raw || 'Speech recognition stopped unexpectedly.';
}

/** Speaks a reply and resolves when Android says the utterance is finished. */
export async function speak(
  text: string,
  lang: string,
  opts: { rate?: number; pitch?: number; onStart?: () => void } = {},
): Promise<{ ok: boolean; error?: string }> {
  const clean = text.replace(/\s+/g, ' ').trim();
  if (!clean) return { ok: true };

  return new Promise((resolve) => {
    let settled = false;
    let handle: { remove: () => Promise<void> } | null = null;

    const finish = async (error?: string) => {
      if (settled) return;
      settled = true;
      if (handle) {
        try {
          await handle.remove();
        } catch {
          /* ignore */
        }
      }
      resolve(error ? { ok: false, error } : { ok: true });
    };

    NexDevice.addListener('speakEnd', () => finish())
      .then(async (h) => {
        handle = h;
        try {
          const result = await NexDevice.speak({
            text: clean,
            lang,
            rate: opts.rate ?? 1.02,
            pitch: opts.pitch ?? 1.08,
          });
          if (!result.queued) {
            finish('Text-to-speech is not available on this device.');
            return;
          }
          opts.onStart?.();
          // Safety net in case the native completion event never arrives.
          const estimate = Math.min(30_000, 1_400 + clean.length * 62);
          setTimeout(() => finish(), estimate);
        } catch (error) {
          finish(error instanceof Error ? error.message : 'Speech failed');
        }
      })
      .catch(() => finish('Speech failed'));
  });
}

export async function stopSpeaking(): Promise<void> {
  try {
    await NexDevice.stopSpeaking();
  } catch {
    /* ignore */
  }
}
