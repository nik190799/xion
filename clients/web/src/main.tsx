import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { BearerProvider } from "./auth/BearerContext";

import "./App.css";

// Root mount. The `BearerProvider` wraps the whole tree so every
// component (ChatView, future DriveView/SensoriumView) can reach the
// token store without prop-drilling. StrictMode double-renders in dev
// only; it does not affect production behavior.

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Xion web client: #root not found in index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <BearerProvider>
      <App />
    </BearerProvider>
  </StrictMode>,
);
