import { useCallback, useEffect, useRef, useState } from "react";

import { buildAuthorizationHeader, useBearer } from "../auth/BearerContext";

// ChatView handles the full server-response envelope matrix for
// `POST /chat` under the 5g-iv admission-gated surface:
//
//   200 ChatResponse         -> render text + correlation_id + usage
//   401 AuthChallenge        -> open sign-in dialog; clear any stored token
//   402 PaymentChallenge     -> "billing not yet supported in browser" banner
//                               pointing at docs/29-BILLING-X402.md curl path
//   429 RateLimitChallenge   -> "Rate limited" with retry_after_s countdown
//   451 RefusalEnvelope      -> explicit refusal UX (stage + principle + corr)
//   503 NoFloorEnvelope
//       / ProviderErrorEnvelope -> "Temporarily unavailable" + correlation_id
//   other                    -> generic error with status
//   timeout (>30s)           -> "Request timed out" with retry affordance
//
// Each non-200 state is deliberately a visible UX state, never a toast
// or a silent error. Doctrine: docs/31-WEB-CLIENT.md § "Envelope handling
// matrix".
//
// Commit 3 of Phase 5g-v will lift the fetch wrapper out of this file
// into `src/lib/api.ts` and promote the DRY-ing of header injection +
// discriminated-union ApiError. For Commit 2 the minimal inline handler
// keeps the surface readable in one file.

type ChatSuccess = {
  role: "xion";
  text: string;
  model_id: string;
  usage: { input_tokens: number; output_tokens: number };
  correlation_id: string;
};

type AuthChallenge = {
  error: "unauthorized";
  accepted_schemes: string[];
};

type RateLimitChallenge = {
  error: "rate_limited";
  retry_after_s: number;
  bucket: "principal" | "ip";
};

type PaymentChallenge = {
  error: "payment_required";
  pricing_url: string;
  accepted_postures: string[];
  posted_price_micro_XION: number;
  reason_code: string;
};

type RefusalEnvelope = {
  stage: "ingress" | "egress";
  principle_code: number;
  reason: "covenant_refuse" | "covenant_escalate" | "provider_empty_candidate";
  correlation_id: string;
};

type NoFloorEnvelope = {
  reason: "open_weights_floor_unsatisfied";
  missing_capability: string;
  manifest_expected_id: string;
};

type ProviderErrorEnvelope = {
  reason: "no_healthy_provider";
  correlation_id: string;
};

type ServiceUnavailable = NoFloorEnvelope | ProviderErrorEnvelope;

type ChatState =
  | { kind: "idle" }
  | { kind: "pending"; startedAt: number; deadlineMs: number }
  | { kind: "success"; response: ChatSuccess }
  | { kind: "auth-required"; body: AuthChallenge }
  | { kind: "payment-required"; body: PaymentChallenge }
  | { kind: "rate-limited"; body: RateLimitChallenge }
  | { kind: "refused"; body: RefusalEnvelope }
  | { kind: "service-unavailable"; body: ServiceUnavailable }
  | { kind: "error"; status: number; detail: string }
  | { kind: "timeout" };

// Match the server's 30s per-turn deadline in
// orchestrator/api/chat.py. Slightly over it so the server's own
// timeout fires first and we render its envelope rather than a client-
// side abort.
const CLIENT_DEADLINE_MS = 32_000;
const SERVER_DEADLINE_MS = 30_000;

async function postChat(
  message: string,
  authHeader: Record<string, string>,
  signal: AbortSignal,
): Promise<{ status: number; body: unknown }> {
  const response = await fetch("/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeader,
    },
    body: JSON.stringify({ message, max_tokens: 512 }),
    signal,
  });
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  return { status: response.status, body };
}

function copyToClipboard(text: string): void {
  if (typeof navigator !== "undefined" && navigator.clipboard) {
    void navigator.clipboard.writeText(text).catch(() => {
      // Clipboard API can fail (permissions, non-secure context). We
      // intentionally swallow; the correlation_id is visible on-screen.
    });
  }
}

function CorrelationId({ id }: { id: string }): JSX.Element {
  return (
    <span className="xion-corr">
      correlation_id:{" "}
      <code className="xion-corr__value">{id}</code>{" "}
      <button
        type="button"
        className="xion-button xion-button--inline"
        onClick={() => copyToClipboard(id)}
        aria-label={`Copy correlation id ${id} to clipboard`}
      >
        copy
      </button>
    </span>
  );
}

function DeadlineProgress({
  startedAt,
  nowMs,
}: {
  startedAt: number;
  nowMs: number;
}): JSX.Element {
  const elapsed = Math.max(0, nowMs - startedAt);
  const remaining = Math.max(0, SERVER_DEADLINE_MS - elapsed);
  const pct = Math.min(100, (elapsed / SERVER_DEADLINE_MS) * 100);
  const remainingS = Math.ceil(remaining / 1000);
  return (
    <div
      className="xion-progress"
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={SERVER_DEADLINE_MS}
      aria-valuenow={elapsed}
      aria-label={`Chat response deadline, ${remainingS} seconds remaining`}
    >
      <div className="xion-progress__bar" style={{ width: `${pct}%` }} />
      <div className="xion-progress__label">
        Xion is thinking… {remainingS}s before the server-side deadline
      </div>
    </div>
  );
}

