import { useRef, useState, type MouseEvent } from "react";
import {
  formatPer90Line,
  ordinal,
  roundPercentile,
  wedgeAriaLabel,
} from "./formatMetric";
import type { PlayerChartData, PlayerMetric, Theme } from "./types";
import {
  holeRadius,
  labelRadius,
  labelRotationDeg,
  makeRadiusScale,
  PERCENTILE_MAX,
  polarToXY,
  sliceAngles,
  wedgePath,
} from "./pizzaGeometry";

type PizzaChartProps = {
  player: PlayerChartData;
  theme: Theme;
};

type Pointer = { x: number; y: number };

const VIEW_W = 1000;
const VIEW_H = 1300;
const CX = 500;
const CY = 560;
const MAX_RADIUS = 310;
const GRID_STEPS = [20, 40, 60, 80, 100];
const FONT_SCALE = 1.6;
const TOOLTIP_W = 240;
const TOOLTIP_H = 108;

function categoryColor(theme: Theme, categoryKey: string): string {
  return theme.categories[categoryKey]?.color ?? theme.color.track;
}

function peerNoun(positionGroup: string): string {
  return positionGroup.endsWith("s") ? positionGroup : `${positionGroup}s`;
}

function clientToViewBox(
  svg: SVGSVGElement,
  clientX: number,
  clientY: number,
): Pointer {
  const rect = svg.getBoundingClientRect();
  return {
    x: ((clientX - rect.left) / rect.width) * VIEW_W,
    y: ((clientY - rect.top) / rect.height) * VIEW_H,
  };
}

function clampTooltip(x: number, y: number): Pointer {
  const pad = 12;
  let tx = x + 18;
  let ty = y + 18;
  if (tx + TOOLTIP_W > VIEW_W - pad) tx = x - TOOLTIP_W - 12;
  if (ty + TOOLTIP_H > VIEW_H - pad) ty = y - TOOLTIP_H - 12;
  tx = Math.max(pad, Math.min(tx, VIEW_W - TOOLTIP_W - pad));
  ty = Math.max(pad, Math.min(ty, VIEW_H - TOOLTIP_H - pad));
  return { x: tx, y: ty };
}

function wedgeAnchor(index: number, count: number): Pointer {
  const { midAngle } = sliceAngles(index, count);
  return polarToXY(CX, CY, midAngle, MAX_RADIUS * 0.62);
}

