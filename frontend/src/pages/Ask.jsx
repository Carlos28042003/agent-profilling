import { useEffect, useMemo, useRef, useState } from "react";
import { StepTokensChart } from "../components/charts.jsx";
import { Legend, Section } from "../components/ui.jsx";
import { fmt } from "../lib/format.js";

function StepCard({ s }) {
  const [open, setOpen] = useState(false);
  const thought = (s.output.match(/Thought:\s*([\s\S]*?)(?=\n\s*(Action|Final Answer):|$)/) || [])[1];
  const final = (s.output.match(/Final Answer:\s*([\s\S]*)/) || [])[1];
  const hit = s.prompt_tokens && s.cached_tokens != null ? Math.round((100 * s.cached_tokens) / s.prompt_tokens) : null;
  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-xs font-semibold px-2 py-0.5 rounded" style={{ background: "var(--surface-2)" }}>Step {s.index}</span>
        <span className="text-sm font-medium">{s.tool ? s.tool : final !== undefined ? "Final answer" : "—"}</span>
        <span className="ml-auto flex flex-wrap gap-3 text-xs secondary num">
          <span title="Time to first token">TTFT {fmt(s.llm_ttft_s, 2)}s</span>
          <span title="Generation time">gen {fmt(s.llm_generation_s, 2)}s</span>
          {s.tool && <span title="Tool time">tool {fmt(s.tool_s, 2)}s</span>}
          <span title="Prompt tokens">{s.prompt_tokens ?? "–"} tok</span>
          <span title="Prompt tokens served from cache">cache {hit ?? "–"}%</span>
        </span>
      </div>
      {thought && <p className="mt-2 text-sm secondary"><span className="muted">Thought: </span>{thought.trim()}</p>}
      {s.tool_input && (
        <p className="mt-1 text-sm"><span className="muted">Input: </span><span className="mono text-xs whitespace-pre-wrap">{s.tool_input}</span></p>
      )}
      {final !== undefined && <p className="mt-2 text-sm font-medium">{final.trim()}</p>}
      {s.observation && (
        <div className="mt-2">
          <button onClick={() => setOpen(!open)} className="text-xs cursor-pointer" style={{ color: "var(--accent)" }}>
            {open ? "Hide" : "Show"} observation ({s.observation.length} chars)
          </button>
          {open && <pre className="mt-1 p-3 rounded-lg text-xs mono whitespace-pre-wrap" style={{ background: "var(--surface-2)" }}>{s.observation}</pre>}
        </div>
      )}
    </div>
  );
}

export default function Ask({ configs }) {
  const [question, setQuestion] = useState("How many years passed between the founding of Google and the founding of Microsoft?");
  const [config, setConfig] = useState(configs.find((c) => c.name === "ollama")?.name ?? configs[0]?.name);
  const [steps, setSteps] = useState([]);
  const [done, setDone] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const source = useRef(null);

  useEffect(() => {
    if (!running) return undefined;
    const t0 = Date.now();
    const id = setInterval(() => setElapsed((Date.now() - t0) / 1000), 200);
    return () => clearInterval(id);
  }, [running]);

  useEffect(() => () => source.current?.close(), []);

  const run = (e) => {
    e.preventDefault();
    source.current?.close();
    setSteps([]); setDone(null); setError(null); setRunning(true); setElapsed(0);
    const src = new EventSource(`/api/ask?${new URLSearchParams({ question, config })}`);
    source.current = src;
    src.addEventListener("step", (ev) => setSteps((p) => [...p, JSON.parse(ev.data)]));
    src.addEventListener("done", (ev) => { setDone(JSON.parse(ev.data)); setRunning(false); src.close(); });
    src.addEventListener("error", (ev) => {
      setError(ev.data ? JSON.parse(ev.data).message : "Connection lost. Is the backend (uv run agentic-ui) still running?");
      setRunning(false); src.close();
    });
  };

  const totals = useMemo(() => {
    const later = steps.filter((s) => s.index > 0);
    const chars = later.reduce((a, s) => a + s.prompt_chars, 0);
    return {
      llm: steps.reduce((a, s) => a + s.llm_total_s, 0),
      tool: steps.reduce((a, s) => a + s.tool_s, 0),
      reuse: chars ? (100 * later.reduce((a, s) => a + s.shared_prefix_chars, 0)) / chars : null,
    };
  }, [steps]);

  const field = { background: "var(--surface-0)", borderColor: "var(--border)" };
  return (
    <div className="space-y-6">
      <form onSubmit={run} className="card p-5 space-y-3">
        <label className="block text-sm font-medium" htmlFor="q">Ask the agent a question</label>
        <textarea id="q" rows="2" value={question} onChange={(e) => setQuestion(e.target.value)}
                  className="w-full rounded-lg p-3 text-sm border" style={field} />
        <div className="flex flex-wrap items-center gap-3">
          <select value={config} onChange={(e) => setConfig(e.target.value)} className="rounded-lg px-3 py-2 text-sm border" style={field}>
            {configs.map((c) => <option key={c.name} value={c.name}>{c.name} · {c.model}</option>)}
          </select>
          <button type="submit" disabled={running || question.trim().length < 3}
                  className="px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50 cursor-pointer" style={{ background: "var(--accent)" }}>
            {running ? `Running… ${fmt(elapsed, 0)}s` : "Run agent"}
          </button>
          <span className="text-xs muted">
            Tools: Wikipedia search and lookup, calculator, Python. Each run is saved to <span className="mono">backend/traces/ask/</span>.
          </span>
        </div>
      </form>

      {error && <div className="card p-4 text-sm" style={{ color: "var(--bad)" }}>⚠ {error}</div>}

      {done && (
        <div className="card p-5">
          <div className="text-xs uppercase tracking-wide muted">Answer · {done.model}</div>
          <div className="mt-1 text-2xl font-semibold">{done.answer ?? "No answer (step limit reached)"}</div>
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-5 gap-3 text-sm num">
            <div><div className="muted text-xs">Total</div>{fmt(done.total_s)} s</div>
            <div><div className="muted text-xs">Steps</div>{steps.length}</div>
            <div><div className="muted text-xs">LLM time</div>{fmt(totals.llm)} s</div>
            <div><div className="muted text-xs">Tool time</div>{fmt(totals.tool)} s</div>
            <div><div className="muted text-xs">Repeated prefix</div>{fmt(totals.reuse, 0)}%</div>
          </div>
          <div className="mt-2 text-xs muted">Saved to <span className="mono">{done.saved_to}</span></div>
        </div>
      )}

      {steps.length > 0 && (
        <Section title="Prompt grows, cache follows">
          <Legend items={[["Prompt tokens", "var(--series-1)"], ["Cached tokens", "var(--series-2)"]]} />
          <div className="mt-2"><StepTokensChart steps={steps} /></div>
        </Section>
      )}

      <div className="space-y-3">
        {steps.map((s) => <StepCard key={s.index} s={s} />)}
        {running && <div className="card p-4 text-sm muted animate-pulse">Step {steps.length}: the model is thinking…</div>}
      </div>
    </div>
  );
}
