FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY backend ./backend
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir .

FROM python:3.12-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --system geoforge && useradd --system --gid geoforge --home-dir /app geoforge
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=geoforge:geoforge backend ./backend
RUN mkdir -p /app/data /app/artifacts/runs && chown -R geoforge:geoforge /app
USER geoforge
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"]
CMD ["uvicorn", "geoforge.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
