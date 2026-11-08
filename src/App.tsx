import { useCallback, useEffect, useRef, useState } from 'react';
import Eye from './eyes/Eye';
import SetupPanel from './components/SetupPanel';
import { useNex } from './hooks/useNex';

export default function App() {
  const nex = useNex();
  const [panelOpen, setPanelOpen] = useState(false);
  const pressTimer = useRef<number | null>(null);
  const longPressed = useRef(false);

  const beginPress = useCallback(() => {
    longPressed.current = false;
    if (pressTimer.current) window.clearTimeout(pressTimer.current);
    pressTimer.current = window.setTimeout(() => {
      longPressed.current = true;
      setPanelOpen(true);
      nex.setShowSetup(true);
    }, 1100);
  }, [nex]);

  const endPress = useCallback(() => {
    if (pressTimer.current) {
      window.clearTimeout(pressTimer.current);
      pressTimer.current = null;
    }
  }, []);

  useEffect(
    () => () => {
      if (pressTimer.current) window.clearTimeout(pressTimer.current);
    },
    [],
  );

  const handleTap = useCallback(() => {
    if (longPressed.current) {
      longPressed.current = false;
      return;
    }
    nex.toggleListening();
  }, [nex]);

  return (
    <div
      className="nex-stage"
      onPointerDown={beginPress}
      onPointerUp={endPress}
      onPointerLeave={endPress}
      onPointerCancel={endPress}
      onClick={handleTap}
    >
      <div className="nex-eyes">
        <Eye index={0} />
        <Eye index={1} />
      </div>

      <SetupPanel
        open={panelOpen || nex.showSetup}
        onClose={() => {
          setPanelOpen(false);
          nex.setShowSetup(false);
        }}
        nex={nex}
      />
    </div>
  );
}
