import type { BearerCredential } from "../auth/BearerContext";
import { buildAuthorizationHeader } from "../auth/BearerContext";

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

export function postChat(
  credential: BearerCredential | null,
  message: string,
  maxTokens: number,
  signal?: AbortSignal,
): Promise<ChatSuccessResponse> {
  return apiFetch<ChatSuccessResponse>({
    path: "/chat",
    method: "POST",
    credential,
    body: { message, max_tokens: maxTokens },
    signal,
  });
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
