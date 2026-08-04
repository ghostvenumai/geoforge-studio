# Architecture

## Decision summary

GeoForge Studio uses a modular monolith: one FastAPI service owns metadata and processing, while a separately built React single-page application consumes a versioned `/api` contract. This keeps the portfolio deployable on one workstation but preserves boundaries that could later become workers or services.

```text
Browser (React, Query, React Flow, Recharts)
                  |
            REST / OpenAPI
                  |
FastAPI routes -> services -> pipeline registry -> Polars/PyArrow/DuckDB
                  |                         |
          SQLAlchemy/SQLite          pyproj/RapidFuzz
                  |
 immutable uploads + versioned run artifacts
```

## Key decisions

1. **Polars-first columnar engine.** Lazy scans and streaming collection support large CSV/Parquet inputs; DuckDB is reserved for analytical aggregation and artifact inspection.
2. **SQLite as metadata, files as data plane.** Metadata remains relational and transactional; potentially large frames never become SQLite blobs.
3. **Synchronous API plus bounded background executor.** Runs execute in a small thread pool, expose cancellation state, and isolate step errors. This is simpler and more reproducible than introducing an external queue.
4. **Strict pipeline DSL.** Pydantic discriminated configuration, a fixed step registry, and `yaml.safe_load` provide expressive pipelines without arbitrary code execution.
5. **Blocked deduplication.** Configurable blocking keys create bounded candidates; RapidFuzz scores only within partitions and caps group size.
6. **Offline map.** A coordinate scatter projection supplies geographic context without sending data to third parties.
7. **Immutable evidence.** Each run writes a manifest, metrics, reports, pipeline YAML, quarantine file, and checksums beneath its own directory.

## Data lifecycle

Upload -> validate/sanitize -> immutable original -> schema preview/profile -> versioned pipeline -> bounded run -> quality comparison -> review/quarantine -> sanitized export and audit manifest.

## Security boundaries

Only generated identifiers participate in storage paths. Downloads resolve stored artifact records and verify containment. Upload limits are enforced during streaming. Logs contain identifiers and counts, never complete source records. CORS is allow-listed for configured local origins.

## Scaling posture

Polars lazy execution, sampling, thread limits, run timeouts, and candidate blocking are the primary controls. The API process is intentionally single-instance for local SQLite correctness; a production scale-out would replace SQLite and the local executor while retaining the pipeline contract.
