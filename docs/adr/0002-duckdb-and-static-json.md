# ADR 0002 — Use DuckDB/Parquet internally and static JSON for serving

**Status:** Accepted
**Date:** 2025-08-20

## Context

The pipeline needs somewhere to store data between stages, and the UI needs a
way to read the final computed data. Options considered:

- A running database + an API server the UI queries live.
- A static approach: files on disk internally, static JSON served to the UI.

This is a single-author learning project with data that refreshes on a schedule
(weekly), not continuously. There is no need for live queries or a running
backend.

## Decision

- **Between pipeline stages:** store data as Parquet files, queried with DuckDB.
  DuckDB is a single-file, zero-server engine that reads Parquet directly and is
  excellent for local analytical work.
- **For serving the UI:** export the final computed table as static JSON files,
  one per league. The UI fetches these static files. No API, no server.

## Consequences

- Much simpler: no database server to run, secure, or deploy.
- The UI can be hosted as static files (GitHub Pages / Vercel) and just fetch
  JSON — cheap and easy to deploy.
- Automation is straightforward: a scheduled job re-runs the pipeline, commits
  fresh JSON, and triggers a redeploy.
- Trade-off: no live/ad-hoc querying from the UI. Fine for this use case; the
  data is precomputed and read-only.
- This mirrors a very common real-world analytics pattern (batch pipeline →
  precomputed artifacts → dashboard), which supports the goal of generalizing
  the approach later.
