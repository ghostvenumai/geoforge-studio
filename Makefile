.PHONY: bootstrap dev backend frontend quality full release build demo benchmark verify loop loop-dry-run video video-preview video-dry-run clean

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

loop:
	./run_loop.sh --resume

loop-dry-run:
	./run_loop.sh --dry-run

video:
	./video/build_demo.sh all --resume

video-preview:
	./video/build_demo.sh all --skip-tts --resume || test $$? -eq 42

video-dry-run:
	./video/build_demo.sh --dry-run

clean:
	.venv/bin/python scripts/clean_build_artifacts.py
