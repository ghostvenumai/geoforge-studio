.PHONY: bootstrap dev backend frontend quality full release build demo benchmark verify clean

bootstrap:
	python3 main.py bootstrap
	cd frontend && npm install

dev:
	./scripts/start_demo.sh

backend:
	.venv/bin/uvicorn geoforge.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev -- --host 127.0.0.1

quality:
	./scripts/run_quality_gate.sh

full:
	./scripts/run_full_test_suite.sh

release:
	./scripts/run_release_gate.sh

build:
	./scripts/run_release_gate.sh

demo:
	./scripts/run_demo_smoke_test.sh

benchmark:
	.venv/bin/python -m benchmarks.run_benchmarks --rows 10000 100000

verify:
	.venv/bin/bandit -r backend/geoforge scripts -lll -q -f json -o artifacts/test-results/bandit.json
	cd frontend && npm run test:e2e

clean:
	.venv/bin/python scripts/clean_build_artifacts.py
