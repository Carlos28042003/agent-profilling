import { useEffect, useState } from "react";
import About from "./pages/About.jsx";
import Ask from "./pages/Ask.jsx";
import Results from "./pages/Results.jsx";

const TABS = [["results", "Results"], ["ask", "Ask the agent"], ["about", "About"]];

export default function App() {
  // null = checking, false = static site (GitHub Pages), object = local backend is running
  const [api, setApi] = useState(null);
  const [tab, setTabState] = useState(() => {
    const hash = window.location.hash.slice(1);
    return TABS.some(([k]) => k === hash) ? hash : "results";
  });
  const setTab = (k) => {
    setTabState(k);
    window.history.replaceState(null, "", `#${k}`);  // tabs are linkable: .../#ask
  };

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : false))
      .then(setApi)
      .catch(() => setApi(false));
  }, []);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">Agentic Profiling</h1>
        <p className="secondary mt-1 max-w-3xl">Where does the time go when an LLM agent runs, and how much of its work is repeated?</p>
        <div className="mt-2 text-xs muted">
          Carlos Chirindza · <a className="underline" href="https://github.com/Carlos28042003/agent-profilling">GitHub repository</a>
        </div>
      </header>

      <nav className="flex gap-1 mb-6 border-b" style={{ borderColor: "var(--border)" }}>
        {TABS.map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
                  className={`px-4 py-2 text-sm rounded-t-lg border border-b-0 -mb-px cursor-pointer ${tab === k ? "tab-active font-medium" : "border-transparent secondary"}`}>
            {label}{k === "ask" && api === false ? " (local only)" : ""}
          </button>
        ))}
      </nav>

      {tab === "results" && <Results />}
      {tab === "about" && <About />}
      {tab === "ask" && (api ? <Ask configs={api.configs} /> : (
        <div className="card p-6 secondary space-y-2">
          <p>{api === null ? "Checking for the local agent server…" : "The live agent runs on your own machine (it needs Ollama and the Python backend)."}</p>
          {api === false && (
            <p>Start it with <code className="mono">cd backend</code> then <code className="mono">uv run agentic-ui</code>, and open <code className="mono">http://localhost:8000</code>.</p>
          )}
        </div>
      ))}
    </div>
  );
}
