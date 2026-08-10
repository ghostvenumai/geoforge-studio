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

## 2026-08-10 — Themed demo library, master-loop, and product video

- Added deterministic Marketing/CRM, E-Commerce, Logistics/Geo and Security/Robustness datasets with 1,000 synthetic rows each and a fixed one-click UI/API library.
- Repaired mixed-format CSV date ingestion by preserving ambiguous raw values as text for explicit pipeline parsing.
- Added a bounded persistent master-loop with fixed commands, atomic state, lock cleanup, retries, timeouts, structured redacted logs, external-blocker continuation and resume.
- Added an 11-scene, 147-second German timeline, real Playwright UI recording, narration/SRT generation, cacheable OpenAI TTS boundary, FFmpeg render and FFprobe/audio QA.
- Recorded and validated `dist/solcom_demo_preview.mp4`: H.264/AAC, 1920×1080, 30 fps, 147.000 seconds, 7,849,089 bytes. The AAC stream is intentionally silent because no TTS credential was available.
- Master-loop completed all reachable phases. Voiceover alone is `BLOCKED_EXTERNAL_CREDENTIAL`; no external request was sent and no narrated final MP4 was claimed.
- Repaired project-local Node/Playwright-FFmpeg selection, video CORS, stale standard E2E server reuse, and Recharts SVG ARIA semantics.
- Final `make full` passed: 109 Python tests, 92.69% backend branch coverage, 9 Vitest tests, Bandit high gate, pip-audit with no known vulnerabilities, and 3/3 Playwright/axe scenarios.
