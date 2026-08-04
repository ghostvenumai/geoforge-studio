# Security

GeoForge Studio is offline-first and operates without API keys. Pipeline YAML is loaded with the safe PyYAML loader and validated against a fixed Pydantic operator registry; rules cannot execute Python or shell code.

Controls include bounded chunked uploads, a 100 MiB default limit, extension checks, sanitized basenames, resolved-path containment, immutable originals, SHA-256 checksums, local CORS origins, request IDs, defensive headers, CSV formula-injection escaping, non-PII audit logs, guarded artifact downloads, worker/time limits, and bounded deduplication blocks.

Containers run as non-root, read-only, with all capabilities dropped and no-new-privileges. Standard operation uses no external geocoder, map, telemetry, or analytics service.

Verified on 2026-08-04: Bandit found zero high-severity issues; pip-audit found no known vulnerabilities after upgrading PyArrow and pytest; npm audit found zero high/critical and two moderate React Router 6 advisories. Dynamic redirects and SSR hydration, the affected paths, are not used. React Router 7 remains a deliberate future major migration.

Never place real personal/customer data, credentials, SSH material, browser data, or secrets in the repository. Demo data is synthetic.