export function PizzaChart({ player, theme }: PizzaChartProps) {
  const { color, typography, brand, attribution } = theme;
  const metrics = player.metrics;
  const n = metrics.length;
  const inner = holeRadius(MAX_RADIUS);
  const radiusOf = makeRadiusScale(MAX_RADIUS);
  const outerLabelR = labelRadius(MAX_RADIUS);
  const fontFamily = `${typography.family}, system-ui, sans-serif`;
  const titleSize = typography.title_size * FONT_SCALE;
  const subtitleSize = typography.subtitle_size * FONT_SCALE;
  const sliceSize = typography.slice_label_size * FONT_SCALE;

  const minutes = Math.round(player.player.minutes).toLocaleString("en-US");
  const subtitle = `${player.competition.league} ${player.competition.season}  ·  ${player.player.position_group}  ·  ${minutes} minutes`;
  const peerLine = `Percentile rank vs ${player.peer_group.n_players} ${peerNoun(player.peer_group.position_group)} with ≥ ${player.peer_group.min_minutes} minutes`;

  const legend = Object.entries(theme.categories).map(([key, meta]) => ({
    key,
    label: meta.label,
    color: meta.color,
  }));
  const legendSwatch = 14;
  const legendSwatchGap = 8;
  const legendItemGap = 40;
  const legendWidths = legend.map(
    (item) =>
      legendSwatch + legendSwatchGap + item.label.length * subtitleSize * 0.56,
  );
  const legendTotal =
    legendWidths.reduce((sum, w) => sum + w, 0) +
    legendItemGap * (legend.length - 1);
  let legendX = (VIEW_W - legendTotal) / 2;
  const legendItems = legend.map((item, i) => {
    const x = legendX;
    legendX += legendWidths[i] + legendItemGap;
    return { ...item, x };
  });
  const legendY = 1040;

  const svgRef = useRef<SVGSVGElement>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const [focused, setFocused] = useState<number | null>(null);
  const [pointer, setPointer] = useState<Pointer | null>(null);

  const activeIndex = hovered ?? focused;
  const activeRow = activeIndex !== null ? metrics[activeIndex] : null;
  const tooltipPos =
    activeIndex === null
      ? null
      : clampTooltip(
          hovered !== null && pointer
            ? pointer.x
            : wedgeAnchor(activeIndex, n).x,
          hovered !== null && pointer
            ? pointer.y
            : wedgeAnchor(activeIndex, n).y,
        );

  function onWedgeMouseMove(index: number, event: MouseEvent<SVGPathElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    setHovered(index);
    setPointer(clientToViewBox(svg, event.clientX, event.clientY));
  }

  function onWedgeMouseLeave() {
    setHovered(null);
    setPointer(null);
  }

  function onWedgeFocus(index: number) {
    setFocused(index);
  }

  function onWedgeBlur() {
    setFocused(null);
  }

  function wedgeOpacity(index: number): number {
    if (activeIndex === null || activeIndex === index) return 1;
    return 0.38;
  }

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      role="group"
      aria-label={`${player.player.name} pizza chart`}
      style={{ width: "min(100%, 720px)", height: "auto", display: "block" }}
    >
      <rect width={VIEW_W} height={VIEW_H} fill={color.background} />

      <text
        x={VIEW_W / 2}
        y={56}
        textAnchor="middle"
        fill={color.text_primary}
        fontFamily={fontFamily}
        fontSize={titleSize}
        fontWeight={typography.title_weight}
      >
        {player.player.name}
      </text>
      <text
        x={VIEW_W / 2}
        y={92}
        textAnchor="middle"
        fill={color.text_secondary}
        fontFamily={fontFamily}
        fontSize={subtitleSize}
      >
        {subtitle}
      </text>
      <text
        x={VIEW_W / 2}
        y={118}
        textAnchor="middle"
        fill={color.text_secondary}
        fontFamily={fontFamily}
        fontSize={subtitleSize}
      >
        {peerLine}
      </text>

      <g transform={`translate(${CX}, ${CY})`} pointerEvents="none">
        {metrics.map((row, i) => {
          const { startAngle, endAngle } = sliceAngles(i, n);
          return (
            <path
              key={`track-${row.metric}`}
              d={wedgePath(inner, MAX_RADIUS, startAngle, endAngle)}
              fill={color.track}
            />
          );
        })}

        {metrics.map((row, i) => {
          const { startAngle, endAngle } = sliceAngles(i, n);
          const shown = roundPercentile(row.percentile);
          const isActive = activeIndex === i;
          return (
            <path
              key={`slice-${row.metric}`}
              d={wedgePath(inner, radiusOf(shown), startAngle, endAngle)}
              fill={categoryColor(theme, row.category_key)}
              stroke={isActive ? color.text_primary : color.background}
              strokeWidth={isActive ? 2.5 : 1.5}
              opacity={wedgeOpacity(i)}
            />
          );
        })}

        {GRID_STEPS.map((step) => (
          <circle
            key={`ring-${step}`}
            r={radiusOf(step)}
            fill="none"
            stroke={color.grid}
            strokeWidth={1}
            strokeDasharray={step === PERCENTILE_MAX ? undefined : "6 6"}
          />
        ))}

        {metrics.map((row, i) => {
          const { endAngle } = sliceAngles(i, n);
          const a = polarToXY(0, 0, endAngle, inner);
          const b = polarToXY(0, 0, endAngle, MAX_RADIUS);
          return (
            <line
              key={`spoke-${row.metric}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={color.grid}
              strokeWidth={1}
            />
          );
        })}

        <circle r={inner} fill={color.background} />
      </g>

      {metrics.map((row, i) => {
        const { midAngle } = sliceAngles(i, n);
        const pos = polarToXY(CX, CY, midAngle, outerLabelR);
        const rotate = labelRotationDeg(i, n);
        return (
          <text
            key={`label-${row.metric}`}
            x={pos.x}
            y={pos.y}
            fill={color.text_primary}
            fontFamily={fontFamily}
            fontSize={sliceSize}
            textAnchor="middle"
            dominantBaseline="middle"
            transform={`rotate(${rotate} ${pos.x} ${pos.y})`}
            opacity={wedgeOpacity(i)}
            pointerEvents="none"
          >
            {row.label}
          </text>
        );
      })}

      {metrics.map((row, i) => {
        const { midAngle } = sliceAngles(i, n);
        const value = roundPercentile(row.percentile);
        const pos = polarToXY(CX, CY, midAngle, radiusOf(value));
        const fill = categoryColor(theme, row.category_key);
        const text = String(value);
        const padX = 7;
        const padY = 4;
        const w = text.length * sliceSize * 0.72 + padX * 2;
        const h = sliceSize + padY * 2;
        return (
          <g
            key={`chip-${row.metric}`}
            transform={`translate(${pos.x}, ${pos.y})`}
            opacity={wedgeOpacity(i)}
            pointerEvents="none"
          >
            <rect
              x={-w / 2}
              y={-h / 2}
              width={w}
              height={h}
              rx={4}
              fill={fill}
            />
            <text
              fill={color.text_on_slice}
              fontFamily={fontFamily}
              fontSize={sliceSize}
              textAnchor="middle"
              dominantBaseline="central"
            >
              {text}
            </text>
          </g>
        );
      })}

      <g transform={`translate(${CX}, ${CY})`}>
        {metrics.map((row, i) => {
          const { startAngle, endAngle } = sliceAngles(i, n);
          const isFocused = focused === i;
          return (
            <path
              key={`hit-${row.metric}`}
              data-metric={row.metric}
              d={wedgePath(inner, MAX_RADIUS, startAngle, endAngle)}
              fill="transparent"
              stroke={isFocused ? color.text_primary : "none"}
              strokeWidth={isFocused ? 2 : 0}
              tabIndex={0}
              role="button"
              aria-label={wedgeAriaLabel(row)}
              style={{ cursor: "pointer", outline: "none" }}
              onMouseEnter={(event) => onWedgeMouseMove(i, event)}
              onMouseMove={(event) => onWedgeMouseMove(i, event)}
              onMouseLeave={onWedgeMouseLeave}
              onFocus={() => onWedgeFocus(i)}
              onBlur={onWedgeBlur}
            />
          );
        })}
      </g>

      {activeRow && tooltipPos ? (
        <WedgeTooltip
          x={tooltipPos.x}
          y={tooltipPos.y}
          row={activeRow}
          theme={theme}
          fontFamily={fontFamily}
          fontSize={subtitleSize}
        />
      ) : null}

      {legendItems.map((item) => (
        <g key={item.key} pointerEvents="none">
          <rect
            x={item.x}
            y={legendY - 8}
            width={legendSwatch}
            height={legendSwatch}
            rx={2}
            fill={item.color}
          />
          <text
            x={item.x + legendSwatch + legendSwatchGap}
            y={legendY + 4}
            fill={color.text_primary}
            fontFamily={fontFamily}
            fontSize={subtitleSize}
          >
            {item.label}
          </text>
        </g>
      ))}

      <text
        x={VIEW_W / 2}
        y={1148}
        textAnchor="middle"
        fill={color.text_secondary}
        fontFamily={fontFamily}
        fontSize={subtitleSize * 0.85}
        pointerEvents="none"
      >
        {attribution.required_text}
      </text>

      {brand.show ? (
        <text
          x={VIEW_W - 36}
          y={VIEW_H - 28}
          textAnchor="end"
          fill={color.text_secondary}
          fontFamily={fontFamily}
          fontSize={subtitleSize * 0.75}
          pointerEvents="none"
        >
          {brand.handle}
        </text>
      ) : null}
    </svg>
  );
}

function WedgeTooltip({
  x,
  y,
  row,
  theme,
  fontFamily,
  fontSize,
}: {
  x: number;
  y: number;
  row: PlayerMetric;
  theme: Theme;
  fontFamily: string;
  fontSize: number;
}) {
  const pct = roundPercentile(row.percentile);
  const { color } = theme;
  return (
    <g
      data-tooltip="wedge"
      transform={`translate(${x}, ${y})`}
      pointerEvents="none"
    >
      <rect
        width={TOOLTIP_W}
        height={TOOLTIP_H}
        rx={8}
        fill={color.surface}
        stroke={color.grid}
        strokeWidth={1}
      />
      <text
        x={14}
        y={26}
        fill={color.text_primary}
        fontFamily={fontFamily}
        fontSize={fontSize * 1.05}
        fontWeight="bold"
      >
        {row.label}
      </text>
      <text
        x={14}
        y={48}
        fill={color.text_secondary}
        fontFamily={fontFamily}
        fontSize={fontSize * 0.9}
      >
        {row.category}
      </text>
      <text
        x={14}
        y={72}
        fill={color.text_primary}
        fontFamily={fontFamily}
        fontSize={fontSize}
      >
        {formatPer90Line(row)}
      </text>
      <text
        x={14}
        y={94}
        fill={color.text_secondary}
        fontFamily={fontFamily}
        fontSize={fontSize * 0.9}
      >
        {ordinal(pct)} percentile
      </text>
    </g>
  );
}
