import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { LiveKitRoom, RoomAudioRenderer, useVoiceAssistant, BarVisualizer, ControlBar } from '@livekit/components-react';
import '@livekit/components-styles';
import './style.css';

type Credentials = { token: string; server_url: string };

function VoicePanel() {
  // The hook follows the active LiveKit agent participant.
  const { state, audioTrack } = useVoiceAssistant();
  return <div className="voice">
    <div className="orb">✦</div>
    <h2>Weye is {state}</h2>
    <p>Speak naturally about your check-in dates, guests, and room preferences.</p>
    {audioTrack && <BarVisualizer state={state} track={audioTrack} barCount={7} />}
    <ControlBar controls={{ microphone: true, camera: false, screenShare: false, leave: false }} />
    <RoomAudioRenderer />
  </div>;
}

function App() {
  const [credentials, setCredentials] = useState<Credentials | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function connect() {
    // Ask our backend for a short-lived, room-scoped LiveKit access token.
    setBusy(true); setError('');
    try {
      const response = await fetch('/api/voice/token', { method: 'POST' });
      if (!response.ok) throw new Error(await response.text());
      setCredentials(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to start session');
    } finally { setBusy(false); }
  }

  return <main><header><span className="brand">✦ Weye AI</span><span className="tag">Hotel reservation prototype</span></header>
    <section className="hero"><h1>Your hotel reservation, just a conversation.</h1>
      <p>Ask about available rooms and complete a demo reservation using your voice.</p>
      {!credentials ? <button disabled={busy} onClick={connect}>{busy ? 'Connecting…' : 'Start voice conversation'}</button> :
        <><LiveKitRoom token={credentials.token} serverUrl={credentials.server_url} connect audio video={false}
          onDisconnected={() => setCredentials(null)} onError={e => setError(e.message)}>
          <VoicePanel />
        </LiveKitRoom>
        <button className="secondary" onClick={() => setCredentials(null)}>End conversation</button></>}
      {error && <p role="alert" className="error">{error}</p>}
    </section><footer>Demo only · No payments · Please use fictional guest information</footer></main>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
