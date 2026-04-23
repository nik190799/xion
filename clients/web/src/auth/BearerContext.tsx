import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

// `BearerContext` is the client-side store for the operator's bearer
// token. It is opt-in: when the server is in the Genesis-Default
// XION_API_REQUIRE_BEARER=false posture, no token is needed and the
// context just holds `null`. When the server flips to require-bearer,
// the client surfaces a sign-in dialog, the operator pastes the
// `principal_id:<hex>` credential, and the hex secret persists in
// localStorage under the key below. An explicit `signOut()` clears it.
//
// Doctrine anchor: docs/31-WEB-CLIENT.md § "Operator workflow — sign-in
// and bearer tokens".
//
// Why localStorage (not sessionStorage, not cookies):
//   - sessionStorage loses the token on tab-refresh (bad UX).
//   - Cookies would need the server to issue a session; the 5g-v server
//     doesn't have a session endpoint and adding one is outside the
//     5g-v scope.
//   - The 5g-v client is the operator's own dashboard (KW-CLIENT-001);
//     the operator trusts the machine running their browser. A public-
//     user posture (Phase 6+) will re-examine this.

const STORAGE_KEY = "xion:bearer";

export interface BearerCredential {
  /** Operator-chosen label, e.g. "operator". Matches the server's
   *  XION_API_BEARER_TOKENS registry key for this token. */
  principalId: string;
  /** Hex-encoded secret. Never logged; never echoed. */
  secretHex: string;
}

export interface BearerContextValue {
  credential: BearerCredential | null;
  /** True iff we have a credential in the store. Convenience alias. */
  isSignedIn: boolean;
  /** Parse a `principal_id:<hex>` string and persist it. Returns an
   *  error string on malformed input (no throw; caller renders the
   *  error in the sign-in dialog). */
  signIn: (pasted: string) => string | null;
  /** Clear the credential and remove it from localStorage. */
  signOut: () => void;
}

const BearerContext = createContext<BearerContextValue | null>(null);

function parseCredential(pasted: string): BearerCredential | string {
  const trimmed = pasted.trim();
  if (!trimmed) {
    return "Credential is empty.";
  }
  const colonIndex = trimmed.indexOf(":");
  if (colonIndex <= 0 || colonIndex === trimmed.length - 1) {
    return "Credential must be `principal_id:<hex-secret>`.";
  }
  const principalId = trimmed.slice(0, colonIndex);
  const secretHex = trimmed.slice(colonIndex + 1);
  // Charset parallels the server's AdmissionConfig.__post_init__.
  if (!/^[a-z0-9_-]{1,64}$/.test(principalId)) {
    return "principal_id must match ^[a-z0-9_-]{1,64}$ (lowercase).";
  }
  if (!/^[0-9a-fA-F]+$/.test(secretHex)) {
    return "Secret must be hex-encoded (0-9, a-f).";
  }
  // 128-bit entropy floor mirrors the server-side token entropy floor
  // (16 bytes => 32 hex chars).
  if (secretHex.length < 32) {
    return "Secret is below the 128-bit entropy floor (must be at least 32 hex chars).";
  }
  return { principalId, secretHex: secretHex.toLowerCase() };
}

function loadFromStorage(): BearerCredential | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (
      parsed &&
      typeof parsed === "object" &&
      "principalId" in parsed &&
      "secretHex" in parsed &&
      typeof (parsed as { principalId: unknown }).principalId === "string" &&
      typeof (parsed as { secretHex: unknown }).secretHex === "string"
    ) {
      return parsed as BearerCredential;
    }
    return null;
  } catch {
    return null;
  }
}

function saveToStorage(credential: BearerCredential): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(credential));
  } catch {
    // Storage may be unavailable (private mode, quota); we keep the
    // in-memory credential so the current tab still works.
  }
}

function clearStorage(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore; see saveToStorage.
  }
}

export function BearerProvider({ children }: { children: ReactNode }): JSX.Element {
  const [credential, setCredential] = useState<BearerCredential | null>(null);

  useEffect(() => {
    setCredential(loadFromStorage());
  }, []);

  const signIn = useCallback((pasted: string): string | null => {
    const parsed = parseCredential(pasted);
    if (typeof parsed === "string") {
      return parsed;
    }
    setCredential(parsed);
    saveToStorage(parsed);
    return null;
  }, []);

  const signOut = useCallback(() => {
    setCredential(null);
    clearStorage();
  }, []);

  const value = useMemo<BearerContextValue>(
    () => ({
      credential,
      isSignedIn: credential !== null,
      signIn,
      signOut,
    }),
    [credential, signIn, signOut],
  );

  return <BearerContext.Provider value={value}>{children}</BearerContext.Provider>;
}

export function useBearer(): BearerContextValue {
  const value = useContext(BearerContext);
  if (!value) {
    throw new Error("useBearer must be used within a BearerProvider");
  }
  return value;
}

export function buildAuthorizationHeader(
  credential: BearerCredential | null,
): Record<string, string> {
  if (!credential) return {};
  return { Authorization: `Bearer ${credential.secretHex}` };
}
