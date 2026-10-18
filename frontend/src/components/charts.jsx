import { useRef, useState } from "react";
import { fmt, SERIES } from "../lib/format.js";
import { Legend, Tooltip } from "./ui.jsx";

/** Prompt tokens vs. cached tokens for each step of one task. */
export function StepTokensChart({ steps }) {
  const [tip, setTip] = useState(null);
  const wrap = useRef(null);
  if (!steps || !steps.length) return <div className="text-sm muted">No steps yet.</div>;
  const W = 640, H = 240, m = { t: 12, r: 8, b: 30, l: 48 };
  const maxY = Math.max(...steps.map((s) => s.prompt_tokens || 0), 1);
  const niceMax = Math.ceil(maxY / 500) * 500;
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const band = iw / steps.length, bw = Math.min(22, (band - 10) / 2);
  const y = (v) => m.t + ih - (v / niceMax) * ih;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(niceMax * f));
  const show = (e, s) => {
    const r = wrap.current.getBoundingClientRect();
    setTip({
      x: e.clientX - r.left,
      y: e.clientY - r.top,
      title: `Step ${s.index}${s.tool ? ` · ${s.tool}` : " · final answer"}`,
      rows: [
        ["Prompt tokens", s.prompt_tokens ?? "–", "var(--series-1)"],
        ["Cached tokens", s.cached_tokens ?? "–", "var(--series-2)"],
        ["Cache hit", s.prompt_tokens && s.cached_tokens != null ? `${Math.round((100 * s.cached_tokens) / s.prompt_tokens)}%` : "–"],
        ["TTFT", `${fmt(s.llm_ttft_s, 2)} s`],
        ...(s.truncated ? [["Context", "truncated"]] : []),
      ],
    });
  };
  return (
    <div ref={wrap} className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Prompt tokens and cached tokens per step">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={m.l} x2={W - m.r} y1={y(t)} y2={y(t)} stroke="var(--grid)" />
            <text x={m.l - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize="11" fill="var(--text-muted)">{t.toLocaleString()}</text>
          </g>
        ))}
        {steps.map((s, i) => {
          const x0 = m.l + i * band + band / 2 - bw - 1;
          const p = s.prompt_tokens || 0, c = s.cached_tokens || 0;
          return (
            <g key={i} onMouseMove={(e) => show(e, s)} onMouseLeave={() => setTip(null)}>
              <rect x={m.l + i * band} y={m.t} width={band} height={ih} fill="transparent" />
              <rect x={x0} y={y(p)} width={bw} height={Math.max(0, m.t + ih - y(p))} rx="3" fill="var(--series-1)" />
              <rect x={x0 + bw + 2} y={y(c)} width={bw} height={Math.max(0, m.t + ih - y(c))} rx="3" fill="var(--series-2)" />
              {s.truncated && <text x={x0 + bw} y={y(p) - 6} textAnchor="middle" fontSize="11" fill="var(--bad)">✂</text>}
              <text x={m.l + i * band + band / 2} y={H - 10} textAnchor="middle" fontSize="11" fill="var(--text-muted)">{s.index}</text>
            </g>
          );
        })}
        <line x1={m.l} x2={W - m.r} y1={m.t + ih} y2={m.t + ih} stroke="var(--text-muted)" />
      </svg>
      <Tooltip tip={tip} />
    </div>
  );
}

/** Share of task time in LLM / tools / overhead, one bar per run (older experiments). */
export function TimeBreakdown({ runs }) {
  const [tip, setTip] = useState(null);
  const wrap = useRef(null);
  const parts = [["LLM", "llm_%", "var(--series-1)"], ["Tools", "tool_%", "var(--series-2)"], ["Overhead", "overhead_%", "var(--series-3)"]];
  return (
    <div className="space-y-3">
      <Legend items={parts.map(([l, , c]) => [l, c])} />
      <div ref={wrap} className="relative space-y-2">
        {runs.map((r) => (
          <div key={r.run} className="flex items-center gap-3">
            <div className="w-28 shrink-0 text-xs secondary mono truncate" title={r.run}>{r.run}</div>
            <div
              className="flex-1 flex h-5 gap-[2px]"
              onMouseMove={(e) => {
                const b = wrap.current.getBoundingClientRect();
                setTip({ x: e.clientX - b.left, y: e.clientY - b.top, title: `${r.run} · ${r.model || ""}`,
                         rows: parts.map(([l, k, c]) => [l, `${fmt(r[k])}%`, c]) });
              }}
              onMouseLeave={() => setTip(null)}
            >
              {parts.map(([l, k, c]) => r[k] > 0.05 && (
                <div key={l} className="first:rounded-l last:rounded-r" style={{ width: `${r[k]}%`, background: c }} />
              ))}
            </div>
            <div className="w-12 text-right text-xs num secondary">{fmt(r["llm_%"], 0)}%</div>
          </div>
        ))}
        <Tooltip tip={tip} />
      </div>
    </div>
  );
}

