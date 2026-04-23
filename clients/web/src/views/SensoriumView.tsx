import { useCallback, useEffect, useRef, useState } from "react";

import { useBearer } from "../auth/BearerContext";
import {
  ApiErrorException,
  getSensorium,
  type ApiError,
  type SensoriumResponse,
} from "../lib/api";

// SensoriumView polls `GET /sensorium` on the same 10s cadence as the
// Drive view. Renders Interoception / Chronoception / Proprioception
// panels plus the last distress signal. The server's SensoriumState is
// content-free by construction (enforced by the Phase 5f SensoriumResponse
// extra="forbid" test + field allowlist); we render it verbatim without
// synthesising any extra field.

const POLL_INTERVAL_MS = 10_000;

function Pct({ v }: { v: number }): JSX.Element {
  return <code>{Math.round(v * 100)}%</code>;
}

function Seconds({ v }: { v: number }): JSX.Element {
  return <code>{v.toFixed(1)}s</code>;
}

function formatUtcNs(ns: number): string {
  if (!ns) return "-";
  const ms = Math.floor(ns / 1_000_000);
  return new Date(ms).toISOString().replace("T", " ").replace("Z", " UTC");
}

export function SensoriumView(): JSX.Element {
  const { credential } = useBearer();
  const [data, setData] = useState<SensoriumResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [lastFetchAt, setLastFetchAt] = useState<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetchOnce = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await getSensorium(credential, controller.signal);
      setData(response);
      setError(null);
      setLastFetchAt(Date.now());
    } catch (err) {
      if (err instanceof ApiErrorException) {
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
    <section className="xion-sensorium" aria-labelledby="sensorium-heading">
      <h2 id="sensorium-heading" className="xion-h2">
        Sensorium
      </h2>
      {error && error.kind === "unauthorized" && (
        <div className="xion-panel xion-panel--auth" role="alert">
          <p>
            Sensorium requires authentication. Sign in from the Chat view to
            view live readings.
          </p>
        </div>
      )}
      {error && error.kind === "rate_limited" && (
        <div className="xion-panel xion-panel--rate" role="alert">
          <p>
            Sensorium poll rate-limited ({error.body.bucket} bucket). Retry in{" "}
            {error.body.retry_after_s}s.
          </p>
        </div>
      )}
      {error &&
        error.kind !== "unauthorized" &&
        error.kind !== "rate_limited" && (
          <div className="xion-panel xion-panel--error" role="alert">
            <p>
              Sensorium poll failed (<code>{error.kind}</code>).
            </p>
          </div>
        )}
      {data ? (
        <div className="xion-sensorium__grid">
          <article className="xion-panel">
            <h3 className="xion-h3">Interoception</h3>
            <dl className="xion-dl">
              <dt>survival pressure</dt>
              <dd>
                <Pct v={data.interoception.survival_pressure} />
              </dd>
              <dt>treasury stress</dt>
              <dd>
                <Pct v={data.interoception.treasury_stress} />
              </dd>
              <dt>cost pressure</dt>
              <dd>
                <Pct v={data.interoception.cost_pressure} />
              </dd>
            </dl>
          </article>

          <article className="xion-panel">
            <h3 className="xion-h3">Chronoception</h3>
            <dl className="xion-dl">
              <dt>checkpoint stale</dt>
              <dd>
                <Seconds v={data.chronoception.checkpoint_staleness_s} />
              </dd>
              <dt>degraded-mode time</dt>
              <dd>
                <Seconds v={data.chronoception.time_in_degraded_mode_s} />
              </dd>
              <dt>monotonic drift</dt>
              <dd>
                <code>{data.chronoception.monotonic_drift_ns} ns</code>
              </dd>
            </dl>
          </article>

          <article className="xion-panel">
            <h3 className="xion-h3">Proprioception</h3>
            <dl className="xion-dl">
              <dt>relay</dt>
              <dd>
                <code
                  className={
                    data.proprioception.relay_healthy
                      ? "xion-status xion-status--ok"
                      : "xion-status xion-status--err"
                  }
                >
                  {data.proprioception.relay_healthy ? "healthy" : "degraded"}
                </code>
              </dd>
              <dt>arbiter</dt>
              <dd>
                <code
                  className={
                    data.proprioception.arbiter_healthy
                      ? "xion-status xion-status--ok"
                      : "xion-status xion-status--err"
                  }
                >
                  {data.proprioception.arbiter_healthy ? "healthy" : "degraded"}
                </code>
              </dd>
              <dt>watchdog fires (10m)</dt>
              <dd>
                <code>{data.proprioception.watchdog_fires_recent}</code>
              </dd>
            </dl>
          </article>

          <article className="xion-panel">
            <h3 className="xion-h3">Distress</h3>
            <dl className="xion-dl">
              <dt>text distress</dt>
              <dd>
                <Pct v={data.distress.text_distress_score} />
              </dd>
              <dt>source</dt>
              <dd>
                <code>{data.distress.source}</code>
              </dd>
            </dl>
          </article>

          <footer className="xion-sensorium__footer xion-meta">
            as_of <code>{formatUtcNs(data.as_of_utc_ns)}</code>
            {lastFetchAt !== null && (
              <>
                {" · "}fetched{" "}
                {Math.round((Date.now() - lastFetchAt) / 1000)}s ago
              </>
            )}
          </footer>
        </div>
      ) : (
        !error && <p className="xion-hint">Loading sensorium…</p>
      )}
    </section>
  );
}
