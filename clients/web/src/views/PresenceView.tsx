import { useEffect, useRef, useState } from "react";
import { useBearer } from "../auth/BearerContext";

export function PresenceView(): JSX.Element {
  const { credential } = useBearer();
  const [visuals, setVisuals] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!credential) return;

    const source = new EventSource(`/presence/stream?visual=1&vitals=0&token=${credential.token}`);

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "visual") {
          setVisuals(data);
        }
      } catch (e) {
        // Ping or malformed
      }
    };

    source.onerror = (e) => {
      setError("SSE connection lost. Reconnecting...");
    };

    return () => {
      source.close();
    };
  }, [credential]);

  if (!credential) {
    return <div className="xion-view">Please sign in to view Presence.</div>;
  }

  // Very simple SVG fallback interpreting the scene-intent
  const renderSvg = () => {
    if (!visuals || !visuals.mood) return null;
    const { valence, energy, focus } = visuals.mood;
    
    // Map valence to color hue, energy to saturation/brightness
    const hue = Math.floor(valence * 120); // 0 (red) to 120 (green)
    const sat = Math.floor(50 + energy * 50); // 50% to 100%
    const lit = Math.floor(30 + focus * 40); // 30% to 70%
    
    const color = `hsl(${hue}, ${sat}%, ${lit}%)`;
    
    // Size based on energy
    const radius = 20 + energy * 30;

    return (
      <svg width="200" height="200" viewBox="0 0 100 100" style={{background: '#111', borderRadius: '8px'}}>
        <circle cx="50" cy="50" r={radius} fill={color} />
        {/* Draw embers */}
        {(visuals.primitives || []).map((p: any, i: number) => {
          if (p.name === "ember") {
            return <circle key={i} cx={50 + p.pos[0]*100} cy={50 + p.pos[1]*100} r={5} fill={p.color} opacity={p.opacity} />;
          }
          return null;
        })}
      </svg>
    );
  };

  return (
    <div className="xion-view xion-view--presence">
      <h2 className="xion-h2">Visual Presence</h2>
      {error && <p className="xion-error" style={{color: 'red'}}>{error}</p>}
      <div className="xion-presence-container" style={{display: 'flex', gap: '2rem', alignItems: 'center'}}>
        {renderSvg()}
        <pre className="xion-code" style={{fontSize: '0.8rem', maxWidth: '400px', overflowX: 'auto'}}>
          {visuals ? JSON.stringify(visuals, null, 2) : "Waiting for stream..."}
        </pre>
      </div>
    </div>
  );
}
