import { fmt } from "../lib/format.js";

function Table({ cols, rows, cell }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm num">
        <thead>
          <tr>{cols.map(([k, l]) => <th key={k} className="text-left font-medium muted py-2 pr-4 whitespace-nowrap">{l}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.run}>{cols.map(([k]) => cell(r, k))}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const mono = (k) => (k === "run" || k === "model" ? "mono text-xs" : "");

export function RunsTable({ runs }) {
  const cols = [["run", "Run"], ["model", "Model"], ["accuracy", "Acc."], ["finished", "Done"], ["steps_mean", "Steps"],
                ["task_s_p50", "P50 s"], ["ttft_mean_s", "TTFT s"], ["prefix_reuse_%", "Prefix % (chars)"],
                ["cached_tok_%", "Cached %"], ["truncated_steps", "Trunc."]];
  return (
    <Table cols={cols} rows={runs} cell={(r, k) => (
      <td key={k} className={`py-2 pr-4 whitespace-nowrap ${mono(k)}`}
          style={k === "truncated_steps" && r[k] > 0 ? { color: "var(--bad)" } : {}}>
        {k === "accuracy" || k === "finished" ? `${Math.round(r[k] * 100)}%`
          : typeof r[k] === "number" ? fmt(r[k], k === "truncated_steps" ? 0 : 1) : r[k]}
      </td>
    )} />
  );
}

export function CompareTable({ rows }) {
  const cols = [["run", "Setup"], ["tasks", "Tasks"], ["accuracy", "Acc."], ["ttft_p50_s", "TTFT P50 s"], ["ttft_p95_s", "TTFT P95 s"],
                ["task_p50_s", "Task P50 s"], ["task_p95_s", "Task P95 s"], ["tasks_per_min", "Tasks/min"],
                ["prefill_tokens_computed", "Prefill tokens"], ["cache_hit_%", "Cache hit %"]];
  return (
    <Table cols={cols} rows={rows} cell={(r, k) => (
      <td key={k} className={`py-2 pr-4 whitespace-nowrap ${mono(k)}`}>
        {k === "accuracy" ? `${Math.round(100 * r[k])}%`
          : k === "prefill_tokens_computed" && r[k] != null ? r[k].toLocaleString()
          : typeof r[k] === "number" ? fmt(r[k], k === "tasks" ? 0 : 1) : (r[k] ?? "–")}
      </td>
    )} />
  );
}

export function TaskGrid({ perTask }) {
  const tasks = Object.keys(perTask);
  if (!tasks.length) return null;
  const runs = Object.keys(perTask[tasks[0]]);
  return (
    <div className="overflow-x-auto">
      <table className="text-sm">
        <thead>
          <tr>
            <th className="text-left font-medium muted py-2 pr-4">Task</th>
            {runs.map((r) => <th key={r} className="font-medium muted py-2 px-2 mono text-xs whitespace-nowrap">{r}</th>)}
          </tr>
        </thead>
        <tbody>
          {tasks.map((t) => (
            <tr key={t}>
              <td className="py-1.5 pr-4 mono text-xs">{t}</td>
              {runs.map((r) => (
                <td key={r} className="text-center py-1.5 px-2" style={{ color: perTask[t][r] ? "var(--good)" : "var(--bad)" }}
                    aria-label={perTask[t][r] ? "correct" : "wrong"}>
                  {perTask[t][r] ? "✓" : "✗"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
