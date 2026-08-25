import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { filterPlayers } from "./searchPlayers";
import type { ManifestPlayer, Theme } from "./types";

type PlayerSearchProps = {
  players: ManifestPlayer[];
  selectedSlug: string;
  theme: Theme;
  onSelect: (player: ManifestPlayer) => void;
};

export function PlayerSearch({
  players,
  selectedSlug,
  theme,
  onSelect,
}: PlayerSearchProps) {
  const { color, typography } = theme;
  const fontFamily = `${typography.family}, system-ui, sans-serif`;
  const listId = useId();
  const inputId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = players.find((player) => player.slug === selectedSlug);

  const [query, setQuery] = useState(selected?.name ?? "");
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  const matches = filterPlayers(players, query);
  const highlightIndex =
    matches.length === 0 ? 0 : Math.min(highlight, matches.length - 1);

  useEffect(() => {
    if (selected) {
      setQuery(selected.name);
    }
  }, [selected]);

  useEffect(() => {
    setHighlight(0);
  }, [query]);

  useEffect(() => {
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, []);

  function selectPlayer(player: ManifestPlayer) {
    setQuery(player.name);
    setOpen(false);
    onSelect(player);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!open) {
        setOpen(true);
        return;
      }
      setHighlight((index) =>
        matches.length === 0 ? 0 : Math.min(index + 1, matches.length - 1),
      );
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      setHighlight((index) => Math.max(index - 1, 0));
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      const choice = matches[highlightIndex];
      if (open && choice) {
        selectPlayer(choice);
      }
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      if (selected) {
        setQuery(selected.name);
      }
    }
  }

  const activeId =
    open && matches[highlightIndex]
      ? `${listId}-${matches[highlightIndex].slug}`
      : undefined;

  return (
    <div
      ref={rootRef}
      style={{
        width: "min(100%, 720px)",
        padding: "20px 16px 8px",
        fontFamily,
        position: "relative",
      }}
    >
      <label
        htmlFor={inputId}
        style={{
          display: "block",
          marginBottom: 8,
          color: color.text_secondary,
          fontSize: 13,
        }}
      >
        Search players
      </label>
      <input
        id={inputId}
        type="text"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={activeId}
        value={query}
        placeholder="Type a name"
        autoComplete="off"
        spellCheck={false}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        style={{
          width: "100%",
          boxSizing: "border-box",
          padding: "10px 12px",
          borderRadius: 8,
          border: `1px solid ${color.grid}`,
          background: color.surface,
          color: color.text_primary,
          fontFamily,
          fontSize: 16,
          boxShadow: open ? `0 0 0 1px ${color.text_secondary}` : undefined,
        }}
      />
      {open ? (
        <ul
          id={listId}
          role="listbox"
          style={{
            listStyle: "none",
            margin: "4px 0 0",
            padding: 4,
            position: "absolute",
            left: 16,
            right: 16,
            zIndex: 2,
            maxHeight: 280,
            overflowY: "auto",
            borderRadius: 8,
            border: `1px solid ${color.grid}`,
            background: color.surface,
          }}
        >
          {matches.length === 0 ? (
            <li
              role="status"
              style={{
                padding: "10px 12px",
                color: color.text_secondary,
                fontSize: 14,
              }}
            >
              No players found
            </li>
          ) : (
            matches.map((player, index) => {
              const isActive = index === highlightIndex;
              return (
                <li
                  key={player.slug}
                  id={`${listId}-${player.slug}`}
                  role="option"
                  aria-selected={isActive}
                  onMouseEnter={() => setHighlight(index)}
                  ref={
                    isActive
                      ? (node) => {
                          node?.scrollIntoView({ block: "nearest" });
                        }
                      : undefined
                  }
                  onMouseDown={(event) => {
                    event.preventDefault();
                    selectPlayer(player);
                  }}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 6,
                    cursor: "pointer",
                    background: isActive ? color.track : "transparent",
                    color: color.text_primary,
                  }}
                >
                  <div style={{ fontSize: 14 }}>{player.name}</div>
                  <div style={{ fontSize: 12, color: color.text_secondary }}>
                    {player.position} · {Math.round(player.minutes).toLocaleString("en-US")}{" "}
                    minutes
                  </div>
                </li>
              );
            })
          )}
        </ul>
      ) : null}
    </div>
  );
}
