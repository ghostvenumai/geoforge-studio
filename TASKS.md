# GeoForge Studio Delivery Backlog

Status: `[x]` complete, `[~]` active, `[ ]` open, `[!]` blocked.

## Foundation

- [x] Create isolated repository and inspect local toolchain.
- [x] Verify installed Codex CLI arguments from `codex --help`.
- [x] Define architecture, safety invariants, dependencies, loop state, and model router.
- [x] Bootstrap `.venv` and `frontend/node_modules`; create reproducible lockfiles.
- [x] Add bounded loop, repair, quality, demo, and release scripts.

## Backend and processing

- [x] Build configuration, request IDs, security headers, JSON logging, database, and health API.
- [x] Implement safe CSV, JSON, JSONL, Parquet, and XLSX ingestion with immutable originals.
- [x] Implement sampled/lazy profiling and quality scoring.
- [x] Implement address normalization with original/normalized value preservation.
- [x] Implement coordinate validation, CRS transforms, distance, bbox, grouping, and geohash.
- [x] Implement blocked exact/normalized/fuzzy weighted deduplication and review decisions.
- [x] Implement validated pipeline models, YAML, registry, engine, quarantine, cancellation, and audit.
- [x] Implement exports, checksums, manifests, metrics, and artifact download.
- [x] Add all required REST resources and consistent errors.
- [x] Add three executable example pipelines.
- [x] Add deterministic synthetic demo-data generator.

## Frontend

- [x] Build responsive shell, 13-page navigation, theme, loading/error/empty states, and toasts.
- [x] Build overview with real backend metrics and charts.
- [x] Build dataset upload, preview, profiling, and column analysis.
- [x] Build address and geo before/after tools and local point map.
- [x] Build React Flow pipeline editor, config panel, YAML editor, validation, persistence, undo/redo.
- [x] Build duplicate side-by-side review and canonical selection.
- [x] Build quality, performance, audit, export, health, and architecture pages.

## Verification and release

- [x] Backend unit/property/integration tests and >=90% owned-code coverage.
- [x] Frontend unit tests, strict typecheck, lint, and coverage.
- [x] Playwright E2E, axe accessibility, screenshots, console/network checks, and responsive review.
- [x] Ruff, MyPy, Bandit, dependency audit, secret scan, and artifact validation.
- [x] Execute demo pipeline and real 10k/100k benchmarks; keep 1m benchmark opt-in.
- [!] Verify production builds, Docker Compose if available, and health checks. Native builds and health checks passed; Compose configuration is valid, while image construction is blocked by DNS in the Docker builder.
- [x] Complete portfolio, SOLCOM mapping, UI review, benchmark, and final release reports.
- [x] Localize the complete visible web interface to German and add a detailed German operating guide.
- [x] Add deterministic Marketing, E-Commerce, Logistics, and Security demo datasets.
- [x] Expose the four themed datasets as a directly loadable in-product demo library.
- [x] Add bounded persistent master-loop, failure classification, retries, resume, and reports.
- [x] Add validated German timeline, deterministic Playwright recording, subtitles, OpenAI TTS adapter, FFmpeg render, and video QA.
- [x] Execute the real 147-second recording, subtitle render, video QA, and final reachable quality gates.
- [!] Generate the final narrated MP4 after an external `OPENAI_API_KEY` is safely supplied; no request was sent without it.
