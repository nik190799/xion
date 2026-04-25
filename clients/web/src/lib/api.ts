import type { BearerCredential } from "../auth/BearerContext";
import { buildAuthorizationHeader } from "../auth/BearerContext";
import { signMessage } from "./crypto";

// Single fetch wrapper for every Xion API call from the web client.
//
// Shape: returns either the parsed JSON body on 2xx, or throws a typed
// ApiError (discriminated union) on any non-2xx response. Callers
// switch on the `kind` field; each case renders its own UX state.
//
// Doctrine anchor: docs/31-WEB-CLIENT.md § "Envelope handling matrix".
//
// The wrapper is deliberately tiny — no interceptor plumbing, no
// retry-with-backoff, no request memoization. Adding any of those is
// its own phase's decision.

export type AuthChallengeBody = {
  error: "unauthorized";
  accepted_schemes: string[];
};

export type RateLimitChallengeBody = {
  error: "rate_limited";
  retry_after_s: number;
  bucket: "principal" | "ip";
};

export type PaymentChallengeBody = {
  error: "payment_required";
  pricing_url: string;
  accepted_postures: string[];
  posted_price_micro_XION: number;
  reason_code: string;
};

export type RefusalEnvelopeBody = {
  stage: "ingress" | "egress";
  principle_code: number;
  reason: "covenant_refuse" | "covenant_escalate" | "provider_empty_candidate";
  correlation_id: string;
};

export type NoFloorBody = {
  reason: "open_weights_floor_unsatisfied";
  missing_capability: string;
  manifest_expected_id: string;
};

export type ProviderErrorBody = {
  reason: "no_healthy_provider";
  correlation_id: string;
};

export type ServiceUnavailableBody = NoFloorBody | ProviderErrorBody;

export type ApiError =
  | { kind: "unauthorized"; status: 401; body: AuthChallengeBody }
  | { kind: "payment_required"; status: 402; body: PaymentChallengeBody }
  | { kind: "rate_limited"; status: 429; body: RateLimitChallengeBody }
  | { kind: "refused"; status: 451; body: RefusalEnvelopeBody }
  | { kind: "service_unavailable"; status: 503; body: ServiceUnavailableBody }
  | { kind: "aborted"; status: 0; reason: "timeout" | "user_cancel" }
  | { kind: "network"; status: 0; message: string }
  | { kind: "other"; status: number; body: unknown };

export class ApiErrorException extends Error {
  readonly api: ApiError;
  constructor(api: ApiError) {
    super(`ApiError ${api.kind} (HTTP ${api.status})`);
    this.name = "ApiErrorException";
    this.api = api;
  }
}

async function parseJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function classifyNon2xx(status: number, body: unknown): ApiError {
  switch (status) {
    case 401:
      return { kind: "unauthorized", status: 401, body: body as AuthChallengeBody };
    case 402:
      return { kind: "payment_required", status: 402, body: body as PaymentChallengeBody };
    case 429:
      return { kind: "rate_limited", status: 429, body: body as RateLimitChallengeBody };
    case 451:
      return { kind: "refused", status: 451, body: body as RefusalEnvelopeBody };
    case 503:
      return {
        kind: "service_unavailable",
        status: 503,
        body: body as ServiceUnavailableBody,
      };
    default:
      return { kind: "other", status, body };
  }
}

export interface ApiRequest {
  path: string;
  method?: "GET" | "POST";
  credential: BearerCredential | null;
  body?: unknown;
  /** AbortSignal caller can use to cancel the fetch. */
  signal?: AbortSignal;
  /** Abort the fetch if no response arrives within this many ms.
   *  Defaults to 32_000 (slightly over the server's 30s /chat deadline
   *  so the server's envelope wins over a client-side abort). */
  deadlineMs?: number;
}

export async function apiFetch<T>(req: ApiRequest): Promise<T> {
  const controller = new AbortController();
  const timeoutHandle = window.setTimeout(
    () => controller.abort(),
    req.deadlineMs ?? 32_000,
  );
  // Forward external aborts (e.g. unmount) into our controller so the
  // fetch sees a single signal.
  if (req.signal) {
    if (req.signal.aborted) {
      controller.abort();
    } else {
      req.signal.addEventListener("abort", () => controller.abort(), { once: true });
    }
  }
  try {
    const headers: Record<string, string> = {
      ...buildAuthorizationHeader(req.credential),
    };
    let body: BodyInit | undefined;
    if (req.body !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(req.body);
    }
    const response = await fetch(req.path, {
      method: req.method ?? "GET",
      headers,
      body,
      signal: controller.signal,
    });
    const parsed = await parseJson(response);
    if (response.ok) {
      return parsed as T;
    }
    throw new ApiErrorException(classifyNon2xx(response.status, parsed));
  } catch (err) {
    if (err instanceof ApiErrorException) {
      throw err;
    }
    if (controller.signal.aborted) {
      const reason: ApiError =
        req.signal?.aborted
          ? { kind: "aborted", status: 0, reason: "user_cancel" }
          : { kind: "aborted", status: 0, reason: "timeout" };
      throw new ApiErrorException(reason);
    }
    throw new ApiErrorException({
      kind: "network",
      status: 0,
      message: err instanceof Error ? err.message : String(err),
    });
  } finally {
    window.clearTimeout(timeoutHandle);
  }
}

