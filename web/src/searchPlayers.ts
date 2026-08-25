import type { ManifestPlayer } from "./types";

/** Case- and accent-insensitive fold so "suarez" matches "Suárez". */
export function foldForSearch(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/\p{M}+/gu, "")
    .toLowerCase();
}

export function filterPlayers(
  players: ManifestPlayer[],
  query: string,
): ManifestPlayer[] {
  const needle = foldForSearch(query.trim());
  if (!needle) {
    return players;
  }
  return players.filter((player) => foldForSearch(player.name).includes(needle));
}
