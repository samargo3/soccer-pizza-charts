import type { PlayerMetric } from "./types";

export function roundPercentile(value: number): number {
  return Math.round(value);
}

/** Pass % is already a rate; everything else is a per-90 value. */
export function formatPer90Line(row: PlayerMetric): string {
  if (row.metric === "pass_completion_pct") {
    return `${row.value_per90.toFixed(1)}%`;
  }
  return `${row.value_per90.toFixed(2)} per 90`;
}

export function ordinal(n: number): string {
  const tens = n % 100;
  if (tens >= 11 && tens <= 13) {
    return `${n}th`;
  }
  switch (n % 10) {
    case 1:
      return `${n}st`;
    case 2:
      return `${n}nd`;
    case 3:
      return `${n}rd`;
    default:
      return `${n}th`;
  }
}

export function wedgeAriaLabel(row: PlayerMetric): string {
  const pct = roundPercentile(row.percentile);
  return `${row.label}, ${row.category}, ${formatPer90Line(row)}, ${ordinal(pct)} percentile`;
}
