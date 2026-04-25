import { useEffect, useState } from "react";
import { useBearer } from "../auth/BearerContext";
import { subscribePresenceStream } from "../lib/api";

export function VitalsView(): JSX.Element {
  const { credential } = useBearer();
  const [vitals, setVitals] = useState<any[]>([]);
  const [modalHash, setModalHash] = useState<string | null>(null);

  useEffect(() => {
    if (!credential) return;

    const controller = new AbortController();
    
    let currentVitalsOverride = true;

    const handleOverride = (e: any) => {
      currentVitalsOverride = e.detail.vitals;
      controller.abort();
    };

    window.addEventListener('xion:override', handleOverride);

    async function connect() {
      try {
        const stream = subscribePresenceStream({
          credential,
          visual: false,
          vitals: currentVitalsOverride,
          signal: controller.signal
        });

        for await (const data of stream) {
          if (data.type === "vitals") {
            setVitals(data.vitals);
          }
        }
      } catch (e: any) {
        if (e.name !== 'AbortError') {
          setTimeout(connect, 2000);
        }
      }
    }

    connect();

    return () => {
      controller.abort();
      window.removeEventListener('xion:override', handleOverride);
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
