import { useCallback, useEffect, useRef, useState } from "react";

import { useBearer } from "../auth/BearerContext";
import {
  ApiErrorException,
  getDrive,
  type ApiError,
  type DriveResponse,
  type DriveTerm,
} from "../lib/api";

// DriveView polls `GET /drive` on the Supervisor's 10s tick cadence
// (matching orchestrator/supervisor/__init__.py; a Witness reading the
// client-side snapshot and a SENSORIUM_LEDGER row at the same monotonic
// instant sees the same numbers). Renders the three drive-vector
// components (w_survive / w_serve / w_meaning) as accessible horizontal
// bars with numeric labels.
//
// Doctrine: docs/04-ARCHITECTURE.md § "The Web Client Surface
// (Phase 5g-v)" — content-faithful rendering (P1) applies here too;
// we do not reinterpret or smooth the server's numbers.

const POLL_INTERVAL_MS = 10_000;

const DRIVE_LABELS = {
  survive: "Survive",
  serve: "Serve",
  meaning: "Meaning",
} as const;

const DRIVE_DESCRIPTIONS = {
  survive: "Keep the lights on; treasury + continuity.",
  serve: "Help the people speaking with Xion.",
  meaning: "Grow; make the covenant richer over time.",
} as const;

function DriveBar({
  name,
  term,
}: {
  name: keyof typeof DRIVE_LABELS;
  term: DriveTerm;
}): JSX.Element {
  const label = DRIVE_LABELS[name];
  const description = DRIVE_DESCRIPTIONS[name];
  const weightPct = Math.round(term.weight * 100);
  const signalPct = Math.round(term.current_signal * 100);
  const [floorPct, ceilingPct] = [
    Math.round(term.weight_band[0] * 100),
    Math.round(term.weight_band[1] * 100),
  ];
  return (
    <div className="xion-drive__row">
      <div className="xion-drive__row-head">
        <h3 className="xion-h3">{label}</h3>
        <span className="xion-meta">{description}</span>
      </div>
      <div
        className="xion-drive__bar"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={weightPct}
        aria-label={`${label} weight ${weightPct}% (band ${floorPct}%-${ceilingPct}%)`}
      >
        <div className="xion-drive__bar-fill" style={{ width: `${weightPct}%` }} />
        <div
          className="xion-drive__bar-band-floor"
          style={{ left: `${floorPct}%` }}
          aria-hidden="true"
        />
        <div
          className="xion-drive__bar-band-ceiling"
          style={{ left: `${ceilingPct}%` }}
          aria-hidden="true"
        />
      </div>
      <dl className="xion-drive__metrics">
        <dt>weight</dt>
        <dd>
          <code>{weightPct}%</code>
          <span className="xion-meta">
            {" "}
            band [{floorPct}%, {ceilingPct}%]
          </span>
        </dd>
        <dt>signal</dt>
        <dd>
          <code>{signalPct}%</code>
        </dd>
      </dl>
    </div>
  );
}

export function DriveView(): JSX.Element {
  const { credential } = useBearer();
  const [data, setData] = useState<DriveResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [lastFetchAt, setLastFetchAt] = useState<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchOnce = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await getDrive(credential, controller.signal);
      setData(response);
      setError(null);
      setLastFetchAt(Date.now());
    } catch (err) {
      if (err instanceof ApiErrorException) {
        // An aborted user_cancel (re-poll replacing a stale request) is
        // not an error we should surface; everything else is.
        if (err.api.kind === "aborted" && err.api.reason === "user_cancel") {
          return;
        }
        setError(err.api);
      }
    }
  }, [credential]);

  useEffect(() => {
    void fetchOnce();
    timerRef.current = window.setInterval(() => {
      void fetchOnce();
    }, POLL_INTERVAL_MS);
    return () => {
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current);
      }
      abortRef.current?.abort();
    };
  }, [fetchOnce]);

  return (
    <section className="xion-drive" aria-labelledby="drive-heading">
      <h2 id="drive-heading" className="xion-h2">
        Drive vector
      </h2>
      {error && error.kind === "unauthorized" && (
        <div className="xion-panel xion-panel--auth" role="alert">
          <p>
            Drive vector requires authentication. Sign in from the Chat view to
            view live readings.
          </p>
        </div>
      )}
      {error && error.kind === "rate_limited" && (
        <div className="xion-panel xion-panel--rate" role="alert">
          <p>
            Drive poll rate-limited ({error.body.bucket} bucket). Retry in{" "}
            {error.body.retry_after_s}s.
          </p>
        </div>
      )}
      {error &&
        error.kind !== "unauthorized" &&
        error.kind !== "rate_limited" && (
          <div className="xion-panel xion-panel--error" role="alert">
            <p>
              Drive poll failed (<code>{error.kind}</code>).
            </p>
          </div>
        )}
      {data ? (
        <>
          <div className="xion-drive__bars">
            <DriveBar name="survive" term={data.terms.survive} />
            <DriveBar name="serve" term={data.terms.serve} />
            <DriveBar name="meaning" term={data.terms.meaning} />
          </div>
          <footer className="xion-meta">
            schema_version <code>{data.schema_version}</code>
            {data.methodology_hash && (
              <>
                {" · "}methodology_hash{" "}
                <code className="xion-corr__value">
                  {data.methodology_hash.slice(0, 12)}…
                </code>
              </>
            )}
            {lastFetchAt !== null && (
              <>
                {" · "}fetched{" "}
                {Math.round((Date.now() - lastFetchAt) / 1000)}s ago
              </>
            )}
          </footer>
        </>
      ) : (
        !error && <p className="xion-hint">Loading drive vector…</p>
      )}
    </section>
  );
}
