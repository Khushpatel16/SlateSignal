# Security policy

## Reporting

Please do not open a public issue for a suspected vulnerability. Report it
privately through GitHub Security Advisories with the affected route, impact,
and a minimal reproduction.

## Security posture

- Passwords are hashed with Argon2.
- Session credentials are opaque, hashed at rest, HTTP-only, same-site cookies.
- Authentication routes are rate limited.
- Admin provisioning requires both a configured email and a separate bootstrap
  token.
- Protected attributes are excluded from prediction inputs.
- Secrets are supplied through environment variables and never bundled into the
  browser.
- CI runs dependency audits, static analysis, strict type checks, and CodeQL.

Production operators must enable secure cookies, terminate TLS, rotate leaked
credentials, use a managed PostgreSQL service with encrypted backups, and
restrict administrative accounts through `ADMIN_EMAIL` and a rotated
`ADMIN_BOOTSTRAP_TOKEN`.

## Supported versions

Only the current `main` branch is supported while the product remains in active
development.
