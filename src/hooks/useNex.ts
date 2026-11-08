import { useCallback, useEffect, useRef, useState } from 'react';
import { eyeEngine } from '../eyes/engine';
import { ERROR_EXPRESSIONS } from '../eyes/expressions';
import { client } from '../lib/api';
import {
  containsWakeWord,
  loadConfig,
  saveConfig,
  stripWakeWord,
  toSpeechLang,
  toSttLang,
  type NexConfig,
} from '../lib/config';
import { NexDevice } from '../lib/native';
import { playAnimalSound, playUiSound, unlockAudio } from '../lib/sounds';
import { SpeechInput, speak, stopSpeaking } from '../lib/speech';
import { NexApiError, type ConversationTurn, type ExpressionName, type NexStatus } from '../types';

const CAMERA_INTENT =
  /\b(what(?:'s| is| was) (?:this|that)|kya hai (?:ye|yeh|yah)|ye(?:h)? kya hai|identify this|describe (?:this|that)|dekh ke batao|kya object hai|naam batao|what do you see)\b/i;

export interface NexError {
  kind: 'network' | 'backend' | 'gemini' | 'permission' | 'unknown';
  message: string;
}

export interface NexApi {
  status: NexStatus;
  expression: ExpressionName;
  serverOnline: boolean | null;
  error: NexError | null;
  config: NexConfig;
  showSetup: boolean;
  facePresent: boolean | null;
  micGranted: boolean;
  updateConfig: (patch: Partial<NexConfig>) => void;
  setShowSetup: (value: boolean) => void;
  toggleListening: () => void;
  requestMicPermission: () => Promise<boolean>;
  requestCameraPermission: () => Promise<boolean>;
  testConnection: () => Promise<boolean>;
  resetSession: () => void;
}

export function useNex(): NexApi {
  const [status, setStatus] = useState<NexStatus>('boot');
  const [expression, setExpression] = useState<ExpressionName>('neutral');
  const [serverOnline, setServerOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<NexError | null>(null);
  const [config, setConfig] = useState<NexConfig>(() => loadConfig());
  const [showSetup, setShowSetup] = useState(false);
  const [facePresent, setFacePresent] = useState<boolean | null>(null);
  const [micGranted, setMicGranted] = useState(false);

  const configRef = useRef(config);
  configRef.current = config;

  const sttRef = useRef<SpeechInput>(new SpeechInput());
  const busyRef = useRef(false);
  const stoppedRef = useRef(false);
  const awakeRef = useRef(false);
  const historyRef = useRef<ConversationTurn[]>([]);
  const sessionIdRef = useRef(`nex-${Math.random().toString(36).slice(2, 10)}`);
  const setupShownRef = useRef(false);

  // ---------------------------------------------------------------- utils
  const applyExpression = useCallback((name: ExpressionName | string) => {
    eyeEngine.setExpression(name);
    setExpression(name as ExpressionName);
  }, []);

  const updateConfig = useCallback((patch: Partial<NexConfig>) => {
    setConfig((prev) => {
      const next = { ...prev, ...patch };
      saveConfig(next);
      client.setBase(next.apiBase);
      return next;
    });
  }, []);

  // --------------------------------------------------------------- speech
  const say = useCallback(async (text: string, lang = 'en-US') => {
    await stopSpeaking();
    return speak(text, lang);
  }, []);

  const reportError = useCallback(
    async (err: unknown) => {
      const kind: NexError['kind'] = err instanceof NexApiError ? err.kind : 'unknown';
      const message =
        err instanceof NexApiError
          ? err.message
          : 'Something unexpected happened. Let us try that again.';
      setError({ kind, message });
      applyExpression(ERROR_EXPRESSIONS[kind] ?? 'confused');
      await playUiSound('error');
      await say(message, toSpeechLang(configRef.current.ttsLanguage));
    },
    [applyExpression, say],
  );

  // ---------------------------------------------------------------- camera
  const handleVision = useCallback(async () => {
    busyRef.current = true;
    setStatus('thinking');
    applyExpression('curious');
    try {
      const granted = await NexDevice.requestCameraPermission();
      if (!granted) {
        busyRef.current = false;
        setStatus('idle');
        await reportError(
          new NexApiError(
            'I need camera permission to see what you are pointing at.',
            'permission',
            'camera_permission',
          ),
        );
        return;
      }
      const shot = await NexDevice.capturePhoto({ quality: 72, front: true });
      if (!shot?.base64) {
        throw new NexApiError('The camera did not return a photo.', 'permission', 'camera_failed');
      }
      const reply = await client.vision(
        shot.base64,
        'What is this?',
        shot.mimeType ?? 'image/jpeg',
      );
      applyExpression(reply.expression ?? 'curious');
      setStatus('speaking');
      await say(reply.reply, toSpeechLang(reply.language ?? 'en'));
    } catch (err) {
      await reportError(err);
    } finally {
      busyRef.current = false;
      setStatus('idle');
      setTimeout(() => void startListeningRef.current?.(), 300);
    }
  }, [applyExpression, reportError, say]);

  // --------------------------------------------------------------- chatting
  const processCommand = useCallback(
    async (rawText: string) => {
      const text = rawText.trim();
      if (!text) return;

      if (CAMERA_INTENT.test(text)) {
        await handleVision();
        return;
      }

      busyRef.current = true;
      setStatus('thinking');
      applyExpression('thinking');

      try {
        const result = await client.chat(text, {
          language: 'auto',
          history: historyRef.current.slice(-8),
          userName: null,
          sessionId: sessionIdRef.current,
        });

        historyRef.current.push({ role: 'user', content: text });
        historyRef.current.push({ role: 'nex', content: result.reply });
        if (historyRef.current.length > 16) {
          historyRef.current = historyRef.current.slice(-16);
        }

        setError(null);

        // --- animal sound -------------------------------------------
        if (result.action?.type === 'animal_sound' && result.action.animal) {
          setStatus('playing_sound');
          applyExpression('excited');
          const sound = await playAnimalSound(result.action.animal);
          if (!sound.ok) {
            await say(
              `I could not play the ${result.action.animal} sound on this device.`,
              toSpeechLang(result.language),
            );
          }
        }

        // --- expression ---------------------------------------------
        const replyExpression = (result.expression ?? 'happy') as ExpressionName;
        const isDance = replyExpression === 'dance' || result.action?.type === 'dance';
        applyExpression(isDance ? 'dance' : replyExpression);

        setStatus('speaking');
        await say(result.reply, toSpeechLang(result.language));

        if (isDance) {
          applyExpression('excited');
          setTimeout(() => applyExpression('neutral'), 600);
        }
      } catch (err) {
        await reportError(err);
      } finally {
        busyRef.current = false;
        setStatus('idle');
        setTimeout(() => void startListeningRef.current?.(), 300);
      }
    },
    [applyExpression, handleVision, reportError, say],
  );

  // ------------------------------------------------------------- listening
  const onSttEvent = useCallback(
    async (event: { type: string; text?: string; message?: string }) => {
      if (event.type === 'error') {
        const message = event.message ?? 'Microphone error.';
        if (/permission/i.test(message)) {
          setMicGranted(false);
          setError({ kind: 'permission', message });
          applyExpression('angry');
          if (!setupShownRef.current) {
            setupShownRef.current = true;
            setShowSetup(true);
          }
        }
        return;
      }

      if (event.type === 'ready') {
        setMicGranted(true);
        if (!busyRef.current) applyExpression('listening');
        return;
      }

      if (event.type === 'partial' && event.text) {
        const hasWake = containsWakeWord(event.text, configRef.current.wakeWords);
        if (hasWake && !awakeRef.current) {
          awakeRef.current = true;
          applyExpression('surprised');
        } else if (!hasWake && !busyRef.current) {
          applyExpression('listening');
        }
        return;
      }

      if (event.type === 'final' && event.text) {
        const text = event.text.trim();
        const hasWake = containsWakeWord(text, configRef.current.wakeWords);
        awakeRef.current = false;
        if (busyRef.current) return;

        if (configRef.current.wakeWordEnabled && !hasWake) {
          // Not addressed to NEX — quietly go back to listening.
          applyExpression('curious');
          setTimeout(() => {
            if (!busyRef.current) applyExpression('listening');
          }, 650);
          return;
        }

        const command = stripWakeWord(text, configRef.current.wakeWords);
        if (!command) {
          busyRef.current = true;
          applyExpression('happy');
          await say(
            'I am here! What can I do for you?',
            toSpeechLang(configRef.current.ttsLanguage),
          );
          busyRef.current = false;
          applyExpression('listening');
          return;
        }
        void processCommand(command);
      }
    },
    [applyExpression, processCommand, say],
  );

  const startListening = useCallback(async () => {
    if (busyRef.current || stoppedRef.current) return;
    const cfg = configRef.current;
    if (!cfg.autoListen && !awakeRef.current) return;
    try {
      await sttRef.current.start(toSttLang(cfg.sttLanguage), onSttEvent);
    } catch {
      /* handled by the error event */
    }
  }, [onSttEvent]);

  const startListeningRef = useRef<(() => Promise<void>) | null>(null);
  startListeningRef.current = startListening;

  const stopListening = useCallback(async () => {
    await sttRef.current.stop();
  }, []);

  const toggleListening = useCallback(() => {
    unlockAudio();
    if (busyRef.current) return;
    if (status === 'listening' || status === 'idle') {
      void stopListening();
      applyExpression('neutral');
      setStatus('idle');
      setTimeout(() => void startListeningRef.current?.(), 1200);
    } else {
      void startListeningRef.current?.();
    }
  }, [applyExpression, status, stopListening]);

  // -------------------------------------------------------------- watchdog
  useEffect(() => {
    const id = window.setInterval(async () => {
      if (stoppedRef.current) return;
      if (busyRef.current) return;
      if (!configRef.current.autoListen) return;
      const listening = await sttRef.current.isListening();
      if (!listening) {
        await startListeningRef.current?.();
      }
    }, 1500);
    return () => window.clearInterval(id);
  }, []);

  // ------------------------------------------------------------- boot flow
  const checkServer = useCallback(async (): Promise<boolean> => {
    try {
      const health = await client.health();
      setServerOnline(true);
      return !!health.status;
    } catch {
      setServerOnline(false);
      return false;
    }
  }, []);

  const requestMicPermission = useCallback(async (): Promise<boolean> => {
    const granted = await sttRef.current.requestPermission();
    setMicGranted(granted);
    if (granted) {
      setError(null);
      applyExpression('happy');
      await startListeningRef.current?.();
    } else {
      applyExpression('sad');
      setError({
        kind: 'permission',
        message: 'Microphone permission is required for NEX to listen to you.',
      });
    }
    return granted;
  }, [applyExpression]);

  const requestCameraPermission = useCallback(async (): Promise<boolean> => {
    const result = await NexDevice.requestCameraPermission();
    return !!result?.granted;
  }, []);

  const testConnection = useCallback(async (): Promise<boolean> => {
    applyExpression('thinking');
    const ok = await checkServer();
    applyExpression(ok ? 'happy' : 'sad');
    return ok;
  }, [applyExpression, checkServer]);

  const resetSession = useCallback(() => {
    historyRef.current = [];
    sessionIdRef.current = `nex-${Math.random().toString(36).slice(2, 10)}`;
  }, []);

  useEffect(() => {
    stoppedRef.current = false;
    client.setBase(configRef.current.apiBase);
    eyeEngine.start();

    let cancelled = false;

    (async () => {
      const online = await checkServer();
      if (cancelled) return;

      const granted = await sttRef.current.hasPermission();
      if (!granted) {
        const requested = await sttRef.current.requestPermission();
        setMicGranted(requested);
      } else {
        setMicGranted(true);
      }

      if (!online) {
        applyExpression('sad');
        setError({
          kind: 'network',
          message:
            'I cannot reach my server yet. Open setup to check the server address.',
        });
        if (!setupShownRef.current) {
          setupShownRef.current = true;
          setShowSetup(true);
        }
      } else {
        applyExpression('happy');
        await say(
          'Hi! I am NEX, your AI robot pet. Say "Hey NEX" and talk to me!',
          toSpeechLang(configRef.current.ttsLanguage),
        );
        applyExpression('listening');
      }

      await startListeningRef.current?.();
    })();

    return () => {
      cancelled = true;
      stoppedRef.current = true;
      void sttRef.current.destroy();
      void stopSpeaking();
      eyeEngine.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ------------------------------------------------------------ face track
  useEffect(() => {
    let handle: { remove: () => Promise<void> } | null = null;
    NexDevice.addListener('faceStatus', (event) => {
      const present = 'present' in event ? !!event.present : false;
      setFacePresent(present);
      if (!busyRef.current) {
        applyExpression(present ? 'happy' : 'curious');
      }
    })
      .then((h) => {
        handle = h;
      })
      .catch(() => undefined);

    return () => {
      if (handle) void handle.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    status,
    expression,
    serverOnline,
    error,
    config,
    showSetup,
    facePresent,
    micGranted,
    updateConfig,
    setShowSetup,
    toggleListening,
    requestMicPermission,
    requestCameraPermission,
    testConnection,
    resetSession,
  };
}
