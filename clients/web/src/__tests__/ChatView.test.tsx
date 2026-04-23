import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ChatView } from "../views/ChatView";
import { BearerProvider } from "../auth/BearerContext";

// Minimal fetch stub; each test overrides window.fetch with a vi.fn()
// returning the Response shape for that posture. We do NOT mock the
// ApiErrorException pipe — we let it run end-to-end so the test is a
// real integration test of the envelope-matrix UX.

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

beforeEach(() => {
  // Each test gets its own isolated localStorage.
  window.localStorage.clear();
  vi.resetAllMocks();
});

describe("ChatView envelope matrix", () => {
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
    // KW-CLIENT-001 is explicitly named in the UX so an operator
    // reading the panel knows where to look in KNOWN_WEAKNESSES.md.
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

describe("ChatView accessibility (axe-core)", () => {
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
