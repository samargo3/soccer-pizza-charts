/** Mirrors outputs/json/v3 player-chart JSON. See docs/schema.md. */
export type PlayerMetric = {
  metric: string;
  label: string;
  category: string;
  category_key: string;
  value_per90: number;
  percentile: number;
  higher_is_better: boolean;
};

export type PlayerChartData = {
  schema_version: number;
  player: {
    name: string;
    position: string;
    position_group: string;
    minutes: number;
  };
  competition: {
    league: string;
    season: string;
  };
  peer_group: {
    position_group: string;
    min_minutes: number;
    n_players: number;
    description: string;
  };
  categories: Array<{
    key: string;
    label: string;
    color: string;
  }>;
  metrics: PlayerMetric[];
};

/** Mirrors config/theme.json. Colors live here, not in components. */
export type Theme = {
  name: string;
  mode: string;
  color: {
    background: string;
    surface: string;
    grid: string;
    track: string;
    text_primary: string;
    text_secondary: string;
    text_on_slice: string;
  };
  categories: Record<string, { label: string; color: string }>;
  brand: {
    show: boolean;
    name: string;
    handle: string;
  };
  typography: {
    family: string;
    title_weight: string;
    title_size: number;
    subtitle_size: number;
    slice_label_size: number;
  };
  attribution: {
    required_text: string;
  };
};
