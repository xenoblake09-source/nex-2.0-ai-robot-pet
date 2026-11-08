import { useEffect, useState } from 'react';
import type { NexApi } from '../hooks/useNex';

interface SetupPanelProps {
  open: boolean;
  onClose: () => void;
  nex: NexApi;
}

/**
 * Hidden setup panel (long-press the face to open).
 *
 * The main screen stays pure black with only two eyes — this panel is the
 * escape hatch for pointing NEX at a different backend or fixing permissions.
 */
export default function SetupPanel({ open, onClose, nex }: SetupPanelProps) {
  const [url, setUrl] = useState(nex.config.apiBase);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (open) setUrl(nex.config.apiBase);
  }, [open, nex.config.apiBase]);

  if (!open) return null;

  const applyUrl = async () => {
    setBusy(true);
    setMessage('');
    nex.updateConfig({ apiBase: url.trim() });
    const ok = await nex.testConnection();
    setMessage(ok ? 'Connected — NEX is online.' : 'Could not reach that server.');
    setBusy(false);
  };

  return (
    <div className="nex-panel-backdrop" onClick={onClose}>
      <div className="nex-panel" onClick={(event) => event.stopPropagation()}>
        <h2>NEX setup</h2>

        <label className="nex-field">
          <span>Server address</span>
          <input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://your-nex-api.onrender.com"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
          />
        </label>

        <div className="nex-row">
          <button className="nex-button" onClick={applyUrl} disabled={busy}>
            {busy ? 'Testing…' : 'Test & save'}
          </button>
          <button
            className="nex-button ghost"
            onClick={async () => {
              const granted = await nex.requestMicPermission();
              setMessage(granted ? 'Microphone ready.' : 'Microphone permission denied.');
            }}
          >
            Microphone
          </button>
          <button
            className="nex-button ghost"
            onClick={async () => {
              const granted = await nex.requestCameraPermission();
              setMessage(granted ? 'Camera ready.' : 'Camera permission denied.');
            }}
          >
            Camera
          </button>
        </div>

        <div className="nex-toggles">
          <label className="nex-toggle">
            <input
              type="checkbox"
              checked={nex.config.wakeWordEnabled}
              onChange={(event) => nex.updateConfig({ wakeWordEnabled: event.target.checked })}
            />
            <span>Require wake word (“Hey NEX”)</span>
          </label>
          <label className="nex-toggle">
            <input
              type="checkbox"
              checked={nex.config.autoListen}
              onChange={(event) => nex.updateConfig({ autoListen: event.target.checked })}
            />
            <span>Always listen (hands-free)</span>
          </label>
        </div>

        <div className="nex-status">
          <span className={`dot ${nex.serverOnline ? 'ok' : 'bad'}`} />
          Server {nex.serverOnline ? 'online' : 'offline'} · mic{' '}
          {nex.micGranted ? 'granted' : 'not granted'}
        </div>

        {message ? <div className="nex-message">{message}</div> : null}
        {nex.error ? <div className="nex-message error">{nex.error.message}</div> : null}

        <div className="nex-row">
          <button className="nex-button ghost" onClick={nex.resetSession}>
            New conversation
          </button>
          <button className="nex-button" onClick={onClose}>
            Close
          </button>
        </div>

        <p className="nex-hint">
          Long-press the eyes to reopen this panel · tap the eyes to start or stop listening.
        </p>
      </div>
    </div>
  );
}