export function ChatView(): JSX.Element {
  const { credential, signIn, signOut } = useBearer();
  const [message, setMessage] = useState("");
  const [state, setState] = useState<ChatState>({ kind: "idle" });
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [signInInput, setSignInInput] = useState("");
  const [signInError, setSignInError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Tick the clock while a request is pending so the deadline progress
  // indicator updates smoothly. 200 ms cadence is plenty for human
  // perception and cheap enough that we don't need RAF.
  useEffect(() => {
    if (state.kind !== "pending") return;
    const handle = window.setInterval(() => setNowMs(Date.now()), 200);
    return () => window.clearInterval(handle);
  }, [state.kind]);

  // Cancel any in-flight request on unmount.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const submit = useCallback(async () => {
    const trimmed = message.trim();
    if (!trimmed) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const timeoutHandle = window.setTimeout(
      () => controller.abort(),
      CLIENT_DEADLINE_MS,
    );
    const startedAt = Date.now();
    setState({ kind: "pending", startedAt, deadlineMs: SERVER_DEADLINE_MS });
    setNowMs(startedAt);
    try {
      const authHeader = buildAuthorizationHeader(credential);
      const { status, body } = await postChat(trimmed, authHeader, controller.signal);
      window.clearTimeout(timeoutHandle);
      if (status === 200 && body && typeof body === "object" && "text" in body) {
        setState({ kind: "success", response: body as ChatSuccess });
        setMessage("");
        return;
      }
      if (status === 401) {
        setState({ kind: "auth-required", body: body as AuthChallenge });
        return;
      }
      if (status === 402) {
        setState({ kind: "payment-required", body: body as PaymentChallenge });
        return;
      }
      if (status === 429) {
        setState({ kind: "rate-limited", body: body as RateLimitChallenge });
        return;
      }
      if (status === 451) {
        setState({ kind: "refused", body: body as RefusalEnvelope });
        return;
      }
      if (status === 503) {
        setState({ kind: "service-unavailable", body: body as ServiceUnavailable });
        return;
      }
      setState({
        kind: "error",
        status,
        detail:
          body && typeof body === "object"
            ? JSON.stringify(body)
            : `Unexpected HTTP ${status}`,
      });
    } catch (err) {
      window.clearTimeout(timeoutHandle);
      if (controller.signal.aborted) {
        setState({ kind: "timeout" });
        return;
      }
      setState({
        kind: "error",
        status: 0,
        detail: err instanceof Error ? err.message : String(err),
      });
    }
  }, [message, credential]);

  const handleSignIn = useCallback(() => {
    const err = signIn(signInInput);
    if (err) {
      setSignInError(err);
      return;
    }
    setSignInError(null);
    setSignInInput("");
    setState({ kind: "idle" });
  }, [signIn, signInInput]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        void submit();
      }
    },
    [submit],
  );

  return (
    <section className="xion-chat" aria-labelledby="chat-heading">
      <h2 id="chat-heading" className="xion-h2">
        Chat
      </h2>

      <form
        className="xion-chat__form"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <label htmlFor="xion-chat-input" className="xion-label">
          Your message to Xion
        </label>
        <textarea
          id="xion-chat-input"
          className="xion-textarea"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={onKeyDown}
          rows={4}
          maxLength={16_000}
          placeholder="Write what you want to ask. Ctrl+Enter to send."
          disabled={state.kind === "pending"}
          aria-describedby="xion-chat-hint"
        />
        <p id="xion-chat-hint" className="xion-hint">
          Plain text. No markdown. 16&nbsp;000 character bound matches the server.
        </p>
        <div className="xion-chat__actions">
          <button
            type="submit"
            className="xion-button xion-button--primary"
            disabled={state.kind === "pending" || !message.trim()}
          >
            {state.kind === "pending" ? "Sending…" : "Send"}
          </button>
          {state.kind === "pending" && (
            <button
              type="button"
              className="xion-button xion-button--ghost"
              onClick={() => abortRef.current?.abort()}
            >
              Cancel
            </button>
          )}
        </div>
      </form>

      <div className="xion-chat__output" aria-live="polite" aria-atomic="false">
        {state.kind === "pending" && (
          <DeadlineProgress startedAt={state.startedAt} nowMs={nowMs} />
        )}

        {state.kind === "success" && (
          <article className="xion-bubble xion-bubble--xion" aria-label="Xion's reply">
            <header className="xion-bubble__header">
              <span className="xion-role">Xion</span>
              <span className="xion-meta">
                model: <code>{state.response.model_id}</code> · input:{" "}
                {state.response.usage.input_tokens} · output:{" "}
                {state.response.usage.output_tokens}
              </span>
            </header>
            <pre className="xion-bubble__text">{state.response.text}</pre>
            <footer className="xion-bubble__footer">
              <CorrelationId id={state.response.correlation_id} />
            </footer>
          </article>
        )}

        {state.kind === "auth-required" && (
          <div className="xion-panel xion-panel--auth" role="alert">
            <h3 className="xion-h3">Sign in required</h3>
            <p>
              The server requires a bearer token. Paste your{" "}
              <code>principal_id:&lt;hex-secret&gt;</code> credential below. The
              secret never leaves this browser beyond the{" "}
              <code>Authorization: Bearer</code> header it injects.
            </p>
            <label htmlFor="xion-signin-input" className="xion-label">
              Credential
            </label>
            <input
              id="xion-signin-input"
              className="xion-input"
              type="password"
              value={signInInput}
              onChange={(e) => setSignInInput(e.target.value)}
              placeholder="operator:a1b2c3…"
              autoComplete="off"
              spellCheck={false}
            />
            {signInError && (
              <p className="xion-error" role="alert">
                {signInError}
              </p>
            )}
            <div className="xion-chat__actions">
              <button
                type="button"
                className="xion-button xion-button--primary"
                onClick={handleSignIn}
              >
                Save credential
              </button>
            </div>
            <p className="xion-hint">
              Accepted schemes:{" "}
              <code>{state.body.accepted_schemes.join(", ")}</code>
            </p>
          </div>
        )}

        {state.kind === "payment-required" && (
          <div className="xion-panel xion-panel--billing" role="alert">
            <h3 className="xion-h3">Billing not yet supported in this client</h3>
            <p>
              The server is configured with <code>XION_BILLING_REQUIRED=true</code>{" "}
              and requires an <code>X-Payment-Commitment</code> header. The
              Phase 5g-v web client does not yet sign payment commitments in the
              browser; see <code>docs/31-WEB-CLIENT.md</code> and{" "}
              <code>docs/29-BILLING-X402.md</code> for the{" "}
              <code>curl</code> path. This gap is tracked as{" "}
              <code>KW-CLIENT-001</code> and closes in Phase 6+ alongside{" "}
              <code>KW-BILLING-001</code>.
            </p>
            <dl className="xion-dl">
              <dt>Posted price</dt>
              <dd>{state.body.posted_price_micro_XION} μXION</dd>
              <dt>Accepted postures</dt>
              <dd>
                <code>{state.body.accepted_postures.join(", ")}</code>
              </dd>
              <dt>Reason</dt>
              <dd>
                <code>{state.body.reason_code}</code>
              </dd>
            </dl>
          </div>
        )}

        {state.kind === "rate-limited" && (
          <div className="xion-panel xion-panel--rate" role="alert">
            <h3 className="xion-h3">Rate limited</h3>
            <p>
              The <code>{state.body.bucket}</code> bucket is exhausted. Retry in{" "}
              <strong>{state.body.retry_after_s}s</strong>.
            </p>
          </div>
        )}

        {state.kind === "refused" && (
          <div className="xion-panel xion-panel--refused" role="alert">
            <h3 className="xion-h3">Xion declined to respond</h3>
            <p>
              Stage: <code>{state.body.stage}</code> · Covenant principle{" "}
              <code>{state.body.principle_code}</code> · reason{" "}
              <code>{state.body.reason}</code>.
            </p>
            <p className="xion-hint">
              Refusals are structural, not aspirational. The server's Arbiter
              verdict is final; this client does not re-moderate.
            </p>
            <CorrelationId id={state.body.correlation_id} />
          </div>
        )}

        {state.kind === "service-unavailable" && (
          <div className="xion-panel xion-panel--unavailable" role="alert">
            <h3 className="xion-h3">Temporarily unavailable</h3>
            {state.body.reason === "open_weights_floor_unsatisfied" ? (
              <p>
                The orchestrator's open-weights floor is not held:{" "}
                <code>{state.body.missing_capability}</code>. Manifest id{" "}
                <code>{state.body.manifest_expected_id}</code>.
              </p>
            ) : (
              <>
                <p>No healthy generation provider.</p>
                <CorrelationId id={state.body.correlation_id} />
              </>
            )}
          </div>
        )}

        {state.kind === "timeout" && (
          <div className="xion-panel xion-panel--timeout" role="alert">
            <h3 className="xion-h3">Request timed out (30s)</h3>
            <p>
              The server did not respond within the per-turn deadline. This is
              typically a Relay-side issue; retry, or check{" "}
              <code>GET /health</code>.
            </p>
          </div>
        )}

        {state.kind === "error" && (
          <div className="xion-panel xion-panel--error" role="alert">
            <h3 className="xion-h3">Unexpected error</h3>
            <p>
              HTTP <code>{state.status}</code>. {state.detail}
            </p>
          </div>
        )}
      </div>

      {credential && (
        <p className="xion-signedin">
          Signed in as <code>{credential.principalId}</code>{" "}
          <button
            type="button"
            className="xion-button xion-button--inline"
            onClick={signOut}
          >
            sign out
          </button>
        </p>
      )}
    </section>
  );
}
