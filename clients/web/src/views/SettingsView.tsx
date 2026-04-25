import { useEffect, useState } from "react";
import { useBearer, buildAuthorizationHeader } from "../auth/BearerContext";
import { forgetKeys } from "../lib/crypto";

export function SettingsView(): JSX.Element {
  const { credential, signOut } = useBearer();
  
  // Phase 6.4 Cost Preview + Consent Toggles
  const [streamVisual, setStreamVisual] = useState(false);
  const [streamVitals, setStreamVitals] = useState(false);
  const [streamVoice, setStreamVoice] = useState(false);
  const [streamMemory, setStreamMemory] = useState(true);

  const [pricing, setPricing] = useState<any>(null);

  // Per-session overrides
  const [overrideVisual, setOverrideVisual] = useState(true);
  const [overrideVitals, setOverrideVitals] = useState(true);

  useEffect(() => {
    // Fetch pricing and consent on mount
    fetch("/pricing")
      .then((r) => r.json())
      .then(setPricing)
      .catch(console.error);

    if (credential) {
      fetch("/memory/consent", {
        headers: buildAuthorizationHeader(credential)
      })
        .then((r) => r.json())
        .then((data) => {
          setStreamVisual(data.stream_visual);
          setStreamVitals(data.stream_vitals);
          setStreamVoice(data.stream_voice);
          setStreamMemory(data.stream_memory);
        })
        .catch(console.error);
    }
  }, [credential]);

  const updateConsent = async (updates: any) => {
    if (!credential) return;
    const body = {
      stream_visual: streamVisual,
      stream_vitals: streamVitals,
      stream_voice: streamVoice,
      stream_memory: streamMemory,
      ...updates
    };
    
    // Optimistic UI update
    if ("stream_visual" in updates) setStreamVisual(updates.stream_visual);
    if ("stream_vitals" in updates) setStreamVitals(updates.stream_vitals);
    if ("stream_voice" in updates) setStreamVoice(updates.stream_voice);
    if ("stream_memory" in updates) setStreamMemory(updates.stream_memory);

    try {
      await fetch("/memory/consent", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          ...buildAuthorizationHeader(credential)
        },
        body: JSON.stringify(body)
      });
    } catch (e) {
      console.error("Failed to save consent", e);
    }
  };

  const handleForgetKeys = async () => {
    await forgetKeys();
    alert("Local Ed25519 keys wiped. Please sign out and sign in to generate new keys. Note: other open tabs will need a reload (KW-PROOF-002).");
  };

  let totalCost = pricing?.per_message_price_micro_XION || 0;
  if (streamVisual) totalCost += pricing?.modality_costs?.stream_visual || 0;
  if (streamVitals) totalCost += pricing?.modality_costs?.stream_vitals || 0;
  if (streamVoice) totalCost += pricing?.modality_costs?.stream_voice || 0;

  return (
    <div className="xion-view xion-view--settings">
      <h2 className="xion-h2">Settings & Consent</h2>
      
      <section className="xion-section">
        <h3>Modality Consent</h3>
        <p>Control what data streams are active during interaction. Changing these affects your privacy and your per-turn cost.</p>
        
        <div className="xion-toggles">
          <label>
            <input type="checkbox" checked={streamVisual} onChange={(e) => updateConsent({stream_visual: e.target.checked})} />
            Visual Presence (Scene Intent)
          </label>
          <br/>
          <label>
            <input type="checkbox" checked={streamVitals} onChange={(e) => updateConsent({stream_vitals: e.target.checked})} />
            Vital Signs (Structural Health)
          </label>
          <br/>
          <label>
            <input type="checkbox" checked={streamVoice} onChange={(e) => updateConsent({stream_voice: e.target.checked})} />
            Voice Form (Audible Output)
          </label>
          <br/>
          <label>
            <input type="checkbox" checked={streamMemory} onChange={(e) => updateConsent({stream_memory: e.target.checked})} />
            Memory Retention
          </label>
        </div>
      </section>

      <section className="xion-section" style={{marginTop: '2rem'}}>
        <h3>Per-Session Overrides</h3>
        <p>Temporarily dim active streams for this tab without changing your global consent posture.</p>
        <div className="xion-toggles">
          <label>
            <input type="checkbox" checked={overrideVisual} onChange={(e) => {
              setOverrideVisual(e.target.checked);
              window.dispatchEvent(new CustomEvent('xion:override', { detail: { visual: e.target.checked, vitals: overrideVitals } }));
            }} disabled={!streamVisual} />
            Visual Presence (Override)
          </label>
          <br/>
          <label>
            <input type="checkbox" checked={overrideVitals} onChange={(e) => {
              setOverrideVitals(e.target.checked);
              window.dispatchEvent(new CustomEvent('xion:override', { detail: { visual: overrideVisual, vitals: e.target.checked } }));
            }} disabled={!streamVitals} />
            Vital Signs (Override)
          </label>
        </div>
      </section>

      <section className="xion-section" style={{marginTop: '2rem'}}>
        <h3>Cost Preview</h3>
        {pricing ? (
          <p>
            Base Cost: {pricing.per_message_price_micro_XION} micro-XION<br/>
            Current Configuration Total: <strong>{totalCost} micro-XION / turn</strong>
          </p>
        ) : (
          <p>Loading pricing...</p>
        )}
      </section>

      <section className="xion-section" style={{marginTop: '2rem', borderTop: '1px solid #ccc', paddingTop: '1rem'}}>
        <h3>Client Cryptography</h3>
        <p>Xion requires client-side Ed25519 proofs for accountability. Your private key never leaves this device.</p>
        <button type="button" className="xion-button xion-button--danger" onClick={handleForgetKeys}>
          Forget my keys
        </button>
      </section>
    </div>
  );
}
