# ADR 0001 — Record architecture decisions

**Status:** Accepted
**Date:** 2025-08-20

## Context

This is a learning project that will evolve over several phases, and the
decisions made early (tools, data storage, the pipeline/UI boundary) will be
hard to remember later. When revisiting the project — or explaining it to
someone else, or reusing the pattern for a business project — the *reasoning*
behind each choice matters as much as the choice itself.

## Decision

We will keep short Architecture Decision Records (ADRs) in `docs/adr/`, one file
per significant decision, numbered sequentially. Each ADR records the context,
the decision, and the consequences. We use a lightweight format (this file is
the template).

## Consequences

- Every meaningful decision has a written "why" that lives with the code.
- Revisiting the project months later is much faster.
- Writing the ADR forces the decision to actually be made, rather than drifted
  into.
- Small overhead: a few minutes per decision. Worth it.

## Format to copy

```
# ADR NNNN — Short title

**Status:** Proposed | Accepted | Superseded by ADR-XXXX
**Date:** YYYY-MM-DD

## Context
What's the situation and what forces are at play?

## Decision
What did we decide to do?

## Consequences
What becomes easier or harder as a result?
```
