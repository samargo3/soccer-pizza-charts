import { arc, scaleLinear } from "d3";

/**
 * Hole size matches mplsoccer PyPizza `inner_circle_size=8` at rmax=100
 * (`set_rorigin(-8)` in the Python renderer). Percentile 0 sits at the hole
 * edge, 100 at the outer ring — linear in between.
 */
export const INNER_CIRCLE_SIZE = 8;
export const PERCENTILE_MAX = 100;
/** Parameter labels sit just outside the 100-ring, like PyPizza param_location. */
export const PARAM_LOCATION = 108;

export function holeRadius(maxRadius: number): number {
  return (INNER_CIRCLE_SIZE / (PERCENTILE_MAX + INNER_CIRCLE_SIZE)) * maxRadius;
}

export function makeRadiusScale(maxRadius: number) {
  return scaleLinear()
    .domain([0, PERCENTILE_MAX])
    .range([holeRadius(maxRadius), maxRadius]);
}

export function labelRadius(maxRadius: number): number {
  return (
    ((PARAM_LOCATION + INNER_CIRCLE_SIZE) /
      (PERCENTILE_MAX + INNER_CIRCLE_SIZE)) *
    maxRadius
  );
}

/**
 * Equal wedges, clockwise from 12 o'clock. Mid-angles are centered on the
 * clock positions so the first metric straddles 12 o'clock, matching PyPizza
 * (`theta_zero_location='N'`, bar align center).
 */
export function sliceAngles(
  index: number,
  count: number,
): { startAngle: number; endAngle: number; midAngle: number } {
  const step = (2 * Math.PI) / count;
  const midAngle = index * step;
  return {
    startAngle: midAngle - step / 2,
    endAngle: midAngle + step / 2,
    midAngle,
  };
}

export function wedgePath(
  innerRadius: number,
  outerRadius: number,
  startAngle: number,
  endAngle: number,
): string {
  return (
    arc()({
      innerRadius,
      outerRadius,
      startAngle,
      endAngle,
    }) ?? ""
  );
}

/** d3.arc 0° is 12 o'clock, clockwise — same as the polar pizza. */
export function polarToXY(
  cx: number,
  cy: number,
  angle: number,
  radius: number,
): { x: number; y: number } {
  return {
    x: cx + radius * Math.sin(angle),
    y: cy - radius * Math.cos(angle),
  };
}

/** Tangent labels, flipped in the lower half so they stay readable (PyPizza). */
export function labelRotationDeg(index: number, count: number): number {
  let rotation = ((2 * Math.PI) / count) * index;
  if (rotation > Math.PI / 2 && rotation < (Math.PI / 2) * 3) {
    rotation += Math.PI;
  }
  return -((rotation * 180) / Math.PI);
}
