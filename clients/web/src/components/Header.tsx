import { useCallback, useEffect, useState } from "react";

import { useBearer } from "../auth/BearerContext";
import {
  ApiErrorException,
  getHealth,
  type HealthResponse,
} from "../lib/api";

// Header: the constant chrome at the top of the app. Hosts:
//   - the view switcher (Chat / Drive / Sensorium)
//   - the sign-in / sign-out affordance
//   - the Relay health dot (polls /health every 10s; /health is
//     public-unauthenticated per the 5g-iv admission surface)
//
// Doctrine: docs/31-WEB-CLIENT.md § "Properties" P3 (accessibility);
// nav is keyboard-reachable with visible focus, the health dot is
// aria-described so screen readers report the current state.

export type ViewId = "chat" | "drive" | "sensorium";

export interface HeaderProps {
  current: ViewId;
  onNavigate: (view: ViewId) => void;
}

const HEALTH_POLL_MS = 10_000;

type HealthState =
  | { kind: "unknown" }
  | { kind: "ok"; health: HealthResponse }
  | { kind: "degraded"; reason: string };

function HealthDot({ state }: { state: HealthState }): JSX.Element {
  const label =
    state.kind === "unknown"
      ? "Relay health unknown"
      : state.kind === "ok"
        ? state.health.relay_healthy && state.health.arbiter_healthy
          ? "Relay healthy; Arbiter healthy"
          : `Relay ${state.health.relay_healthy ? "healthy" : "degraded"}; Arbiter ${state.health.arbiter_healthy ? "healthy" : "degraded"}`
        : `Relay unreachable: ${state.reason}`;
  const className =
    state.kind === "ok" && state.health.relay_healthy && state.health.arbiter_healthy
      ? "xion-dot xion-dot--ok"
      : state.kind === "ok"
        ? "xion-dot xion-dot--warn"
        : state.kind === "degraded"
          ? "xion-dot xion-dot--err"
          : "xion-dot xion-dot--unknown";
  return (
    <span className="xion-health">
      <span className={className} aria-hidden="true" />
      <span className="xion-health__label">
        <span className="xion-sr-only">Relay status: </span>
        {label}
      </span>
    </span>
  );
}

export function Header({ current, onNavigate }: HeaderProps): JSX.Element {
  const { credential, signOut } = useBearer();
  const [health, setHealth] = useState<HealthState>({ kind: "unknown" });

  const pollHealth = useCallback(async () => {
    try {
      const h = await getHealth(credential);
      setHealth({ kind: "ok", health: h });
    } catch (err) {
      if (err instanceof ApiErrorException) {
        setHealth({ kind: "degraded", reason: err.api.kind });
      } else {
        setHealth({
          kind: "degraded",
          reason: err instanceof Error ? err.message : "unknown",
        });
      }
    }
  }, [credential]);

  useEffect(() => {
    void pollHealth();
    const handle = window.setInterval(() => {
      void pollHealth();
    }, HEALTH_POLL_MS);
    return () => window.clearInterval(handle);
  }, [pollHealth]);

  return (
    <header className="xion-header" role="banner">
      <div className="xion-header__top">
        <h1 className="xion-h1">Xion</h1>
        <HealthDot state={health} />
      </div>
      <nav className="xion-nav" aria-label="Primary">
        <ul className="xion-nav__list">
          {(["chat", "drive", "sensorium"] as const).map((view) => (
            <li key={view}>
              <button
                type="button"
                className={
                  "xion-nav__item" +
                  (current === view ? " xion-nav__item--active" : "")
                }
                onClick={() => onNavigate(view)}
                aria-current={current === view ? "page" : undefined}
              >
                {view === "chat" ? "Chat" : view === "drive" ? "Drive" : "Sensorium"}
              </button>
            </li>
          ))}
        </ul>
        <div className="xion-nav__auth">
          {credential ? (
            <>
              <span className="xion-meta">
                Signed in as <code>{credential.principalId}</code>
              </span>
              <button
                type="button"
                className="xion-button xion-button--ghost"
                onClick={signOut}
              >
                Sign out
              </button>
            </>
          ) : (
            <span className="xion-meta">Not signed in</span>
          )}
        </div>
      </nav>
    </header>
  );
}
