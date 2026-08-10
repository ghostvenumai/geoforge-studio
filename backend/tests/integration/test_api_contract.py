from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any, cast

RUNTIME_ROOT = Path("artifacts/test-results/api-runtime").resolve()
RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["GEOFORGE_DATABASE_URL"] = f"sqlite:///{RUNTIME_ROOT / 'integration.db'}"
os.environ["GEOFORGE_DATA_DIR"] = str(RUNTIME_ROOT / "data")
os.environ["GEOFORGE_ARTIFACT_DIR"] = str(RUNTIME_ROOT / "runs")

from fastapi.testclient import TestClient  # noqa: E402

from geoforge.db.base import SessionLocal  # noqa: E402
from geoforge.db.models import Artifact, Run  # noqa: E402
from geoforge.main import app  # noqa: E402

CSV = b"""record_id,street,city,postal_code,country,latitude,longitude
a,Teststr. 1,Berlin,10115,DE,52.52,13.405
b,Teststrasse 1,BERLIN,10115,DE,52.5201,13.4051
c,Other Str. 2,Nordhafen,bad,DE,120,13.4
"""


def upload(
    client: TestClient, name: str = "contract.csv", content: bytes = CSV
) -> dict[str, object]:
    response = client.post("/api/datasets/upload", files={"file": (name, content, "text/csv")})
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def wait_for_run(client: TestClient, run_id: str) -> dict[str, object]:
    for _ in range(200):
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed", "cancelled", "timed_out"}:
            return cast(dict[str, Any], payload)
        time.sleep(0.05)
    raise AssertionError("Run timed out in API contract test")


def test_dataset_crud_profile_duplicate_and_errors() -> None:
    with TestClient(app) as client:
        invalid = client.post(
            "/api/datasets/upload", files={"file": ("payload.py", b"print(1)", "text/plain")}
        )
        assert invalid.status_code == 400
        dataset = upload(client, f"contract-{uuid.uuid4().hex}.csv")
        dataset_id = str(dataset["id"])
        assert client.get(f"/api/datasets/{dataset_id}").status_code == 200
        listing = client.get("/api/datasets").json()
        assert any(item["id"] == dataset_id for item in listing["items"])
        assert client.get(f"/api/datasets/{dataset_id}/profile").status_code == 404
        assert client.post(f"/api/datasets/{dataset_id}/profile").status_code == 200
        assert client.get(f"/api/datasets/{dataset_id}/profile").status_code == 200

        duplicate = upload(client, f"duplicate-{uuid.uuid4().hex}.csv")
        assert duplicate["status"] == "duplicate"
        assert duplicate["duplicate_of_dataset_id"]
        assert client.delete(f"/api/datasets/{duplicate['id']}").status_code == 200
        assert client.get(f"/api/datasets/{duplicate['id']}").status_code == 404
        assert client.delete("/api/datasets/not-found").status_code == 404


def test_registered_demo_dataset_library_is_fixed_and_importable() -> None:
    with TestClient(app) as client:
        library = client.get("/api/datasets/demo")
        assert library.status_code == 200
        assert {item["theme"] for item in library.json()["items"]} == {
            "marketing",
            "ecommerce",
            "logistics",
            "security",
        }
        imported = client.post("/api/datasets/demo/marketing")
        assert imported.status_code == 201, imported.text
        assert imported.json()["original_filename"] == "geoforge-demo-marketing.csv"
        assert imported.json()["row_count"] == 1_000
        assert client.post("/api/datasets/demo/not-registered").status_code == 422


