# Argo FC Analytics — Agent Rules

This repo didn't have a root `AGENTS.md` before; day-to-day conventions
(architecture, pipeline structure, frontend/data contract) live in
`.cursor/rules/*.mdc` and still apply. This file exists for the one
convention that needs to hold across tools, not just Cursor: session-end
hygiene.

## Session-end rules

- STATUS.md is updated in the same commit as the docs/dev-log.md entry.
  A session is not clean until both are current.

  <!-- Note: this repo's running log is `docs/log.md`, not `docs/dev-log.md` —
       the rule above refers to whichever of the two is this repo's dev log. -->
