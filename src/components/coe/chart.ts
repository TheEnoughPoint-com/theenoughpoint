// Small geometry helpers for the COE figures. Months are 'YYYY-MM' strings with
// 1-indexed months (as written); mi() converts to a running month count so a
// difference of 1 is one calendar month. No date arithmetic beyond that is done here.
export const mi = (ym: string): number => {
  const [y, m] = ym.split('-').map(Number);
  return y * 12 + (m - 1);
};

export const fmtN = (v: number): string => Math.round(v).toLocaleString('en-SG');
export const round100 = (v: number): string => (Math.round(v / 100) * 100).toLocaleString('en-SG');

/** Map a month and a value into the 0..100 box used by every plot. */
export function scales(x0: string, x1: string, yLo: number, yHi: number) {
  const a = mi(x0), b = mi(x1);
  const X = (m: number) => ((m - a) / (b - a)) * 100;
  const Y = (v: number) => ((yHi - v) / (yHi - yLo)) * 100;
  return { X, Y, xm: (ym: string) => X(mi(ym)) };
}

/** Polyline point strings for a series with gaps (null breaks the line). */
export function segments(pts: Array<[number, number | null]>, X: (m: number) => number, Y: (v: number) => number): string[] {
  const out: string[] = [];
  let cur: string[] = [];
  for (const [m, v] of pts) {
    if (v === null || v === undefined) { if (cur.length > 1) out.push(cur.join(' ')); cur = []; continue; }
    cur.push(`${X(m).toFixed(3)},${Y(v).toFixed(3)}`);
  }
  if (cur.length > 1) out.push(cur.join(' '));
  return out;
}

/** Step line for quarterly values: each value holds from its start month to the month after its end. */
export function steps(rows: Array<{ start: string; end: string; v: number }>, X: (m: number) => number, Y: (v: number) => number): string {
  return rows.map((r) => `${X(mi(r.start)).toFixed(3)},${Y(r.v).toFixed(3)} ${X(mi(r.end) + 1).toFixed(3)},${Y(r.v).toFixed(3)}`).join(' ');
}
