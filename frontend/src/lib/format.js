export const fmt = (v, d = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? "–" : Number(v).toFixed(d);

export const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);

// Categorical series colors, in fixed order (never cycled).
export const SERIES = ["var(--series-1)", "var(--series-2)", "var(--series-3)"];