// ----- Typed helpers for each endpoint the client uses -----

export type ChatSuccessResponse = {
  role: "xion";
  text: string;
  model_id: string;
  usage: { input_tokens: number; output_tokens: number };
  correlation_id: string;
};

export async function postChat(
  credential: BearerCredential | null,
  message: string,
  maxTokens: number,
  signal?: AbortSignal,
): Promise<ChatSuccessResponse> {
  const { signatureB64, publicKeyB64 } = await signMessage(message);
  return apiFetch<ChatSuccessResponse>({
    path: "/chat",
    method: "POST",
    credential,
    body: {
      message,
      max_tokens: maxTokens,
      user_proof: {
        user_pubkey_b64: publicKeyB64,
        signature_b64: signatureB64,
        algorithm: "ed25519",
      },
    },
    signal,
  });
}

// ----- Streaming chat (Phase 5g-ii) --------------------------------------
//
// Doctrine anchor: docs/32-CHAT-STREAMING.md § "SSE wire format" +
// docs/04-ARCHITECTURE.md § "Streaming the Chat Surface (Phase 5g-ii)".
//
// The server emits SSE records of the form ``data: <json>\n\n``. Each
// JSON object is one of three discriminated shapes keyed by ``kind``:
// ``chunk``, ``done``, ``error``. ``streamChat`` returns an
// ``AsyncIterable<StreamEvent>`` the caller consumes with ``for await``.
//
// HTTP-level admission failures (401/402/429) never open the stream —
// they surface as a thrown ``ApiErrorException`` before the async
// iterator produces any event, so the caller can reuse the same
// envelope-matrix branching as ``postChat``.
//
// The fetch is wired to ``AbortSignal`` so a user-side cancel closes
// the underlying connection; the server's Commit-3 disconnect
// detection will observe the close and write an ``outcome=cancelled``
// PAYMENT row.

export type StreamChunkServerEvent = {
  kind: "chunk";
  seq: number;
  text: string;
};

export type StreamDoneServerEvent = {
  kind: "done";
  verdict: "approve" | "refuse" | "cancelled" | "no_floor" | "provider_error";
  response?: ChatSuccessResponse | null;
  refusal?: RefusalEnvelopeBody | null;
  no_floor?: NoFloorBody | null;
  provider_error?: ProviderErrorBody | null;
};

export type StreamErrorServerEvent = {
  kind: "error";
  error: "internal" | "deadline_exceeded";
  correlation_id: string;
};

export type StreamEvent =
  | StreamChunkServerEvent
  | StreamDoneServerEvent
  | StreamErrorServerEvent;

export interface StreamChatRequest {
  credential: BearerCredential | null;
  message: string;
  maxTokens: number;
  signal?: AbortSignal;
  /** Matches ``apiFetch``'s default so the server envelope wins over
   *  a client-side abort. */
  deadlineMs?: number;
}

export async function* streamChat(
  req: StreamChatRequest,
): AsyncIterable<StreamEvent> {
  const controller = new AbortController();
  const timeoutHandle = window.setTimeout(
    () => controller.abort(),
    req.deadlineMs ?? 32_000,
  );
  if (req.signal) {
    if (req.signal.aborted) {
      controller.abort();
    } else {
      req.signal.addEventListener("abort", () => controller.abort(), {
        once: true,
      });
    }
  }
  try {
    const { signatureB64, publicKeyB64 } = await signMessage(req.message);
    const response = await fetch("/chat/stream", {
      method: "POST",
      headers: {
        ...buildAuthorizationHeader(req.credential),
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({
        message: req.message,
        max_tokens: req.maxTokens,
        user_proof: {
          user_pubkey_b64: publicKeyB64,
          signature_b64: signatureB64,
          algorithm: "ed25519",
        },
      }),
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = await parseJson(response);
      throw new ApiErrorException(classifyNon2xx(response.status, body));
    }
    if (!response.body) {
      throw new ApiErrorException({
        kind: "network",
        status: 0,
        message: "streaming response body missing",
      });
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // SSE records are separated by blank lines (\n\n). Split the
      // current buffer; keep the tail (potentially incomplete record)
      // for the next read.
      let sepIndex: number;
      while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
        const record = buffer.slice(0, sepIndex);
        buffer = buffer.slice(sepIndex + 2);
        const parsed = _parseSseRecord(record);
        if (parsed !== null) {
          yield parsed;
        }
      }
    }
    // Drain any trailing record that lacked a final \n\n (defensive;
    // the server pins \n\n terminators).
    if (buffer.trim().length > 0) {
      const parsed = _parseSseRecord(buffer);
      if (parsed !== null) {
        yield parsed;
      }
    }
  } catch (err) {
    if (err instanceof ApiErrorException) {
      throw err;
    }
    if (controller.signal.aborted) {
      const reason: ApiError =
        req.signal?.aborted
          ? { kind: "aborted", status: 0, reason: "user_cancel" }
          : { kind: "aborted", status: 0, reason: "timeout" };
      throw new ApiErrorException(reason);
    }
    throw new ApiErrorException({
      kind: "network",
      status: 0,
      message: err instanceof Error ? err.message : String(err),
    });
  } finally {
    window.clearTimeout(timeoutHandle);
  }
}

function _parseSseRecord(record: string): any | null {
  const trimmed = record.trim();
  if (trimmed.length === 0) return null;
  // Accept multi-line records but the server only ever emits one
  // "data:" line per record; concatenate any continuation lines
  // defensively per SSE spec.
  const lines = trimmed.split("\n");
  let eventType = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
  }
  
  if (eventType === "closed") {
    return { kind: "closed" };
  }
  
  if (dataLines.length === 0) return null;
  const payload = dataLines.join("\n");
  try {
    return JSON.parse(payload);
  } catch {
    return null;
  }
}

