import { useEffect, useState } from "react";
import { useBearer } from "../auth/BearerContext";
import { forgetKeys } from "../lib/crypto";

export function SettingsView(): JSX.Element {
  const { credential, signOut } = useBearer();
  
  // Phase 6.4 Cost Preview + Consent Toggles
  const [visualConsent, setVisualConsent] = useState(true);
  const [vitalsConsent, setVitalsConsent] = useState(true);
  const [voiceConsent, setVoiceConsent] = useState(true);
  const [memoryConsent, setMemoryConsent] = useState(true);

  const [pricing, setPricing] = useState<any>(null);

  useEffect(() => {
    // Fetch pricing and consent on mount
    fetch("/pricing")
      .then((r) => r.json())
      .then(setPricing)
      .catch(console.error);

    if (credential) {
      fetch("/memory/consent", {
        headers: { Authorization: `Bearer ${credential.token}` }
      })
        .then((r) => r.json())
        .then((data) => {
          setVisualConsent(data.visual);
          setVitalsConsent(data.vitals);
          setVoiceConsent(data.voice);
          setMemoryConsent(data.memory);
        })
        .catch(console.error);
    }
  }, [credential]);

  const updateConsent = async (updates: any) => {
    if (!credential) return;
    const body = {
      visual: visualConsent,
      vitals: vitalsConsent,
      voice: voiceConsent,
      memory: memoryConsent,
      ...updates
    };
    
    // Optimistic UI update
    if ("visual" in updates) setVisualConsent(updates.visual);
    if ("vitals" in updates) setVitalsConsent(updates.vitals);
    if ("voice" in updates) setVoiceConsent(updates.voice);
    if ("memory" in updates) setMemoryConsent(updates.memory);

    try {
      await fetch("/memory/consent", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          Authorization: `Bearer ${credential.token}` 
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
  if (visualConsent) totalCost += pricing?.modality_costs?.visual || 0;
  if (vitalsConsent) totalCost += pricing?.modality_costs?.vitals || 0;
  if (voiceConsent) totalCost += pricing?.modality_costs?.voice || 0;

  return (
    <div className="xion-view xion-view--settings">
      <h2 className="xion-h2">Settings & Consent</h2>
      
      <section className="xion-section">
        <h3>Modality Consent</h3>
        <p>Control what data streams are active during interaction. Changing these affects your privacy and your per-turn cost.</p>
        
        <div className="xion-toggles">
          <label>
            <input type="checkbox" checked={visualConsent} onChange={(e) => updateConsent({visual: e.target.checked})} />
            Visual Presence (Scene Intent)
          </label>
          <br/>
          <label>
            <input type="checkbox" checked={vitalsConsent} onChange={(e) => updateConsent({vitals: e.target.checked})} />
            Vital Signs (Structural Health)
          </label>
          <br/>
          <label>
            <input type="checkbox" checked={voiceConsent} onChange={(e) => updateConsent({voice: e.target.checked})} />
            Voice Form (Audible Output)
          </label>
          <br/>
          <label>
            <input type="checkbox" checked={memoryConsent} onChange={(e) => updateConsent({memory: e.target.checked})} />
            Memory Retention
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
