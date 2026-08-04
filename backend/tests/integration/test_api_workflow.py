from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, cast

RUNTIME_ROOT = Path("artifacts/test-results/api-runtime").resolve()
RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["GEOFORGE_DATABASE_URL"] = f"sqlite:///{RUNTIME_ROOT / 'integration.db'}"
os.environ["GEOFORGE_DATA_DIR"] = str(RUNTIME_ROOT / "data")
os.environ["GEOFORGE_ARTIFACT_DIR"] = str(RUNTIME_ROOT / "runs")

from fastapi.testclient import TestClient  # noqa: E402

from geoforge.main import app  # noqa: E402

CSV_DATA = b"""record_id,street,city,postal_code,country,latitude,longitude,note
one, Teststr. 1 , berlin ,10115,DE,52.52,13.405,=1+1
two,Teststrasse 1,Berlin,10115,DE,52.5201,13.4051,normal
three,Other Str. 2,Hamburg,bad,DE,53.55,9.99,normal
"""


def _wait_for_run(client: TestClient, run_id: str) -> dict[str, object]:
    for _ in range(200):
        payload = client.get(f"/api/runs/{run_id}").json()
        if payload["status"] in {"completed", "failed", "cancelled", "timed_out"}:
            return cast(dict[str, Any], payload)
        time.sleep(0.05)
    raise AssertionError("Run did not reach a terminal state")


def test_full_upload_profile_run_and_artifact_workflow() -> None:
    with TestClient(app) as client:
        upload = client.post(
            "/api/datasets/upload",
            files={"file": ("../../demo.csv", CSV_DATA, "text/csv")},
            headers={"X-Request-ID": "integration-123"},
        )
        assert upload.status_code == 201, upload.text
        assert upload.headers["X-Request-ID"] == "integration-123"
        dataset = upload.json()
        assert dataset["original_filename"] == "demo.csv"
        assert dataset["row_count"] == 3
        assert dataset["encoding"]

        profile_response = client.post(f"/api/datasets/{dataset['id']}/profile")
        assert profile_response.status_code == 200
        profile = profile_response.json()["profile"]
        assert profile["quality_score"] < 100
        assert profile["total_invalid_count"] >= 1

        pipelines = client.get("/api/pipelines").json()["items"]
        address_pipeline = next(
            item for item in pipelines if item["name"] == "German Address Cleanup"
        )
        started = client.post(
            f"/api/pipelines/{address_pipeline['id']}/run", json={"dataset_id": dataset["id"]}
        )
        assert started.status_code == 202
        run = _wait_for_run(client, started.json()["id"])
        assert run["status"] == "completed", run
        assert run["input_rows"] == 3
        assert run["output_rows"] == 2
        assert run["quarantine_rows"] == 1

        metrics = client.get(f"/api/runs/{run['id']}/metrics").json()["metrics"]
        assert metrics["total_runtime_seconds"] > 0
        assert metrics["rows_per_second"] > 0
        assert metrics["peak_memory_bytes"] > 0
        assert len(metrics["steps"]) == 4

        artifacts = client.get(f"/api/runs/{run['id']}/artifacts").json()["items"]
        assert {item["kind"] for item in artifacts} >= {
            "result_parquet",
            "result_csv",
            "result_jsonl",
            "quarantine",
            "quality_report",
            "performance_report",
            "audit_log",
            "run_manifest",
            "pipeline_yaml",
            "checksums",
        }
        csv_artifact = next(item for item in artifacts if item["kind"] == "result_csv")
        csv_download = client.get(f"/api/artifacts/{csv_artifact['id']}/download")
        assert csv_download.status_code == 200
        assert b"'=1+1" in csv_download.content


def test_error_envelope_and_parallel_health_requests() -> None:
    with TestClient(app) as client:
        missing = client.get("/api/datasets/does-not-exist")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "http_404"
        assert missing.json()["error"]["request_id"]

        with ThreadPoolExecutor(max_workers=4) as executor:
            statuses = list(executor.map(lambda _: client.get("/api/health").status_code, range(8)))
        assert statuses == [200] * 8