export interface PresenceStreamRequest {
  credential: BearerCredential | null;
  visual: boolean;
  vitals: boolean;
  signal?: AbortSignal;
}

export async function* subscribePresenceStream(
  req: PresenceStreamRequest,
): AsyncIterable<any> {
  const controller = new AbortController();
  if (req.signal) {
    if (req.signal.aborted) {
      controller.abort();
    } else {
      req.signal.addEventListener("abort", () => controller.abort(), {
        once: true,
      });
    }
  }

  try {
    const visualParam = req.visual ? "1" : "0";
    const vitalsParam = req.vitals ? "1" : "0";
    const response = await fetch(`/presence/stream?visual=${visualParam}&vitals=${vitalsParam}`, {
      method: "GET",
      headers: {
        ...buildAuthorizationHeader(req.credential),
        Accept: "text/event-stream",
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      const body = await parseJson(response);
      throw new ApiErrorException(classifyNon2xx(response.status, body));
    }
    if (!response.body) {
      throw new ApiErrorException({
        kind: "network",
        status: 0,
        message: "streaming response body missing",
      });
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let sepIndex: number;
      while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
        const record = buffer.slice(0, sepIndex);
        buffer = buffer.slice(sepIndex + 2);
        const parsed = _parseSseRecord(record);
        if (parsed !== null) {
          if (parsed.kind === "closed") {
            return; // Clean exit
          }
          yield parsed;
        }
      }
    }
    if (buffer.trim().length > 0) {
      const parsed = _parseSseRecord(buffer);
      if (parsed !== null && parsed.kind !== "closed") {
        yield parsed;
      }
    }
  } catch (err) {
    if (err instanceof ApiErrorException) {
      throw err;
    }
    if (controller.signal.aborted) {
      return; // Clean exit on abort
    }
    throw new ApiErrorException({
      kind: "network",
      status: 0,
      message: err instanceof Error ? err.message : String(err),
    });
  }
}

export type HealthResponse = {
  relay_healthy: boolean;
  arbiter_healthy: boolean;
  watchdog_fires_recent: number;
  as_of_monotonic_ns: number;
};

export function getHealth(
  credential: BearerCredential | null,
  signal?: AbortSignal,
): Promise<HealthResponse> {
  return apiFetch<HealthResponse>({
    path: "/health",
    credential,
    signal,
    // /health is a fast probe; cap at 5s.
    deadlineMs: 5_000,
  });
}

export type DriveTerm = {
  current_signal: number;
  weight: number;
  weight_band: [number, number];
};

export type DriveResponse = {
  schema_version: string;
  as_of_utc_ns: number;
  terms: { survive: DriveTerm; serve: DriveTerm; meaning: DriveTerm };
  methodology_hash: string | null;
};

export function getDrive(
  credential: BearerCredential | null,
  signal?: AbortSignal,
): Promise<DriveResponse> {
  return apiFetch<DriveResponse>({
    path: "/drive",
    credential,
    signal,
    deadlineMs: 5_000,
  });
}

export type SensoriumResponse = {
  interoception: {
    survival_pressure: number;
    treasury_stress: number;
    cost_pressure: number;
    as_of_utc_ns: number;
  };
  chronoception: {
    as_of_utc_ns: number;
    checkpoint_staleness_s: number;
    time_in_degraded_mode_s: number;
    monotonic_drift_ns: number;
  };
  proprioception: {
    as_of_utc_ns: number;
    relay_healthy: boolean;
    arbiter_healthy: boolean;
    watchdog_fires_recent: number;
  };
  distress: {
    text_distress_score: number;
    source: string;
    as_of_utc_ns: number;
  };
  as_of_utc_ns: number;
};

export function getSensorium(
  credential: BearerCredential | null,
  signal?: AbortSignal,
): Promise<SensoriumResponse> {
  return apiFetch<SensoriumResponse>({
    path: "/sensorium",
    credential,
    signal,
    deadlineMs: 5_000,
  });
}
