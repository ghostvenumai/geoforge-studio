# Testing

Fast gate: make quality. Full gate: make full. Release gate: make release.

The final full run executed Ruff, Ruff formatting, MyPy, 82 Python unit/property/integration/generator tests, backend branch coverage, Bandit high-severity scan, pip-audit, ESLint, strict TypeScript, 9 Vitest tests with coverage, and 3 Playwright scenarios with axe.

Backend coverage was 92.54%, above the 90% gate. Frontend coverage was 62.03% statements, 66.66% branches, 27.96% functions; full behavior is additionally covered by the browser journey.

Playwright uses local Chrome and repository-local FFmpeg support. It retains screenshot, video, trace, and HTML report data on failure and writes approved screenshots to artifacts/ui-review. The scenarios cover upload, profiling, pipeline validation/run, status polling, quality, duplicate decision, performance, Parquet download, manifest parsing, reload persistence, all main pages, desktop/tablet/mobile, dark mode, keyboard focus, overflow, browser console, failed requests, and serious/critical axe findings.

Known non-failing warnings: React Router 6 future flags in Vitest and Starlette's TestClient httpx deprecation.
