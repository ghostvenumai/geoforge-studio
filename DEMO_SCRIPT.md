# Demo Script

Start with ./scripts/start_demo.sh and open http://127.0.0.1:5173.

1. Upload data/samples/geoforge-demo.csv under Datasets.
2. Profile it and point out invalid postal codes, coordinates, duplicates, and recommendations.
3. Open Full Data Quality and Deduplication in Pipeline Builder; show nodes, config, YAML, validation, and version save.
4. Run it and follow Runs and Audit.
5. Compare before/after quality and quarantine-aware row-loss controls.
6. Review a duplicate group side by side and accept a canonical record.
7. Show measured run metrics plus 10k/100k CSV-versus-Parquet charts.
8. Download Parquet and inspect the run manifest/checksum artifacts.
9. Reload the browser and reopen the persisted run.
