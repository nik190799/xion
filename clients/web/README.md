# Xion web client (Phase 5g-v)

The operator's own dashboard against the admission-gated HTTP surface.

**Doctrine:** [`docs/31-WEB-CLIENT.md`](../../docs/31-WEB-CLIENT.md)
and [`docs/04-ARCHITECTURE.md`](../../docs/04-ARCHITECTURE.md) § "The Web
Client Surface (Phase 5g-v)".

## Requirements

- Node.js `>=20.10`
- npm `>=10`

## Build (production)

```bash
cd clients/web
npm ci                # reproducible install from package-lock.json
npm run lint          # eslint + jsx-a11y; zero warnings required
npm test              # Vitest + axe-core; zero violations required
npm run build         # emits clients/web/dist/
cd ../..
xion-verify web-client  # structural audit of the emitted bundle
```

The verifier asserts: (1) `index.html` carries a `Content-Security-Policy`
meta tag pinning `default-src 'self'`; (2) every `https?://` origin in the
emitted tree matches the explicit non-self allowlist (React production
error-decoder URLs and W3C XML namespace identifiers — both literal strings
that are never fetched at runtime). Any stray CDN URL baked into a dependency
would fail the verifier and is a release blocker.

Then in the orchestrator:

```bash
# in .env (or equivalent):
XION_WEB_CLIENT_ENABLED=true
XION_WEB_CLIENT_DIST_PATH=clients/web/dist

XION_DOTENV_PATH=.env xion-orchestrator-api
```

The FastAPI launcher will mount the bundle at `/app/*` and the SPA
fallback at `/` will serve `index.html` for any unknown in-app route
(see Commit 4 of Phase 5g-v).

## Dev mode

```bash
# Terminal 1: orchestrator
XION_DOTENV_PATH=.env xion-orchestrator-api

# Terminal 2: Vite dev server with API proxy to :8000
cd clients/web
npm run dev           # http://127.0.0.1:5173/app/
```

Vite's dev server proxies `/chat`, `/drive`, `/sensorium`, `/health`,
and `/pricing` to `http://127.0.0.1:8000`. The cross-origin posture
exists only on the developer's own machine.

## What lives here

- `package.json`, `package-lock.json` — dependency pins. `npm ci` is
  the reproducible-install entrypoint.
- `vite.config.ts` — Vite dev-proxy + production-base at `/app/`.
- `tsconfig.json` — strict TypeScript.
- `index.html` — root HTML shell. Carries a
  `Content-Security-Policy: default-src 'self'` meta tag.
- `src/main.tsx` — React root mount + `BearerProvider`.
- `src/App.tsx` — layout + view switcher.
- `src/App.css` — design-system tokens + plain-CSS components.
- `src/auth/BearerContext.tsx` — bearer-token store. Persists in
  `localStorage` under `xion:bearer`. Explicit sign-out clears it.
- `src/views/ChatView.tsx` — `POST /chat` UI. Handles the full server-
  response envelope matrix (200 / 401 / 402 / 429 / 451 / 503) with
  explicit UX states, a 30 s deadline countdown, and a
  correlation-id copy affordance.

## What does NOT live here (tracked as KWs)

- In-browser x402 payment-commitment signing (`KW-CLIENT-001`; closes
  Phase 6+ alongside `KW-BILLING-001`).
- Streaming UX (`KW-CLIENT-002`; closes with Phase 5g-ii's SSE/WebSocket
  streaming + per-chunk moderation).
- Component library, CSS framework, state library, router library. A
  client this small does not need them; the supply-chain widening would
  outweigh the ergonomic saving.
- Analytics, trackers, cookies, SSR.
