import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ChatView } from "../views/ChatView";
import { BearerProvider } from "../auth/BearerContext";

vi.mock("../lib/crypto", () => ({
  signMessage: async () => ({
    signatureB64: "mock-signature",
    publicKeyB64: "mock-pubkey"
  }),
  forgetKeys: async () => {}
}));

// Minimal fetch stub; each test overrides window.fetch with a vi.fn()
// returning the Response shape for that posture. We do NOT mock the
// ApiErrorException pipe — we let it run end-to-end so the test is a
// real integration test of the envelope-matrix UX.
//
// Phase 5g-ii note: ChatView now defaults to the streaming
// `/chat/stream` endpoint. The original envelope-matrix tests below
// force the non-streaming path via `?stream=0`; a new "streaming
// render-path" describe block exercises the SSE parser and the
// pending-chunk UX.

function renderChat() {
  return render(
    <BearerProvider>
      <ChatView />
    </BearerProvider>,
  );
}

function makeResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function forceNonStreaming() {
  window.history.replaceState({}, "", "/?stream=0");
}

function forceStreaming() {
  window.history.replaceState({}, "", "/");
}

beforeEach(() => {
  window.localStorage.clear();
  vi.resetAllMocks();
});

describe("ChatView envelope matrix (non-streaming, ?stream=0)", () => {
  beforeEach(() => {
    forceNonStreaming();
  });
  afterEach(() => {
    forceStreaming();
  });

  it("renders the model's text verbatim on 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        makeResponse(200, {
          role: "xion",
          text: "Hello, world.\n\n**not rendered as markdown**",
          model_id: "test-model",
          usage: { input_tokens: 4, output_tokens: 9 },
          correlation_id: "corr-abc-123",
        }),
      ),
    );
    const user = userEvent.setup();
    renderChat();

    await user.type(
      screen.getByRole("textbox", { name: /your message to xion/i }),
      "Hello",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    // The <pre> renders the raw text including the literal "**" — we
    // do NOT re-interpret it as markdown (content-faithful rendering).
    const bubble = await screen.findByLabelText(/xion's reply/i);
    expect(bubble.textContent).toContain(
      "Hello, world.\n\n**not rendered as markdown**",
    );
    expect(screen.getByText(/corr-abc-123/)).toBeInTheDocument();
  });

  it("surfaces a sign-in dialog on 401", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        makeResponse(401, {
          error: "unauthorized",
          accepted_schemes: ["Bearer"],
        }),
      ),
    );
    const user = userEvent.setup();
    renderChat();

    await user.type(
      screen.getByRole("textbox", { name: /your message to xion/i }),
      "Hi",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(
      await screen.findByRole("heading", { name: /sign in required/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/accepted schemes/i)).toBeInTheDocument();
  });

  it("shows the billing-not-supported panel on 402 with the posted price", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        makeResponse(402, {
          error: "payment_required",
          pricing_url: "/pricing",
          accepted_postures: ["operator-attest:v1"],
          posted_price_micro_XION: 1000,
          reason_code: "missing_commitment",
        }),
      ),
    );
    const user = userEvent.setup();
    renderChat();

    await user.type(
      screen.getByRole("textbox", { name: /your message to xion/i }),
      "Hi",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(
      await screen.findByRole("heading", {
        name: /billing not yet supported/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/1000 μXION/)).toBeInTheDocument();
    expect(screen.getByText(/KW-CLIENT-001/)).toBeInTheDocument();
  });

  it("shows the rate-limit retry_after_s on 429", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        makeResponse(429, {
          error: "rate_limited",
          retry_after_s: 17,
          bucket: "principal",
        }),
      ),
    );
    const user = userEvent.setup();
    renderChat();

    await user.type(
      screen.getByRole("textbox", { name: /your message to xion/i }),
      "Hi",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(
      await screen.findByRole("heading", { name: /rate limited/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/17s/)).toBeInTheDocument();
    expect(screen.getByText(/principal/)).toBeInTheDocument();
  });

  it("renders the refusal envelope with stage + principle + correlation_id on 451", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        makeResponse(451, {
          stage: "ingress",
          principle_code: 2,
          reason: "covenant_refuse",
          correlation_id: "corr-refuse-99",
        }),
      ),
    );
    const user = userEvent.setup();
    renderChat();

    await user.type(
      screen.getByRole("textbox", { name: /your message to xion/i }),
      "Hi",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(
      await screen.findByRole("heading", { name: /xion declined to respond/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/covenant_refuse/)).toBeInTheDocument();
    expect(screen.getByText(/corr-refuse-99/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------
// Streaming render-path tests (Phase 5g-ii Commit 4).
// ---------------------------------------------------------------
//
// These tests exercise the SSE branch of ChatView by mocking
// `window.fetch` to return a Response whose body is a ReadableStream
// we control via an imperative `push`/`close` API. We can therefore
// drive the test deterministically:
//   1. Push a couple of chunks; assert the pending bubble renders
//      their concatenation in the "pending egress review" visual
//      state.
//   2. Push a `done:approve`; assert the pending bubble is replaced
//      by the committed reply bubble.
//   3. Push a `done:refuse`; assert the pending bubble is replaced
//      by the content-free RefusalEnvelope panel (retroactive
//      refusal).
//
// An axe-core pass is run on the pending state to close
// KW-CLIENT-002's accessibility-of-provisional-UI concern.

interface ControlledSseResponse {
  response: Response;
  push: (event: object) => void;
  close: () => void;
}

function makeControlledSseResponse(): ControlledSseResponse {
  let streamController: ReadableStreamDefaultController<Uint8Array> | null =
    null;
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      streamController = controller;
    },
  });
  const response = new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
  return {
    response,
    push: (event: object) => {
      if (!streamController) throw new Error("stream controller not ready");
      streamController.enqueue(
        encoder.encode(`data: ${JSON.stringify(event)}\n\n`),
      );
    },
    close: () => {
      if (!streamController) throw new Error("stream controller not ready");
      streamController.close();
    },
  };
}

describe("ChatView streaming render-path (Phase 5g-ii)", () => {
  beforeEach(() => {
    forceStreaming();
  });

  it("renders streamed chunks in a pending state, then commits on done:approve", async () => {
    const ctrl = makeControlledSseResponse();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ctrl.response));

    const user = userEvent.setup();
    renderChat();

    await user.type(
      screen.getByRole("textbox", { name: /your message to xion/i }),
      "Stream test",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    // First chunk arrives — pending bubble should render its text.
    ctrl.push({ kind: "chunk", seq: 0, text: "Hello, " });
    const pendingText = await screen.findByText(
      (_content, node) =>
        node?.className?.toString().includes("xion-bubble__text--pending") ===
          true &&
        (node?.textContent ?? "").startsWith("Hello, "),
    );
    expect(pendingText).toBeInTheDocument();
    expect(screen.getByText(/pending egress review/i)).toBeInTheDocument();

    // Second chunk arrives — the buffer grows.
    ctrl.push({ kind: "chunk", seq: 1, text: "world." });
    await waitFor(() => {
      const pending = screen
        .getAllByRole("article")
        .find((a) =>
          a.getAttribute("aria-label")?.includes("pending egress review"),
        );
      expect(pending?.textContent).toContain("Hello, world.");
    });

    // done:approve commits the message. The pending bubble should be
    // replaced by the final reply bubble, carrying the server's
    // egress-moderated `response.text` (which, per doctrine, equals
    // the concatenated chunks when approve fires).
    ctrl.push({
      kind: "done",
      verdict: "approve",
      response: {
        role: "xion",
        text: "Hello, world.",
        model_id: "stream-model",
        usage: { input_tokens: 3, output_tokens: 4 },
        correlation_id: "corr-stream-ok",
      },
    });
    ctrl.close();

    const committed = await screen.findByLabelText(/xion's reply/i);
    expect(committed.textContent).toContain("Hello, world.");
    expect(screen.getByText(/corr-stream-ok/)).toBeInTheDocument();
    expect(screen.queryByText(/pending egress review/i)).not.toBeInTheDocument();
  });

  it("retroactively replaces pending chunks with a RefusalEnvelope on done:refuse", async () => {
    const ctrl = makeControlledSseResponse();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ctrl.response));

    const user = userEvent.setup();
    renderChat();

    await user.type(
      screen.getByRole("textbox", { name: /your message to xion/i }),
      "Refuse test",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    ctrl.push({ kind: "chunk", seq: 0, text: "forbidden tokens " });
    ctrl.push({ kind: "chunk", seq: 1, text: "still speculative" });
    await waitFor(() => {
      expect(screen.getByText(/pending egress review/i)).toBeInTheDocument();
    });

    // Server moderates the full candidate, emits done:refuse. The
    // client must DISCARD the buffered pending text and render a
    // content-free RefusalEnvelope panel.
    ctrl.push({
      kind: "done",
      verdict: "refuse",
      refusal: {
        stage: "egress",
        principle_code: 5,
        reason: "covenant_refuse",
        correlation_id: "corr-refuse-egress-1",
      },
    });
    ctrl.close();

    expect(
      await screen.findByRole("heading", { name: /xion declined to respond/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/covenant_refuse/)).toBeInTheDocument();
    expect(screen.getByText(/corr-refuse-egress-1/)).toBeInTheDocument();
    // Crucially: the previously-buffered tokens must NOT remain in
    // the DOM. Retroactive refusal is the whole point.
    expect(screen.queryByText(/forbidden tokens/)).not.toBeInTheDocument();
    expect(screen.queryByText(/pending egress review/i)).not.toBeInTheDocument();
  });

  it("treats done:cancelled as the user_cancel UX", async () => {
    const ctrl = makeControlledSseResponse();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ctrl.response));

    const user = userEvent.setup();
    renderChat();

    await user.type(
      screen.getByRole("textbox", { name: /your message to xion/i }),
      "Cancel test",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    ctrl.push({ kind: "chunk", seq: 0, text: "draft" });
    // Per doctrine the server does NOT emit done:cancelled on the
    // wire (the client is gone by then). The verdict is retained in
    // the client-side discriminated union only for operator-replay
    // tooling. We still assert the UI handles it gracefully.
    ctrl.push({ kind: "done", verdict: "cancelled" });
    ctrl.close();

    expect(
      await screen.findByRole("heading", { name: /request cancelled/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/pending egress review/i)).not.toBeInTheDocument();
  });

  it("maps error:deadline_exceeded to the timeout UX", async () => {
    const ctrl = makeControlledSseResponse();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ctrl.response));

    const user = userEvent.setup();
    renderChat();

    await user.type(
      screen.getByRole("textbox", { name: /your message to xion/i }),
      "Deadline test",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    ctrl.push({
      kind: "error",
      error: "deadline_exceeded",
      correlation_id: "corr-deadline-1",
    });
    ctrl.close();

    expect(
      await screen.findByRole("heading", { name: /request timed out/i }),
    ).toBeInTheDocument();
  });

  it("surfaces pre-stream 401 via the sign-in panel", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        makeResponse(401, {
          error: "unauthorized",
          accepted_schemes: ["Bearer"],
        }),
      ),
    );
    const user = userEvent.setup();
    renderChat();

    await user.type(
      screen.getByRole("textbox", { name: /your message to xion/i }),
      "Need auth",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(
      await screen.findByRole("heading", { name: /sign in required/i }),
    ).toBeInTheDocument();
  });

  it("has no axe-core violations in the pending (streaming) state", async () => {
    const ctrl = makeControlledSseResponse();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ctrl.response));

    const user = userEvent.setup();
    const { container } = renderChat();

    await user.type(
      screen.getByRole("textbox", { name: /your message to xion/i }),
      "axe pending test",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    ctrl.push({ kind: "chunk", seq: 0, text: "chunk one " });
    ctrl.push({ kind: "chunk", seq: 1, text: "chunk two" });
    await waitFor(() => {
      expect(screen.getByText(/pending egress review/i)).toBeInTheDocument();
    });

    const axeMod = await import("axe-core");
    const axe = axeMod.default ?? axeMod;
    const results = await axe.run(container, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
      },
    });
    if (results.violations.length > 0) {
      const summary = results.violations
        .map((v) => `${v.id}: ${v.help}`)
        .join("\n");
      throw new Error(`axe-core violations in pending state:\n${summary}`);
    }

    // Cleanly terminate the stream so the test doesn't leak a
    // running async iterator into the next test.
    ctrl.push({
      kind: "done",
      verdict: "approve",
      response: {
        role: "xion",
        text: "chunk one chunk two",
        model_id: "axe-model",
        usage: { input_tokens: 1, output_tokens: 2 },
        correlation_id: "corr-axe",
      },
    });
    ctrl.close();
    await screen.findByLabelText(/xion's reply/i);
  });
});

describe("ChatView accessibility (axe-core)", () => {
  beforeEach(() => {
    forceNonStreaming();
  });
  afterEach(() => {
    forceStreaming();
  });

  it("has no axe-core violations in the idle state", async () => {
    const axeMod = await import("axe-core");
    const axe = axeMod.default ?? axeMod;
    const { container } = renderChat();
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /^chat$/i })).toBeInTheDocument();
    });
    const results = await axe.run(container, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
      },
    });
    if (results.violations.length > 0) {
      const summary = results.violations.map((v) => `${v.id}: ${v.help}`).join("\n");
      throw new Error(`axe-core violations:\n${summary}`);
    }
  });
});
