import { useState } from "react";

import { Header, type ViewId } from "./components/Header";
import { ChatView } from "./views/ChatView";
import { DriveView } from "./views/DriveView";
import { SensoriumView } from "./views/SensoriumView";
import { PresenceView } from "./views/PresenceView";
import { VitalsView } from "./views/VitalsView";
import { SettingsView } from "./views/SettingsView";

// App shell: Header + main view region + footer. Six views total
// (Chat / Drive / Sensorium / Presence / Vitals / Settings); the Header component owns the switcher
// and the Relay health dot. No client-side routing library — a single
// state variable is sufficient for six views.

export function App(): JSX.Element {
  const [view, setView] = useState<ViewId>("chat");
  return (
    <div className="xion-shell">
      <Header current={view} onNavigate={setView} />
      <main className="xion-main" role="main" id="main-content">
        {view === "chat" && <ChatView />}
        {view === "drive" && <DriveView />}
        {view === "sensorium" && <SensoriumView />}
        {view === "presence" && <PresenceView />}
        {view === "vitals" && <VitalsView />}
        {view === "settings" && <SettingsView />}
      </main>
      <footer className="xion-footer" role="contentinfo">
        <p className="xion-hint">
          The server's Arbiter verdict is final. This client does not
          re-moderate. Doctrine: <code>docs/31-WEB-CLIENT.md</code>.
        </p>
      </footer>
    </div>
  );
}
