import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { SettingsView } from "../views/SettingsView";
import { PresenceView } from "../views/PresenceView";
import { VitalsView } from "../views/VitalsView";
import { BearerProvider } from "../auth/BearerContext";

vi.mock("../lib/crypto", () => ({
  signMessage: async () => ({
    signatureB64: "mock-sig",
    publicKeyB64: "mock-pub"
  }),
  forgetKeys: async () => {}
}));

function makeResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  window.localStorage.clear();
  vi.resetAllMocks();
});

describe("New Web Views accessibility (axe-core)", () => {
  it("has no axe-core violations in SettingsView", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(makeResponse(200, {
      per_message_price_micro_XION: 1000,
      modality_costs: { visual: 0, vitals: 0, voice: 0 }
    })));

    const axeMod = await import("axe-core");
    const axe = axeMod.default ?? axeMod;
    const { container } = render(
      <BearerProvider>
        <SettingsView />
      </BearerProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /settings/i })).toBeInTheDocument();
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

  it("has no axe-core violations in PresenceView", async () => {
    // Stub EventSource
    class MockEventSource {
      onmessage: any;
      onerror: any;
      close = vi.fn();
      constructor(url: string) {
        setTimeout(() => {
          if (this.onmessage) {
            this.onmessage({ data: JSON.stringify({ type: "visual", mood: { valence: 0.5, energy: 0.5, focus: 0.5 }, primitives: [] }) });
          }
        }, 10);
      }
    }
    vi.stubGlobal("EventSource", MockEventSource);
    // Mock user being signed in by faking the token
    window.localStorage.setItem("xion:bearer", JSON.stringify({ secretHex: "0123456789abcdef0123456789abcdef", principalId: "test" }));

    const axeMod = await import("axe-core");
    const axe = axeMod.default ?? axeMod;
    const { container } = render(
      <BearerProvider>
        <PresenceView />
      </BearerProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /visual presence/i })).toBeInTheDocument();
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

  it("has no axe-core violations in VitalsView", async () => {
    // Stub EventSource
    class MockEventSource {
      onmessage: any;
      onerror: any;
      close = vi.fn();
      constructor(url: string) {
        setTimeout(() => {
          if (this.onmessage) {
            this.onmessage({ data: JSON.stringify({ type: "vitals", vitals: [{ domain: "1 — Financial Vitality", reading: 1.0, band: "healthy", methodology_sha256: "abc", subjective: false }] }) });
          }
        }, 10);
      }
    }
    vi.stubGlobal("EventSource", MockEventSource);
    window.localStorage.setItem("xion:bearer", JSON.stringify({ secretHex: "0123456789abcdef0123456789abcdef", principalId: "test" }));

    const axeMod = await import("axe-core");
    const axe = axeMod.default ?? axeMod;
    const { container } = render(
      <BearerProvider>
        <VitalsView />
      </BearerProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /vital signs/i })).toBeInTheDocument();
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
