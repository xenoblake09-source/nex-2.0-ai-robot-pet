/**
 * Typed client for the NEX backend.
 *
 * Every failure is converted into a NexApiError whose `kind` tells the UI and
 * the voice exactly what went wrong:
 *   network   -> no internet / server unreachable
 *   backend   -> our server returned an error
 *   gemini    -> Gemini itself failed
 *   permission-> the device refused microphone / camera
 */
import type { ChatReply, ConversationTurn, NexApiError, VisionReply } from '../types';
import { NexApiError as ApiError } from '../types';

const DEFAULT_TIMEOUT = 40_000;

export class NexClient {
  private base: string;

  constructor(base: string) {
    this.base = base.replace(/\/+$/, '');
  }

  setBase(base: string): void {
    this.base = base.replace(/\/+$/, '');
  }

  getBase(): string {
    return this.base;
  }

  private async request<T>(
    path: string,
    init: RequestInit = {},
    timeout = DEFAULT_TIMEOUT,
  ): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    const url = `${this.base}${path}`;
    try {
      const response = await fetch(url, { ...init, signal: controller.signal });
      const text = await response.text();
      let body: unknown = null;
      if (text) {
        try {
          body = JSON.parse(text);
        } catch {
          body = { raw: text };
        }
      }

      if (!response.ok) {
        const payload = (body as { error?: { code?: string; message?: string } } | null)?.error;
        const code = payload?.code ?? `http_${response.status}`;
        const message = payload?.message ?? `Server returned ${response.status}`;
        let kind: NexApiError['kind'] = 'backend';
        if (code.startsWith('gemini')) kind = 'gemini';
        else if (code === 'config_error') kind = 'backend';
        throw new ApiError(message, kind, code, response.status);
      }
      return body as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      const err = error as Error & { name?: string };
      if (err?.name === 'AbortError') {
        throw new ApiError('The request timed out.', 'network', 'timeout');
      }
      throw new ApiError(
        'Cannot reach the NEX server. Check the internet connection and the server address.',
        'network',
        'network_error',
      );
    } finally {
      clearTimeout(timer);
    }
  }

  async health(): Promise<{ status: string; gemini_configured: boolean; model: string }> {
    return this.request('/health', {}, 12_000);
  }

  async chat(
    message: string,
    opts: {
      language?: string;
      history?: ConversationTurn[];
      userName?: string | null;
      sessionId?: string;
      deviceTimezone?: string;
    } = {},
  ): Promise<ChatReply> {
    const body = {
      message,
      language: opts.language ?? 'auto',
      history: opts.history ?? [],
      user_name: opts.userName ?? null,
      session_id: opts.sessionId ?? 'nex-session',
      device_timezone: opts.deviceTimezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone,
      local_time: new Date().toISOString(),
    };
    return this.request<ChatReply>(
      '/api/chat',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
      45_000,
    );
  }

  async vision(
    imageBase64: string,
    question = 'What is this?',
    mimeType = 'image/jpeg',
    language = 'auto',
  ): Promise<VisionReply> {
    const body = { image_base64: imageBase64, question, mime_type: mimeType, language };
    return this.request<VisionReply>(
      '/api/vision',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
      60_000,
    );
  }
}

export const client = new NexClient('');
