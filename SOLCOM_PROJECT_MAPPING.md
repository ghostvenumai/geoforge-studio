# SOLCOM Project Mapping

| SOLCOM requirement | Implemented function | Relevant file | Test | Visible demo value |
|---|---|---|---|---|
| Python data processing | Typed Polars pipeline engine | backend/geoforge/processing/engine.py | test_engine_matrix.py | 19 visual operators execute |
| Large tabular formats | CSV/JSONL/Parquet/XLSX ingestion | processing/ingestion.py | test_ingestion_formats.py | Upload, preview, schema |
| Data quality | Sampling profiler and score | processing/profile.py | test_profile.py | Column warnings and before/after |
| Address data | German/European normalization | processing/address.py | test_address.py | Original vs normalized fields |
| Geodata | Validation, swap, CRS, Haversine | processing/geo.py | test_geo.py, test_geo_extended.py | Local map and ETRS89 output |
| Deduplication | Blocking plus weighted RapidFuzz | processing/dedup.py | test_dedup.py | Side-by-side review |
| Robust pipelines | Typed safe YAML DAG, quarantine/cancel | models/pipeline.py, processing/engine.py | test_pipeline_models.py | React Flow plus YAML |
| APIs/integration | FastAPI contract and background runs | api/routes, services/runs.py | test_api_workflow.py | Persistent asynchronous workflow |
| Audit/export | Manifest, checksums, reports, 3 formats | services/runs.py | test_api_workflow.py | Downloadable evidence |
| Performance | Real metrics and fixed-seed benchmark | benchmarks/run_benchmarks.py | release gate | CSV/Parquet charts |
| Quality engineering | Coverage, lint, typing, security, E2E | scripts/run_full_test_suite.sh | 82 Python, 9 Vitest, 3 E2E | Reproducible gates |
| Operations | Non-root multi-stage containers and loop | Dockerfiles, run_codex_loop.sh | preflight/release gate | One-command local start |
