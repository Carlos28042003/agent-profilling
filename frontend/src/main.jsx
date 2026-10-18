import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

// ?theme=light or ?theme=dark forces a theme (otherwise the system setting is used).
const theme = new URLSearchParams(window.location.search).get("theme");
if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
