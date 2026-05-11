// Cloudflare Worker — Chutes inference proxy for Xion Relay
//
// Property promised: the Chutes API key never leaves the Cloudflare account.
// Akash-deployed relays call this Worker's URL (a non-secret); the Worker
// attaches the real Chutes Authorization header from Worker secrets and
// forwards /v1/* paths to https://llm.chutes.ai/v1/* . On-chain Akash SDL
// only sees the public Worker URL, never the cpk_... token.
//
// Required Worker secret (Dashboard → your Worker → Settings → Variables and Secrets → Add → "Type: Secret"):
//   CHUTES_API_KEY     The cpk_... token issued by chutes.ai with inference scope.
//
// Optional Worker secret (defense-in-depth):
//   PROXY_BEARER       If set, requests must send `Authorization: Bearer <this>`;
//                      anything else returns 401. Rotate instantly if leaked.
//
// Routes served:
//   GET  /health        → 200 "ok"     (cheap reachability check, no upstream)
//   ANY  /v1/*          → proxied to https://llm.chutes.ai/v1/*
//   *    everything else → 404
//
// Streaming is preserved (response body is piped, not buffered).

const UPSTREAM = "https://llm.chutes.ai";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return new Response("ok\n", {
        status: 200,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    if (!url.pathname.startsWith("/v1/")) {
      return new Response("Not Found\n", {
        status: 404,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    // Optional client-side bearer gate.
    if (env.PROXY_BEARER) {
      const auth = request.headers.get("Authorization") || "";
      if (auth !== `Bearer ${env.PROXY_BEARER}`) {
        return new Response("Unauthorized\n", {
          status: 401,
          headers: { "content-type": "text/plain; charset=utf-8" },
        });
      }
    }

    if (!env.CHUTES_API_KEY) {
      return new Response("server misconfigured: CHUTES_API_KEY not set\n", {
        status: 500,
        headers: { "content-type": "text/plain; charset=utf-8" },
      });
    }

    // Build upstream request: keep method, body, query, drop client auth,
    // attach our Chutes bearer, let fetch() set Host.
    const upstreamUrl = new URL(UPSTREAM + url.pathname + url.search);
    const headers = new Headers(request.headers);
    headers.set("Authorization", `Bearer ${env.CHUTES_API_KEY}`);
    headers.delete("Host");
    headers.delete("CF-Connecting-IP");
    headers.delete("CF-Ray");
    headers.delete("X-Forwarded-For");

    const upstreamReq = new Request(upstreamUrl.toString(), {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "manual",
    });

    const upstreamResp = await fetch(upstreamReq);

    // Stream straight back — preserves SSE for streaming chat completions.
    return new Response(upstreamResp.body, {
      status: upstreamResp.status,
      statusText: upstreamResp.statusText,
      headers: upstreamResp.headers,
    });
  },
};
