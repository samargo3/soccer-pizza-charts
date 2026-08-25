import { useEffect, useState } from "react";
import { PizzaChart } from "./PizzaChart";
import type { PlayerChartData, Theme } from "./types";

/** Pipeline JSON served from public/. Manual copy for now; Phase 4 will automate it. */
const PLAYER_JSON_URL =
  "/data/json/v3/la_liga_2015_16/luis_alberto_suarez_diaz.json";
const THEME_URL = "/config/theme.json";

export default function App() {
  const [player, setPlayer] = useState<PlayerChartData | null>(null);
  const [theme, setTheme] = useState<Theme | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([
      fetch(PLAYER_JSON_URL).then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status} for ${PLAYER_JSON_URL}`);
        }
        return response.json() as Promise<PlayerChartData>;
      }),
      fetch(THEME_URL).then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status} for ${THEME_URL}`);
        }
        return response.json() as Promise<Theme>;
      }),
    ])
      .then(([playerData, themeData]) => {
        setPlayer(playerData);
        setTheme(themeData);
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err)),
      );
  }, []);

  if (error) {
    return <p>Failed to load chart data: {error}</p>;
  }
  if (!player || !theme) {
    return <p>Loading…</p>;
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        margin: 0,
        display: "flex",
        justifyContent: "center",
        background: theme.color.background,
      }}
    >
      <PizzaChart player={player} theme={theme} />
    </div>
  );
}
