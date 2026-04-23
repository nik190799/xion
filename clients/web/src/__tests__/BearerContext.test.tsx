import { describe, expect, it, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";

import {
  BearerProvider,
  buildAuthorizationHeader,
  useBearer,
  type BearerCredential,
} from "../auth/BearerContext";

function Probe() {
  const { credential, isSignedIn, signIn, signOut } = useBearer();
  return (
    <div>
      <div data-testid="state">
        {isSignedIn ? `signed-in:${credential?.principalId}` : "signed-out"}
      </div>
      <button
        data-testid="sign-in-good"
        onClick={() =>
          signIn(
            "operator:a1b2c3d4e5f6789012345678901234567890abcdef0123456789abcdef01",
          )
        }
      />
      <button
        data-testid="sign-in-short"
        onClick={() => signIn("operator:abc")}
      />
      <button
        data-testid="sign-in-nonhex"
        onClick={() => signIn("operator:zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")}
      />
      <button
        data-testid="sign-in-bad-principal"
        onClick={() =>
          signIn(
            "OPERATOR:a1b2c3d4e5f6789012345678901234567890abcdef0123456789abcdef01",
          )
        }
      />
      <button data-testid="sign-out" onClick={signOut} />
    </div>
  );
}

beforeEach(() => {
  window.localStorage.clear();
});

describe("BearerContext", () => {
  it("starts signed-out and signs in on a valid credential", async () => {
    render(
      <BearerProvider>
        <Probe />
      </BearerProvider>,
    );
    expect(screen.getByTestId("state").textContent).toBe("signed-out");
    act(() => {
      screen.getByTestId("sign-in-good").click();
    });
    expect(screen.getByTestId("state").textContent).toBe("signed-in:operator");
  });

  it("rejects short secrets (< 32 hex chars)", async () => {
    render(
      <BearerProvider>
        <Probe />
      </BearerProvider>,
    );
    act(() => {
      screen.getByTestId("sign-in-short").click();
    });
    expect(screen.getByTestId("state").textContent).toBe("signed-out");
  });

  it("rejects non-hex secrets", async () => {
    render(
      <BearerProvider>
        <Probe />
      </BearerProvider>,
    );
    act(() => {
      screen.getByTestId("sign-in-nonhex").click();
    });
    expect(screen.getByTestId("state").textContent).toBe("signed-out");
  });

  it("rejects uppercase principal_id (server charset is lowercase)", async () => {
    render(
      <BearerProvider>
        <Probe />
      </BearerProvider>,
    );
    act(() => {
      screen.getByTestId("sign-in-bad-principal").click();
    });
    expect(screen.getByTestId("state").textContent).toBe("signed-out");
  });

  it("persists across a remount via localStorage", () => {
    const { unmount } = render(
      <BearerProvider>
        <Probe />
      </BearerProvider>,
    );
    act(() => {
      screen.getByTestId("sign-in-good").click();
    });
    expect(screen.getByTestId("state").textContent).toBe("signed-in:operator");
    unmount();

    render(
      <BearerProvider>
        <Probe />
      </BearerProvider>,
    );
    expect(screen.getByTestId("state").textContent).toBe("signed-in:operator");
  });

  it("signOut clears both memory and localStorage", () => {
    render(
      <BearerProvider>
        <Probe />
      </BearerProvider>,
    );
    act(() => {
      screen.getByTestId("sign-in-good").click();
    });
    act(() => {
      screen.getByTestId("sign-out").click();
    });
    expect(screen.getByTestId("state").textContent).toBe("signed-out");
    expect(window.localStorage.getItem("xion:bearer")).toBeNull();
  });
});

describe("buildAuthorizationHeader", () => {
  it("returns {} when no credential", () => {
    expect(buildAuthorizationHeader(null)).toEqual({});
  });

  it("returns a Bearer header for a credential", () => {
    const cred: BearerCredential = {
      principalId: "operator",
      secretHex: "deadbeef".repeat(4),
    };
    expect(buildAuthorizationHeader(cred)).toEqual({
      Authorization: `Bearer ${"deadbeef".repeat(4)}`,
    });
  });
});
