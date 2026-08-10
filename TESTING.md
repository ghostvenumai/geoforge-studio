# Testing

Fast gate: make quality. Full gate: make full. Release gate: make release.

The final full run on 2026-08-10 executed Ruff, Ruff formatting, MyPy, 109 Python unit/property/integration/generator/automation/video tests, backend branch coverage, Bandit high-severity scan, pip-audit, ESLint, strict TypeScript, 9 Vitest tests with coverage, and 3 Playwright scenarios with axe.

Backend branch coverage was 92.69%, above the 90% gate. Frontend coverage was 40.54% statements, 64.12% branches, and 29.13% functions; full behavior is additionally covered by the browser journey.

Playwright uses local Chrome and repository-local FFmpeg support. It retains screenshot, video, trace, and HTML report data on failure and writes approved screenshots to artifacts/ui-review. The scenarios cover upload, profiling, pipeline validation/run, status polling, quality, duplicate decision, performance, Parquet download, manifest parsing, reload persistence, all main pages, desktop/tablet/mobile, dark mode, keyboard focus, overflow, browser console, failed requests, and serious/critical axe findings.

Known non-failing warnings: React Router 6 future flags in Vitest and Starlette's TestClient httpx deprecation.

The standard Playwright configuration uses fresh isolated localhost services on
ports 18083/15176, a dedicated SQLite database, dedicated artifacts, a scoped
CORS origin, and `reuseExistingServer: false`. This prevents an unrelated or stale
developer server from influencing release evidence.

## Master-loop and video tests

The fast and full gates also cover the persistent automation state machine,
bounded retries, atomic resume state, failure classification, secret redaction,
timeline validation, subtitle timing, credential-safe TTS behavior, scene cache,
FFmpeg command construction, themed-data determinism, and video probe analysis.

Useful focused commands:

```bash
.venv/bin/pytest automation/tests video/tests scripts/test_generate_themed_demo_data.py -q
make loop-dry-run
make video-dry-run
```

The recording test has a separate Playwright configuration and is excluded from
the normal fast E2E set because its duration is intentionally 147 seconds. It
starts isolated localhost services on ports 18082 and 15175, uses isolated SQLite
and artifact directories under `video/tmp`, loads the Marketing demo through the
visible UI, profiles it, executes the full quality pipeline, and records the real
quality, duplicate, performance, export, and architecture pages.
