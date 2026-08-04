# GeoForge Studio Agent Guide

## Scope and safety

- Work only inside this repository. Never inspect user-private files or use real personal data.
- Do not use `sudo`, `danger-full-access`, `--yolo`, sandbox bypasses, `eval`, or `exec`.
- Runtime behavior must be offline-first and require no credentials or external map/geocoding service.
- Install Python dependencies only in `.venv` and JavaScript dependencies only in `frontend/node_modules`.
- Preserve original uploads and never log full records. Sanitize filenames and spreadsheet exports.

## Architecture invariants

- `backend/geoforge/processing` contains pure, typed transformation primitives.
- `backend/geoforge/services` coordinates persistence, files, profiling, pipelines, and runs.
- API routes validate input and return the shared error envelope; they do not embed data logic.
- Pipeline YAML is parsed with `yaml.safe_load` and dispatched through a fixed step registry.
- The frontend consumes `/api` via typed adapters and remains usable at desktop and tablet widths.
- Store generated run artifacts beneath `artifacts/runs/<run-id>` and uploads beneath `data/uploads/<dataset-id>`.

## Quality workflow

1. Read `LOOP_GOAL.md`, `LOOP_STATE.json`, and `TASKS.md`.
2. Select exactly one bounded open task.
3. Add or update tests with implementation.
4. Run focused checks, then `scripts/run_quality_gate.sh`.
5. Update docs, `TASKS.md`, `LOOP_LOG.md`, and atomically update `LOOP_STATE.json`.
6. Never weaken or delete tests to force a pass.

Use Ruff formatting, strict MyPy, TypeScript strict mode, accessible semantic HTML, and deterministic synthetic fixtures.
