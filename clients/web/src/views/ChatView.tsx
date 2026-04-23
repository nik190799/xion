import { useCallback, useEffect, useRef, useState } from "react";

import { useBearer } from "../auth/BearerContext";
import {
  ApiErrorException,
  postChat,
  type ApiError,
  type ChatSuccessResponse,
} from "../lib/api";

// ChatView handles the full server-response envelope matrix for
// `POST /chat` under the 5g-iv admission-gated surface. The matrix and
// the UX states are pinned in docs/31-WEB-CLIENT.md § "Envelope
// handling matrix".
//
// Commit 3 of Phase 5g-v lifted the fetch wrapper into `src/lib/api.ts`
// as a typed ApiError discriminated union. ChatView now switches on
// `err.kind` instead of raw status codes.

type ChatState =
  | { kind: "idle" }
  | { kind: "pending"; startedAt: number }
  | { kind: "success"; response: ChatSuccessResponse }
  | { kind: "error"; err: ApiError };

const SERVER_DEADLINE_MS = 30_000;
const CLIENT_DEADLINE_MS = 32_000;

function copyToClipboard(text: string): void {
  if (typeof navigator !== "undefined" && navigator.clipboard) {
    void navigator.clipboard.writeText(text).catch(() => {
      // Clipboard API can fail (permissions, non-secure context); the
      // correlation_id remains visible on-screen.
    });
  }
}

function CorrelationId({ id }: { id: string }): JSX.Element {
  return (
    <span className="xion-corr">
      correlation_id: <code className="xion-corr__value">{id}</code>{" "}
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

  useEffect(() => {
    if (state.kind !== "pending") return;
    const handle = window.setInterval(() => setNowMs(Date.now()), 200);
    return () => window.clearInterval(handle);
  }, [state.kind]);

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
    const startedAt = Date.now();
    setState({ kind: "pending", startedAt });
    setNowMs(startedAt);
    try {
      const response = await postChat(credential, trimmed, 512, controller.signal);
      setState({ kind: "success", response });
      setMessage("");
    } catch (err) {
      if (err instanceof ApiErrorException) {
        setState({ kind: "error", err: err.api });
      } else {
        setState({
          kind: "error",
          err: {
            kind: "network",
            status: 0,
            message: err instanceof Error ? err.message : String(err),
          },
        });
      }
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
          Client deadline: {Math.floor(CLIENT_DEADLINE_MS / 1000)}s.
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

        {state.kind === "error" && state.err.kind === "unauthorized" && (
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
              <code>{state.err.body.accepted_schemes.join(", ")}</code>
            </p>
          </div>
        )}

        {state.kind === "error" && state.err.kind === "payment_required" && (
          <div className="xion-panel xion-panel--billing" role="alert">
            <h3 className="xion-h3">Billing not yet supported in this client</h3>
            <p>
              The server is configured with <code>XION_BILLING_REQUIRED=true</code>{" "}
              and requires an <code>X-Payment-Commitment</code> header. The Phase
              5g-v web client does not yet sign payment commitments in the browser;
              see <code>docs/31-WEB-CLIENT.md</code> and{" "}
              <code>docs/29-BILLING-X402.md</code> for the <code>curl</code> path.
              This gap is tracked as <code>KW-CLIENT-001</code> and closes in
              Phase 6+ alongside <code>KW-BILLING-001</code>.
            </p>
            <dl className="xion-dl">
              <dt>Posted price</dt>
              <dd>{state.err.body.posted_price_micro_XION} μXION</dd>
              <dt>Accepted postures</dt>
              <dd>
                <code>{state.err.body.accepted_postures.join(", ")}</code>
              </dd>
              <dt>Reason</dt>
              <dd>
                <code>{state.err.body.reason_code}</code>
              </dd>
            </dl>
          </div>
        )}

        {state.kind === "error" && state.err.kind === "rate_limited" && (
          <div className="xion-panel xion-panel--rate" role="alert">
            <h3 className="xion-h3">Rate limited</h3>
            <p>
              The <code>{state.err.body.bucket}</code> bucket is exhausted. Retry
              in <strong>{state.err.body.retry_after_s}s</strong>.
            </p>
          </div>
        )}

        {state.kind === "error" && state.err.kind === "refused" && (
          <div className="xion-panel xion-panel--refused" role="alert">
            <h3 className="xion-h3">Xion declined to respond</h3>
            <p>
              Stage: <code>{state.err.body.stage}</code> · Covenant principle{" "}
              <code>{state.err.body.principle_code}</code> · reason{" "}
              <code>{state.err.body.reason}</code>.
            </p>
            <p className="xion-hint">
              Refusals are structural, not aspirational. The server's Arbiter
              verdict is final; this client does not re-moderate.
            </p>
            <CorrelationId id={state.err.body.correlation_id} />
          </div>
        )}

        {state.kind === "error" && state.err.kind === "service_unavailable" && (
          <div className="xion-panel xion-panel--unavailable" role="alert">
            <h3 className="xion-h3">Temporarily unavailable</h3>
            {state.err.body.reason === "open_weights_floor_unsatisfied" ? (
              <p>
                The orchestrator's open-weights floor is not held:{" "}
                <code>{state.err.body.missing_capability}</code>. Manifest id{" "}
                <code>{state.err.body.manifest_expected_id}</code>.
              </p>
            ) : (
              <>
                <p>No healthy generation provider.</p>
                <CorrelationId id={state.err.body.correlation_id} />
              </>
            )}
          </div>
        )}

        {state.kind === "error" && state.err.kind === "aborted" && (
          <div className="xion-panel xion-panel--timeout" role="alert">
            <h3 className="xion-h3">
              {state.err.reason === "timeout"
                ? "Request timed out (30s)"
                : "Request cancelled"}
            </h3>
            <p>
              {state.err.reason === "timeout"
                ? "The server did not respond within the per-turn deadline. This is typically a Relay-side issue; retry, or check GET /health."
                : "You cancelled the request."}
            </p>
          </div>
        )}

        {state.kind === "error" && state.err.kind === "network" && (
          <div className="xion-panel xion-panel--error" role="alert">
            <h3 className="xion-h3">Network error</h3>
            <p>{state.err.message}</p>
          </div>
        )}

        {state.kind === "error" && state.err.kind === "other" && (
          <div className="xion-panel xion-panel--error" role="alert">
            <h3 className="xion-h3">Unexpected error</h3>
            <p>
              HTTP <code>{state.err.status}</code>
              {state.err.body && typeof state.err.body === "object"
                ? ` — ${JSON.stringify(state.err.body)}`
                : ""}
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
