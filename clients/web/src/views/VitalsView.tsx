import { useEffect, useState } from "react";
import { useBearer } from "../auth/BearerContext";

export function VitalsView(): JSX.Element {
  const { credential } = useBearer();
  const [vitals, setVitals] = useState<any[]>([]);
  const [modalHash, setModalHash] = useState<string | null>(null);

  useEffect(() => {
    if (!credential) return;

    // We can fetch initial state or just use the stream
    const source = new EventSource(`/presence/stream?visual=0&vitals=1&token=${credential.token}`);

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "vitals") {
          setVitals(data.vitals);
        }
      } catch (e) {
        // Ping
      }
    };

    return () => {
      source.close();
    };
  }, [credential]);

  if (!credential) {
    return <div className="xion-view">Please sign in to view Vitals.</div>;
  }

  const bandColors: Record<string, string> = {
    healthy: 'green',
    warning: 'orange',
    critical: 'red'
  };

  return (
    <div className="xion-view xion-view--vitals">
      <h2 className="xion-h2">Vital Signs (8 Domains)</h2>
      <p>Tracking the structural health of the intelligence.</p>
      
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem'}}>
        {vitals.map((v, i) => (
          <div key={i} style={{border: `2px solid ${bandColors[v.band] || 'gray'}`, padding: '1rem', borderRadius: '4px'}}>
            <h4>{v.domain}</h4>
            <p>Reading: {v.reading}</p>
            <p style={{color: bandColors[v.band], fontWeight: 'bold'}}>{v.band.toUpperCase()}</p>
            <button 
              type="button" 
              className="xion-button xion-button--ghost"
              onClick={() => setModalHash(v.methodology_sha256)}
              aria-label={`View methodology hash for ${v.domain}`}
            >
              Methodology Hash
            </button>
          </div>
        ))}
        {vitals.length === 0 && <p>Waiting for vitals stream...</p>}
      </div>

      {modalHash && (
        <div style={{position: 'fixed', top: '20%', left: '50%', transform: 'translate(-50%, 0)', background: 'white', border: '1px solid black', padding: '2rem', zIndex: 100}}>
          <h3>Methodology SHA-256</h3>
          <code>{modalHash}</code>
          <br/><br/>
          <button type="button" onClick={() => setModalHash(null)} className="xion-button">Close</button>
        </div>
      )}
    </div>
  );
}