/** Prefill / decode / tools / overhead split, one bar per workload (Week 3+). */
export function TimeSplit({ split }) {
  const parts = [["Prefill (TTFT)", "prefill (TTFT)", "var(--series-1)"], ["Decode", "decode", "var(--series-2)"],
                 ["Tools", "tools", "var(--series-3)"], ["Overhead", "overhead", "var(--series-4)"]];
  return (
    <div className="space-y-3">
      <Legend items={parts.map(([l, , c]) => [l, c])} />
      {Object.entries(split).map(([run, v]) => (
        <div key={run} className="flex items-center gap-3">
          <div className="w-24 shrink-0 text-xs secondary mono truncate" title={run}>{run}</div>
          <div className="flex-1 flex h-6 gap-[2px]">
            {parts.map(([l, k, c]) => v[k] > 0.3 && (
              <div key={k} title={`${l}: ${fmt(v[k])}%`}
                   className="flex items-center justify-center text-[11px] text-white first:rounded-l last:rounded-r"
                   style={{ width: `${v[k]}%`, background: c }}>
                {v[k] >= 9 ? `${Math.round(v[k])}%` : ""}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Line chart with optional 25th-75th percentile band, or a step line for CDFs.
 * series: [{ name, points: [{ x, y, lo?, hi? }] }]
 */
export function LineChart({ series, xLabel, yLabel, yMax, band, stepLine,
                            fmtY = (v) => v.toLocaleString(), fmtX = (v) => v }) {
  const [tip, setTip] = useState(null);
  const wrap = useRef(null);
  const W = 640, H = 260, m = { t: 12, r: 16, b: 38, l: 52 };
  const all = series.flatMap((s) => s.points);
  if (!all.length) return null;
  const xMin = stepLine ? 0 : Math.min(...all.map((p) => p.x));
  const xMax = Math.max(...all.map((p) => p.x));
  const top = yMax ?? Math.max(...all.map((p) => p.hi ?? p.y)) * 1.08;
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const x = (v) => m.l + (xMax === xMin ? iw / 2 : ((v - xMin) / (xMax - xMin)) * iw);
  const y = (v) => m.t + ih - (v / top) * ih;
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => top * f);
  const xTicks = stepLine
    ? [0, 0.25, 0.5, 0.75, 1].map((f) => xMin + f * (xMax - xMin))
    : [...new Set(all.map((p) => p.x))].filter((v, i, a) => a.length <= 12 || i % Math.ceil(a.length / 8) === 0);
  const path = (pts) => stepLine
    ? pts.map((p, i) => (i === 0 ? `M${x(p.x)},${y(0)} V${y(p.y)}` : `H${x(p.x)} V${y(p.y)}`)).join(" ")
    : pts.map((p, i) => `${i ? "L" : "M"}${x(p.x)},${y(p.y)}`).join(" ");
  const onMove = (e) => {
    const r = wrap.current.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const rows = series.map((s, i) => {
      const near = s.points.reduce((a, p) => (Math.abs(x(p.x) - px) < Math.abs(x(a.x) - px) ? p : a), s.points[0]);
      return [s.name, `${fmtY(near.y)} @ ${fmtX(near.x)}`, SERIES[i]];
    });
    setTip({ x: e.clientX - r.left, y: e.clientY - r.top, title: xLabel, rows });
  };
  return (
    <div ref={wrap} className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" onMouseMove={onMove} onMouseLeave={() => setTip(null)}>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={m.l} x2={W - m.r} y1={y(t)} y2={y(t)} stroke="var(--grid)" />
            <text x={m.l - 8} y={y(t)} dy="0.32em" textAnchor="end" fontSize="11" fill="var(--text-muted)">{fmtY(Math.round(t))}</text>
          </g>
        ))}
        {band && series.map((s, i) => s.points[0]?.lo !== undefined && (
          <path key={`band${i}`} fill={SERIES[i]} opacity="0.12"
                d={`${s.points.map((p, j) => `${j ? "L" : "M"}${x(p.x)},${y(p.hi)}`).join(" ")} ${[...s.points].reverse().map((p) => `L${x(p.x)},${y(p.lo)}`).join(" ")} Z`} />
        ))}
        {series.map((s, i) => (
          <g key={i}>
            <path d={path(s.points)} fill="none" stroke={SERIES[i]} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
            {!stepLine && s.points.map((p, j) => (
              <circle key={j} cx={x(p.x)} cy={y(p.y)} r="4" fill={SERIES[i]} stroke="var(--surface-1)" strokeWidth="2" />
            ))}
          </g>
        ))}
        <line x1={m.l} x2={W - m.r} y1={m.t + ih} y2={m.t + ih} stroke="var(--text-muted)" />
        {xTicks.map((v) => (
          <text key={v} x={x(v)} y={H - 20} textAnchor="middle" fontSize="11" fill="var(--text-muted)">{fmtX(v)}</text>
        ))}
        <text x={m.l + iw / 2} y={H - 4} textAnchor="middle" fontSize="11" fill="var(--text-secondary)">{xLabel}</text>
        <text x={12} y={m.t + ih / 2} textAnchor="middle" fontSize="11" fill="var(--text-secondary)"
              transform={`rotate(-90 12 ${m.t + ih / 2})`}>{yLabel}</text>
      </svg>
      <Tooltip tip={tip} />
    </div>
  );
}

/** Horizontal bars of throughput (tasks per minute), one per setup. */
export function ThroughputBars({ rows }) {
  const maxT = Math.max(...rows.map((r) => r.tasks_per_min || 0), 1);
  return (
    <div className="space-y-2">
      {rows.map((r) => (
        <div key={r.run} className="flex items-center gap-3">
          <div className="w-28 shrink-0 text-xs secondary mono truncate">{r.run}</div>
          <div className="flex-1">
            <div className="h-5" style={{ width: `${(100 * (r.tasks_per_min || 0)) / maxT}%`, background: "var(--series-1)", borderRadius: "0 4px 4px 0" }} />
          </div>
          <div className="w-12 text-right text-xs num secondary">{fmt(r.tasks_per_min)}</div>
        </div>
      ))}
    </div>
  );
}
