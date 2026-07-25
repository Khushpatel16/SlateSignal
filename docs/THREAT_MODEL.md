# Threat Model

## Assets

- account credentials and session tokens
- private film concepts and saved package assumptions
- administrative metrics
- TMDB and infrastructure credentials
- integrity of source observations, forecasts, and model-version metadata
- unpublished film concepts and package assumptions
- model artifacts and immutable ledger entries

## Trust Boundaries

1. browser to Next.js
2. Next.js to FastAPI
3. FastAPI to PostgreSQL
4. scheduled jobs to third-party data providers
5. API and jobs to the versioned GCS model bucket
6. CI and deployment systems to runtime environments

## Primary Threats and Controls

| Threat | Current control | Production follow-up |
| --- | --- | --- |
| Credential theft | Argon2, HTTP-only same-site cookies | secure cookies, MFA/SSO |
| Session database leak | token digests only | key rotation and session revocation |
| Brute-force auth | in-process rate limiting | shared Redis/WAF limiter |
| Cross-user project access | repository queries scoped by user ID | authorization regression tests |
| Admin privilege escalation | configured email plus bootstrap secret | verified-email invite and audit log |
| Secret exposure | server-only environment variables | managed secret store |
| Malicious payload size | Pydantic lengths and ranges | proxy body limits |
| Connector compromise or SSRF | fixed provider base URLs, read-only calls, timeouts | egress allow-list and circuit breaker |
| Source poisoning | provenance, checksums, confidence, conflict retention | anomaly alerts and source quarantine |
| Historical leakage | cutoff checks on every observation and backtest feature | immutable warehouse snapshots |
| Forecast tampering | append-only ledger payloads and SHA-256 verification | signed hashes in an external transparency log |
| Model manipulation | bounded factors, artifact hashes, promotion gates | signed artifacts and two-person promotion |
| Scheduled-job replay | idempotent upserts and job-run records | unique scheduler invocation IDs |
| Sensitive log leakage | no request-body or synopsis logging | structured redaction policy |

## Privacy

Film concepts may be commercially sensitive. Production telemetry should use
request IDs and canonical hashes rather than synopsis text. Saved payload
retention and account deletion need explicit product controls before accepting
real confidential material.

## Residual Risk

The local rate limiter is process-scoped and is not sufficient across multiple
replicas. Third-party source data can still be wrong even when provenance is
complete. Account recovery, email verification, MFA, CSRF tokens for
cross-site deployment variants, a shared rate limiter, and a full audit event
stream are required before accepting confidential commercial concepts.
