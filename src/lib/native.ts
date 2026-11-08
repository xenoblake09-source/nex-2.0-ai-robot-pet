/**
 * Bridge to the native Android helper plugin (`NexDevice`).
 *
 * The native plugin provides:
 *   - Android TextToSpeech with a real "speech finished" event (so NEX knows
 *     exactly when to re-arm the microphone)
 *   - Front-camera single-shot capture (CameraX) returning a base64 JPEG
 *   - On-device face detection (ML Kit bundled model) with live status events
 *
 * A fully functional web fallback is provided so the same build can be previewed
 * in a desktop browser (Web SpeechSynthesis + getUserMedia).
 */
import { Capacitor, registerPlugin, type PluginListenerHandle } from '@capacitor/core';

export interface SpeakOptions {
  text: string;
  lang?: string;
  rate?: number;
  pitch?: number;
}

export interface SpeakEndEvent {
  utteranceId: string;
  error?: boolean;
}

export interface FaceStatusEvent {
  present: boolean;
  count: number;
}

export interface NexDevicePlugin {
  speak(options: SpeakOptions): Promise<{ queued: boolean; error?: string }>;
  stopSpeaking(): Promise<void>;
  isSpeaking(): Promise<{ speaking: boolean }>;
  capturePhoto(options?: { quality?: number; front?: boolean }): Promise<{
    base64: string;
    mimeType: string;
  }>;
  hasCamera(): Promise<{ available: boolean }>;
  requestCameraPermission(): Promise<{ granted: boolean }>;
  startFaceTracking(): Promise<{ started: boolean }>;
  stopFaceTracking(): Promise<void>;
  addListener(
    eventName: 'speakEnd' | 'faceStatus',
    listener: (data: SpeakEndEvent | FaceStatusEvent) => void,
  ): Promise<PluginListenerHandle>;
  removeAllListeners(): Promise<void>;
}

class WebNexDevice implements NexDevicePlugin {
  private speaking = false;
  private mediaStream: MediaStream | null = null;
  private listeners: Record<string, ((data: unknown) => void)[]> = {};

  async speak(options: SpeakOptions): Promise<{ queued: boolean }> {
    if (!('speechSynthesis' in window)) return { queued: false };
    const synth = window.speechSynthesis;
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(options.text);
    utterance.lang = options.lang ?? 'en-US';
    utterance.rate = options.rate ?? 1;
    utterance.pitch = options.pitch ?? 1.05;
    utterance.onend = () => {
      this.speaking = false;
      this.emit('speakEnd', { utteranceId: 'web' });
    };
    utterance.onerror = () => {
      this.speaking = false;
      this.emit('speakEnd', { utteranceId: 'web', error: true });
    };
    this.speaking = true;
    synth.speak(utterance);
    return { queued: true };
  }

  async stopSpeaking(): Promise<void> {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    this.speaking = false;
  }

  async isSpeaking(): Promise<{ speaking: boolean }> {
    return { speaking: this.speaking };
  }

  async hasCamera(): Promise<{ available: boolean }> {
    return { available: !!navigator.mediaDevices?.getUserMedia };
  }

  async requestCameraPermission(): Promise<{ granted: boolean }> {
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
      return { granted: true };
    } catch {
      return { granted: false };
    }
  }

  async capturePhoto(): Promise<{ base64: string; mimeType: string }> {
    const stream = this.mediaStream ?? (await navigator.mediaDevices.getUserMedia({ video: true }));
    this.mediaStream = stream;
    const video = document.createElement('video');
    video.srcObject = stream;
    video.muted = true;
    await video.play();
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext('2d')!.drawImage(video, 0, 0, canvas.width, canvas.height);
    video.pause();
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
    return { base64: dataUrl.split(',')[1] ?? '', mimeType: 'image/jpeg' };
  }

  async startFaceTracking(): Promise<{ started: boolean }> {
    return { started: false };
  }

  async stopFaceTracking(): Promise<void> {
    /* not supported on web */
  }

  async addListener(
    eventName: 'speakEnd' | 'faceStatus',
    listener: (data: SpeakEndEvent | FaceStatusEvent) => void,
  ): Promise<PluginListenerHandle> {
    this.listeners[eventName] = this.listeners[eventName] ?? [];
    this.listeners[eventName].push(listener as (data: unknown) => void);
    return {
      remove: async () => {
        this.listeners[eventName] = (this.listeners[eventName] ?? []).filter(
          (l) => l !== (listener as unknown),
        );
      },
    };
  }

  async removeAllListeners(): Promise<void> {
    this.listeners = {};
  }

  private emit(eventName: string, data: unknown): void {
    (this.listeners[eventName] ?? []).forEach((l) => l(data));
  }
}

export const NexDevice = registerPlugin<NexDevicePlugin>('NexDevice', {
  web: () => new WebNexDevice(),
});

export const isNativePlatform = Capacitor.isNativePlatform();
export const platformName = Capacitor.getPlatform();
