# GeoForge Studio Benchmark Report

Measured at `2026-08-04T16:11:23.832726+00:00` on `Linux-6.8.0-134-generic-x86_64-with-glibc2.39`.
Times are wall-clock measurements from a single local run; RSS is process memory sampled at operation boundaries.

| Rows | Pipeline s | Pipeline rows/s | CSV read s | Parquet read s | CSV size | Parquet size |
|---:|---:|---:|---:|---:|---:|---:|
| 10,000 | 1.009 | 9,915 | 0.026 | 0.005 | 1,190,169 | 249,905 |
| 100,000 | 43.470 | 2,300 | 0.056 | 0.032 | 12,010,757 | 2,003,163 |

## Method

Synthetic rows are generated with a fixed seed, written to CSV and Zstandard Parquet, read with Polars, then processed through address normalization, coordinate validation, and blocked weighted deduplication. The one-million-row case is opt-in via `--include-million`.
