import { useEffect, useState } from "react";
import { PizzaChart } from "./PizzaChart";
import { PlayerSearch } from "./PlayerSearch";
import type { ManifestPlayer, PlayerChartData, SearchManifest, Theme } from "./types";

/** Pipeline JSON served from public/. Manual copy for now; Phase 4 will automate it. */
const DATA_DIR = "/data/json/v3/la_liga_2015_16";
const MANIFEST_URL = `${DATA_DIR}/index.json`;
const THEME_URL = "/config/theme.json";
const DEFAULT_SLUG = "luis_alberto_suarez_diaz";

async function fetchJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    throw new Error(`Couldn’t load ${url} (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export default function App() {
  const [theme, setTheme] = useState<Theme | null>(null);
  const [players, setPlayers] = useState<ManifestPlayer[]>([]);
  const [selectedSlug, setSelectedSlug] = useState(DEFAULT_SLUG);
  const [player, setPlayer] = useState<PlayerChartData | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [playerError, setPlayerError] = useState<string | null>(null);
  const [playerLoading, setPlayerLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    void fetchJson<Theme>(THEME_URL, controller.signal)
      .then(setTheme)
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setBootError(err instanceof Error ? err.message : String(err));
      });
    void fetchJson<SearchManifest>(MANIFEST_URL, controller.signal)
      .then((manifest) => setPlayers(manifest.players))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setBootError(err instanceof Error ? err.message : String(err));
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setPlayerLoading(true);
    setPlayerError(null);
    void fetchJson<PlayerChartData>(`${DATA_DIR}/${selectedSlug}.json`, controller.signal)
      .then((data) => {
        setPlayer(data);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setPlayerError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setPlayerLoading(false);
        }
      });
    return () => controller.abort();
  }, [selectedSlug]);

  if (bootError && !theme) {
    return <p>Failed to load the app: {bootError}</p>;
  }
  if (!theme) {
    return <p>Loading…</p>;
  }

  const { color, typography } = theme;
  const fontFamily = `${typography.family}, system-ui, sans-serif`;

  return (
    <div
      style={{
        minHeight: "100vh",
        margin: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        background: color.background,
        fontFamily,
        color: color.text_primary,
      }}
    >
      {bootError && players.length === 0 ? (
        <p
          role="alert"
          style={{
            margin: "8px 16px",
            color: color.text_secondary,
            fontSize: 14,
          }}
        >
          Couldn’t load the player list. {bootError}
        </p>
      ) : null}

      {players.length > 0 ? (
        <PlayerSearch
          players={players}
          selectedSlug={selectedSlug}
          theme={theme}
          onSelect={(entry) => setSelectedSlug(entry.slug)}
        />
      ) : null}

      {playerLoading ? (
        <p
          role="status"
          style={{
            margin: "4px 0",
            color: color.text_secondary,
            fontSize: 14,
          }}
        >
          Loading player…
        </p>
      ) : null}

      {playerError ? (
        <p
          role="alert"
          style={{
            margin: "4px 16px",
            color: color.text_secondary,
            fontSize: 14,
          }}
        >
          Couldn’t load that player. {playerError}
        </p>
      ) : null}

      {player ? (
        <PizzaChart key={selectedSlug} player={player} theme={theme} />
      ) : null}
    </div>
  );
}
