# Performance

Processing is columnar with Polars/PyArrow, sampled profiling, lazy-compatible plans, bounded workers, per-step timers, candidate blocking, and capped duplicate blocks. Every run records runtime, rows/s, observed RSS, CPU, I/O sizes, warnings, errors, and row counts.

The final fixed-seed run on 2026-08-04 measured:

| Rows | Pipeline seconds | Rows/s | Peak observed RSS | CSV read rows/s | Parquet read rows/s |
|---:|---:|---:|---:|---:|---:|
| 10,000 | 1.009 | 9,915 | 160,251,904 B | 383,956 | 1,946,264 |
| 100,000 | 43.470 | 2,300 | 642,822,144 B | 1,800,005 | 3,101,916 |

At 100k, CSV occupied 12,010,757 bytes and Parquet 2,003,163 bytes. Results live in benchmarks/benchmark-results.json and are served to the Performance page. The one-million-row run is opt-in and was not executed.
