import React from "react";
import ReactDOM from "react-dom/client";
import App, { PRELOAD } from "./App.jsx";
import "./index.css";
import { initMonitoring } from "./lib/monitoring";

initMonitoring();

// The public pages arrive with their content already in #root, rendered at
// build time (scripts/prerender.mjs), which says which page it is. Load that
// page's code before the first render so React replaces the copy with the
// same page, not with the loading skeleton. A failed load renders anyway and
// the page's own error handling takes over.
const container = document.getElementById("root");
const prerendered = container.dataset.prerendered;
const ready = PRELOAD[prerendered]?.() ?? Promise.resolve();

ready
  .catch(() => {})
  .then(() => {
    ReactDOM.createRoot(container).render(
      <React.StrictMode>
        <App still={Boolean(prerendered)} />
      </React.StrictMode>
    );
  });
