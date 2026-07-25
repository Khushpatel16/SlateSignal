# Deployment

## Recommended Resume Topology

- Web: Vercel
- API: GCP Cloud Run
- Scheduled ingestion and forecasts: Cloud Run Jobs + Cloud Scheduler
- Database: Neon PostgreSQL
- Model bundle: private versioned GCS bucket
- Secrets: Google Secret Manager

This keeps public reads fast and inexpensive. BERT runs in scheduled jobs or the
separate scenario path, not on ordinary movie-report requests.

## 1. Revoke and Recreate Credentials

The legacy notebooks contained provider credentials. Treat every credential
that ever appeared there as compromised and revoke it before deployment.
Create fresh TMDB, YouTube, and approved Reddit credentials. Never place secret
values in `NEXT_PUBLIC_*`, Git, Terraform variables, or container layers.

## 2. Provision Neon

1. Create a PostgreSQL project in a region near the Cloud Run region.
2. Enable automated backups and point-in-time recovery if the plan supports it.
3. Use the pooled connection endpoint.
4. Convert the URL prefix to `postgresql+psycopg://`.
5. Retain `sslmode=require`.

Example shape:

```text
postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
```

## 3. Build and Publish the API Image

Create an Artifact Registry Docker repository, authenticate Docker, then build
from the inference-service directory:

```bash
gcloud auth configure-docker us-west1-docker.pkg.dev
docker build -t \
  us-west1-docker.pkg.dev/PROJECT/slatesignal/api:GIT_SHA \
  services/inference
docker push us-west1-docker.pkg.dev/PROJECT/slatesignal/api:GIT_SHA
```

Pin `api_image` by immutable digest for production rather than a mutable tag.

The image is non-root and includes the API, migrations, small XGBoost
artifacts, tokenizer, portable catalog, and precomputed launch ledger. The
208 MB ONNX encoder is deliberately excluded.

## 4. Upload the Model Bundle

The GCP Terraform creates a versioned bucket. Upload the local encoder and
verify the versioned checksum:

```bash
gsutil cp \
  services/inference/artifacts/bert-base-uncased-fp16.onnx \
  gs://PROJECT-slatesignal-models/
shasum -a 256 \
  services/inference/artifacts/bert-base-uncased-fp16.onnx
```

The expected digest is in
`services/inference/artifacts/bert-base-uncased-fp16.parity.json`. Cloud Run
mounts the bucket read-only at `/models`.

## 5. Create Secrets

Terraform references existing secrets and never stores secret values in state.
Create the secret containers and versions first:

```bash
gcloud secrets create slatesignal-database-url --replication-policy=automatic
printf '%s' "$DATABASE_URL" | \
  gcloud secrets versions add slatesignal-database-url --data-file=-

gcloud secrets create slatesignal-tmdb-token --replication-policy=automatic
printf '%s' "$TMDB_API_TOKEN" | \
  gcloud secrets versions add slatesignal-tmdb-token --data-file=-

gcloud secrets create slatesignal-admin-bootstrap-token \
  --replication-policy=automatic
openssl rand -base64 32 | \
  gcloud secrets versions add slatesignal-admin-bootstrap-token --data-file=-
```

Add optional YouTube and Reddit secrets to the buzz job after base deployment.
Without them, Wikimedia and GDELT still run; no source is fabricated.

## 6. Apply GCP Infrastructure

```bash
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

The module creates:

- required Google APIs
- private versioned GCS model bucket
- least-privilege runtime and scheduler service accounts
- Cloud Run API service
- catalog, actuals, buzz, forecast, and IMDb jobs
- UTC Cloud Scheduler triggers

The API runs `alembic upgrade head` before Uvicorn starts. For a high-scale
rollout, move migration execution into a one-off release job to avoid startup
races across multiple new instances.

Verify:

```bash
curl https://CLOUD_RUN_URL/v1/health
gcloud run jobs execute slatesignal-catalog --region us-west1 --wait
gcloud run jobs execute slatesignal-forecasts --region us-west1 --wait
```

## 7. Deploy Vercel

Import the repository and set the Vercel root directory to `apps/web`.

Set:

```text
INFERENCE_API_URL=https://CLOUD_RUN_URL
NEXT_PUBLIC_SITE_URL=https://YOUR_VERCEL_OR_CUSTOM_DOMAIN
```

Set the API's `WEB_ORIGIN` to that exact HTTPS origin. Vercel proxies
`/api/v1/*` to Cloud Run, so HTTP-only session cookies remain first-party.

Run these checks against the production URL:

```bash
curl -I https://YOUR_DOMAIN
curl https://YOUR_DOMAIN/api/v1/health
```

Then complete the browser journeys for search, movie report, compare,
backtests, account registration, saved scenario, and mobile navigation.

## 8. Provision the Administrator

Register once over HTTPS with the configured email and the bootstrap token:

```bash
curl -X POST https://YOUR_DOMAIN/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -H "X-Admin-Bootstrap-Token: $ADMIN_BOOTSTRAP_TOKEN" \
  -d '{"email":"you@example.com","display_name":"Owner","password":"use-a-password-manager"}'
```

After the admin exists, rotate or destroy the bootstrap secret version.

## Portable Alternatives

### Railway

Deploy `services/inference` as a Docker service. `railway.json` configures the
health check. Attach Neon or Railway PostgreSQL, set the API environment, and
deploy `apps/web` separately to Vercel.

### DigitalOcean

`infra/digitalocean/app.yaml` is an App Platform starting point. Replace the
repository and web origin, then add secrets in the control plane. Use a worker
or Functions schedule for CLI jobs.

### Heroku

Deploy `services/inference` as the application root with the included
`heroku.yml`, attach Heroku Postgres or Neon, and use Heroku Scheduler for CLI
jobs. The release command is folded into web startup for portability.

### AWS

`infra/aws/apprunner.yaml` documents an App Runner source deployment. A more
complete AWS topology is App Runner or ECS Fargate, EventBridge Scheduler,
RDS/Aurora PostgreSQL, S3 for the model, and Secrets Manager.

The same API container works on all platforms. The web container can run on
Railway, DigitalOcean, Heroku, ECS, or GCP if Vercel is not desired.

## Local Production-Like Stack

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8000/v1/health
```

Open `http://localhost:3000`.

## Launch Checklist

- no notebook or pickle artifacts in the production tree
- fresh provider credentials in managed secrets
- `COOKIE_SECURE=true`
- `AUTO_CREATE_SCHEMA=false`
- final `WEB_ORIGIN` and `NEXT_PUBLIC_SITE_URL`
- Neon backups and restore procedure tested
- ONNX GCS object checksum verified
- ledger verification job returns valid
- all scheduled jobs show successful `job_runs`
- TMDB attribution visible
- source conflicts and stale data visible
- CodeQL, secret scan, dependency audits, unit tests, and Playwright green
- custom domain, HTTPS, privacy notice, and terms configured
- synopsis text and session tokens excluded from logs