def test_pipeline_validation_creation_and_missing_references() -> None:
    yaml_text = """name: Contract pipeline
description: Safe fixed operation pipeline
version: 1
steps:
  - id: load
    type: load_dataset
    name: Load
    config: {}
  - id: export
    type: export_dataset
    name: Export
    config: {format: parquet, filename: contract}
"""
    with TestClient(app) as client:
        pipelines = client.get("/api/pipelines")
        assert pipelines.status_code == 200 and pipelines.json()["total"] >= 3
        example_id = pipelines.json()["items"][0]["id"]
        assert client.get(f"/api/pipelines/{example_id}").status_code == 200
        validated = client.post("/api/pipelines/validate", json={"yaml_text": yaml_text})
        assert validated.status_code == 200
        assert validated.json()["warnings"]
        assert len(validated.json()["checksum"]) == 64
        assert (
            client.post(
                "/api/pipelines/validate", json={"yaml_text": "!!python/object:bad {}"}
            ).status_code
            == 422
        )
        created = client.post("/api/pipelines", json={"yaml_text": yaml_text})
        assert created.status_code == 201
        assert client.get(f"/api/pipelines/{created.json()['id']}").status_code == 200
        assert client.get("/api/pipelines/not-found").status_code == 404
        assert (
            client.post(
                f"/api/pipelines/{created.json()['id']}/run", json={"dataset_id": "not-found"}
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/pipelines/not-found/run", json={"dataset_id": "not-found"}
            ).status_code
            == 404
        )


def test_run_duplicate_review_cancel_overview_and_artifact_guards() -> None:
    with TestClient(app) as client:
        dataset = upload(client, f"run-{uuid.uuid4().hex}.csv")
        pipeline = next(
            item
            for item in client.get("/api/pipelines").json()["items"]
            if item["name"] == "Full Data Quality and Deduplication"
        )
        started = client.post(
            f"/api/pipelines/{pipeline['id']}/run", json={"dataset_id": dataset["id"]}
        )
        assert started.status_code == 202
        run = wait_for_run(client, started.json()["id"])
        assert run["status"] == "completed", run
        assert client.get("/api/runs").json()["total"] >= 1
        duplicates = client.get(f"/api/runs/{run['id']}/duplicates")
        assert duplicates.status_code == 200
        assert duplicates.json()["total"] >= 1
        group = duplicates.json()["items"][0]
        decision = client.post(
            f"/api/runs/{run['id']}/duplicates/decision",
            json={
                "duplicate_group_id": group["group_id"],
                "decision": "accepted",
                "canonical_record_id": group["records"][0]["record_id"],
            },
        )
        assert decision.status_code == 200

        with SessionLocal() as db:
            queued = Run(
                id=uuid.uuid4().hex,
                dataset_id=str(dataset["id"]),
                pipeline_id=str(pipeline["id"]),
            )
            db.add(queued)
            db.commit()
        cancelled = client.post(f"/api/runs/{queued.id}/cancel")
        assert cancelled.status_code == 200
        assert client.post(f"/api/runs/{queued.id}/cancel").status_code == 409
        assert client.get("/api/runs/not-found").status_code == 404

        outside_id = uuid.uuid4().hex
        missing_id = uuid.uuid4().hex
        with SessionLocal() as db:
            db.add_all(
                [
                    Artifact(
                        id=outside_id,
                        run_id=str(run["id"]),
                        kind="guard",
                        name="outside.txt",
                        stored_path=str(RUNTIME_ROOT / f"outside-{outside_id}.txt"),
                        checksum="0" * 64,
                        size_bytes=0,
                        media_type="text/plain",
                    ),
                    Artifact(
                        id=missing_id,
                        run_id=str(run["id"]),
                        kind="guard",
                        name="missing.txt",
                        stored_path=str(RUNTIME_ROOT / "runs" / f"missing-{missing_id}.txt"),
                        checksum="0" * 64,
                        size_bytes=0,
                        media_type="text/plain",
                    ),
                ]
            )
            db.commit()
        assert client.get(f"/api/artifacts/{outside_id}/download").status_code == 403
        assert client.get(f"/api/artifacts/{missing_id}/download").status_code == 404
        assert client.get("/api/artifacts/not-found/download").status_code == 404
        assert client.get("/api/overview").status_code == 200
        benchmark = client.get("/api/benchmarks")
        assert benchmark.status_code == 200
        assert any(item["rows"] == 100_000 for item in benchmark.json()["results"])
        assert client.get("/api/system/info").status_code == 200
        assert client.delete(f"/api/datasets/{dataset['id']}").status_code == 409
