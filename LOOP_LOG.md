# Loop Log

## 2026-08-04 — Iteration 1

- Created a new isolated Git repository because the initial working directory was a home directory, not a repository.
- Confirmed Python 3.12.3, Node 18.19.1, npm 9.2.0, and Codex CLI 0.146.0.
- Confirmed safe Codex arguments from installed CLI help; host sandbox prevented direct Docker probing.
- Established architecture, safety rules, bounded backlog, state schema, and deterministic model routing.

## 2026-08-04 — Release validation

- Completed backend, processing engine, API, React UI, visual pipeline builder, demo data, audit/export, and portfolio documentation.
- Verified 82 Python tests, 92.54% backend branch coverage, Ruff, MyPy, Bandit high-severity gate, pip-audit, ESLint, strict TypeScript, 9 Vitest tests, frontend coverage, and production build.
- Verified three Playwright scenarios with axe, responsive layouts, console/network inspection, dark mode, keyboard flow, screenshots, demo pipeline, and artifact downloads.
- Measured real 10,000- and 100,000-row CSV/Parquet benchmarks. The 100,000-row pipeline processed 2,300.42 rows/s.
- Docker Compose configuration passed. Image construction was attempted and stopped at the documented external DNS failure in the Docker builder; no sandbox bypass was attempted.

## 2026-08-04 — German interface and operating guide

- Localized all 13 navigation pages, shared states, accessibility labels, dynamic statuses, example pipeline names, step names, profiling recommendations, chart series, and artifact kinds to German.
- Kept API fields and YAML step identifiers stable for compatibility and documented that boundary.
- Added BEDIENUNGSANLEITUNG.md with startup, complete workflow, every page, visual/YAML editing, deduplication decisions, exports, privacy, troubleshooting, and a five-minute demo.
- Verified ESLint, strict TypeScript/production build, 9 Vitest tests, Bandit high-severity gate, and Playwright/axe: desktop, tablet, and mobile all passed.
