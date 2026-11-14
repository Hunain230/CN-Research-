# Task 1 Repository Cleanup

## Goal

Make the project easier to navigate before running or extending experiments, while preserving the full audit trail and every potentially useful result.

## Steps

1. Read `README.md`, `CONTEXT.md`, `PROJECT_ITERATIONS.md`, `.gitignore`, and all phase specifications before moving or changing anything.
2. Inventory tracked and untracked files, imports, CLI entry points, configs, fixtures, outputs, and dashboards. Identify duplicates by content hash and references, not by filename or age alone.
3. Produce `PROJECT_ITERATIONS.md` describing the active source modules, configs, fixtures, authoritative records, historical outputs, restricted data locations, and dashboard entry points.
4. Identify genuinely unused code only with static reference/import checks. Do not infer that a file is unnecessary because it is old, repeated in a run bundle, or not imported by the main CLI.
5. Make only low-risk organizational/refactoring changes: improve names or docs, consolidate repeated utilities only when behavior and callers are understood, and add compatibility shims if a referenced path changes.
6. Do not delete raw files, `data/derived`, prior outputs, phase records, fixtures, or archived bundle contents. If duplicate material is confusing, document canonical versus historical copies; move only when all links and scripts are updated and the move is reversible.
7. Update the root `README.md` with a short “start here” map and the accurate current research status. Do not rewrite historical reports to match new interpretations.
8. Run the existing relevant self-checks after edits. Do not add dependencies or change metrics/protocol during cleanup.

## Required result

- `PROJECT_ITERATIONS.md`
- A dated cleanup section in `PROJECT_ITERATIONS.md` listing changed or moved files, reasons, evidence, and validation commands
- focused, reviewable cleanup changes in source/docs only

## Acceptance checklist

- [ ] No historical result or raw/restricted dataset was deleted or overwritten.
- [ ] Imports and documented commands still resolve.
- [ ] The root README points to current authoritative records, not only stale status.
- [ ] Cleanup did not silently alter data, models, splits, prompts, metrics, or experiment outputs.
- [ ] Any uncertain “unused” code is retained and documented.

