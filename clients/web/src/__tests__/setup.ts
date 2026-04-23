import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// React Testing Library auto-cleanup is not wired into vitest the way
// it is in jest; we do it by hand here so each test starts with an
// empty DOM.
afterEach(() => {
  cleanup();
});

// Silence the React 18 act() warnings that fire during async state
// transitions in the tests below. Vitest's default console wrapper
// emits the warning anyway if we leave it; suppressing only this one
// line keeps the signal-to-noise ratio honest.
const originalError = console.error;
console.error = (...args: unknown[]) => {
  const first = args[0];
  if (
    typeof first === "string" &&
    first.includes("not wrapped in act")
  ) {
    return;
  }
  originalError(...args);
};
