import { ChatView } from "./views/ChatView";

// Minimal App for Commit 2 of Phase 5g-v: the ChatView is reachable and
// rendered. Header, DriveView, and SensoriumView land in Commit 3; the
// view switcher becomes non-trivial at that point. For now there is one
// view and one heading.

export function App(): JSX.Element {
  return (
    <div className="xion-shell">
      <header className="xion-header" role="banner">
        <h1 className="xion-h1">Xion</h1>
        <p className="xion-header__tagline">Phase 5g-v operator dashboard</p>
      </header>
      <main className="xion-main" role="main" id="main-content">
        <ChatView />
      </main>
      <footer className="xion-footer" role="contentinfo">
        <p className="xion-hint">
          The server's Arbiter verdict is final. This client does not
          re-moderate. See <code>docs/31-WEB-CLIENT.md</code>.
        </p>
      </footer>
    </div>
  );
}
