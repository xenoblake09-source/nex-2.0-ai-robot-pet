/**
 * Runtime configuration for the NEX app.
 *
 * The backend URL can be changed at runtime (stored locally) so the same APK
 * can point at a local dev server or a deployed Render instance without a
 * rebuild. The value can also be baked in at build time with
 * VITE_NEX_API_BASE.
 */

const STORAGE_KEY = 'nex.config.v1';

export interface NexConfig {
  apiBase: string;
  wakeWordEnabled: boolean;
  wakeWords: string[];
  sttLanguage: string;
  ttsLanguage: string;
  autoListen: boolean;
  cameraEnabled: boolean;
}

const BUILD_TIME_BASE = (import.meta.env.VITE_NEX_API_BASE || '').trim();

/**
 * In development the app talks to the local backend through the Vite proxy
 * (relative URLs). In a production build it uses the configured host.
 */
export const DEFAULT_API_BASE = import.meta.env.DEV
  ? ''
  : BUILD_TIME_BASE || 'https://nex-ai-robot-pet-api.onrender.com';

const WAKE_WORDS = (import.meta.env.VITE_NEX_WAKE_WORD || 'hey nex')
  .split(',')
  .map((w) => w.trim().toLowerCase())
  .filter(Boolean);

export const DEFAULT_CONFIG: NexConfig = {
  apiBase: DEFAULT_API_BASE,
  wakeWordEnabled: true,
  wakeWords: WAKE_WORDS.length ? WAKE_WORDS : ['hey nex'],
  sttLanguage: 'en-IN',
  ttsLanguage: 'en-US',
  autoListen: true,
  cameraEnabled: true,
};

export function loadConfig(): NexConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_CONFIG };
    const parsed = JSON.parse(raw) as Partial<NexConfig>;
    return { ...DEFAULT_CONFIG, ...parsed };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

export function saveConfig(config: NexConfig): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  } catch {
    /* storage unavailable — keep running with in-memory config */
  }
}

/** Strip a wake word from the beginning of an utterance. */
export function stripWakeWord(text: string, wakeWords: string[]): string {
  let out = text.trim();
  for (const wake of wakeWords) {
    const escaped = wake.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`^\\s*(?:${escaped})[\\s,!?.]*`, 'i');
    out = out.replace(re, '');
  }
  // Common variants people actually say.
  out = out.replace(/^\s*(?:n\s*\.?\s*e\s*\.?\s*x|hey\s+n\s*\.?\s*e\s*\.?\s*x)\b[\s,!?.]*/i, '');
  return out.trim();
}

export function containsWakeWord(text: string, wakeWords: string[]): boolean {
  const lowered = text.toLowerCase();
  if (wakeWords.some((w) => lowered.includes(w))) return true;
  return /\b(?:hey\s+)?n\s*\.?\s*e\s*\.?\s*x\b/i.test(lowered);
}

/**
 * Map the language code returned by the backend to a BCP-47 tag that Android
 * TTS understands. Hinglish is spoken with the Hindi voice.
 */
export function toSpeechLang(language: string | undefined): string {
  if (!language) return 'en-US';
  const lang = language.toLowerCase();
  if (lang === 'hi' || lang === 'hinglish' || lang === 'hindi') return 'hi-IN';
  if (lang === 'en' || lang === 'english') return 'en-US';
  if (lang.includes('-')) return lang;
  const map: Record<string, string> = {
    bn: 'bn-IN',
    ta: 'ta-IN',
    te: 'te-IN',
    mr: 'mr-IN',
    gu: 'gu-IN',
    pa: 'pa-IN',
    ur: 'ur-PK',
    ar: 'ar-SA',
    es: 'es-ES',
    fr: 'fr-FR',
    de: 'de-DE',
    it: 'it-IT',
    pt: 'pt-BR',
    ru: 'ru-RU',
    zh: 'zh-CN',
    ja: 'ja-JP',
    ko: 'ko-KR',
    id: 'id-ID',
    ms: 'ms-MY',
    tr: 'tr-TR',
    nl: 'nl-NL',
    pl: 'pl-PL',
    sv: 'sv-SE',
    th: 'th-TH',
    vi: 'vi-VN',
  };
  return map[lang] ?? 'en-US';
}

/** Map a BCP-47 tag to the locale Android's speech recogniser prefers. */
export function toSttLang(tag: string): string {
  if (!tag) return 'en-IN';
  if (tag === 'hi-IN') return 'hi-IN';
  if (tag.startsWith('en')) return 'en-IN';
  return tag;
}
