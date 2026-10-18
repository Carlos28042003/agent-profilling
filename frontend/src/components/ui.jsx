export function Stat({ label, value, unit, hint }) {
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wide muted">{label}</div>
      <div className="mt-1 text-3xl font-semibold">
        {value}
        <span className="text-lg secondary ml-0.5">{unit}</span>
      </div>
      {hint && <div className="mt-1 text-xs secondary">{hint}</div>}
    </div>
  );
}

export function Legend({ items }) {
  return (
    <div className="flex flex-wrap gap-4 text-xs secondary">
      {items.map(([label, color]) => (
        <span key={label} className="inline-flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm" style={{ background: color }} />
          {label}
        </span>
      ))}
    </div>
  );
}

export function Tooltip({ tip }) {
  if (!tip) return null;
  return (
    <div
      className="pointer-events-none absolute z-10 card px-3 py-2 text-xs shadow-lg"
      style={{ left: tip.x, top: tip.y, transform: "translate(-50%, calc(-100% - 10px))", minWidth: 150 }}
    >
      <div className="font-medium mb-1">{tip.title}</div>
      {tip.rows.map(([k, v, c]) => (
        <div key={k} className="flex justify-between gap-4">
          <span className="inline-flex items-center gap-1.5 secondary">
            {c && <span className="inline-block w-2 h-2 rounded-sm" style={{ background: c }} />}
            {k}
          </span>
          <span className="num">{v}</span>
        </div>
      ))}
    </div>
  );
}

export function Section({ title, subtitle, children, className = "" }) {
  return (
    <section className={`card p-5 min-w-0 ${className}`}>
      <h3 className="font-semibold">{title}</h3>
      {subtitle && <p className="text-xs muted mt-0.5">{subtitle}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}
