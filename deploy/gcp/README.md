# Deploying GrowthReel to Google Cloud Run

Three Cloud Run services (`backend` Django, `api` FastAPI, `frontend` React
SPA) plus a new Cloud SQL Postgres instance and a new Memorystore Redis
instance. Run everything below from the **repo root**, in order. Each `gcloud`
command is safe to re-run (idempotent) unless noted otherwise.

Not covered here: the `celery_worker` service from `docker-compose.yml`.
Cloud Run's request-driven model doesn't fit a long-running queue consumer
as well as Cloud Run Jobs / a `min-instances=1` background service would —
worth its own pass once the three HTTP services are live.

## 0. One-time setup

```bash
# Edit these three, then everything below copy-pastes unchanged.
export PROJECT_ID=your-gcp-project-id
export REGION=asia-south1
export REPO=growthreel-repo        # already created, per your `gcloud artifacts repositories create` command

gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  vpcaccess.googleapis.com \
  compute.googleapis.com \
  secretmanager.googleapis.com

gcloud auth configure-docker "${REGION}-docker.pkg.dev"
```

### Why `.gcloudignore` files exist in this repo now

`backend/.gitignore` ignores `apps/*/migrations/` (and `static/css/tailwind.css`)
because they're machine-generated / locally-edited, not because they're
unneeded at build time — Django migrations and the compiled Tailwind CSS both
have to be **inside the image**. `gcloud builds submit` silently mirrors
`.gitignore` into an implicit `.gcloudignore` when none exists, which would
upload a tree missing both, and `manage.py migrate` would then have nothing to
apply (empty schema, every page 500s). `backend/.gcloudignore` and the root
`.gcloudignore` (for the `api` image, built from the repo root — see below)
exist specifically to not repeat that exclusion. Nothing to do here, just
don't delete them.

## 1. Cloud SQL (Postgres)

```bash
gcloud sql instances create growthreel-db \
  --database-version=POSTGRES_16 \
  --tier=db-g1-small \
  --region="$REGION" \
  --storage-size=10 \
  --storage-auto-increase

gcloud sql databases create growthreel --instance=growthreel-db

# Pick a real password; this is NOT the local-dev "growthreel/growthreel" one.
export DB_PASSWORD='generate-a-strong-password-here'
gcloud sql users create growthreel \
  --instance=growthreel-db \
  --password="$DB_PASSWORD"

export CONNECTION_NAME=$(gcloud sql instances describe growthreel-db --format='value(connectionName)')
echo "$CONNECTION_NAME"   # PROJECT_ID:REGION:growthreel-db — you'll reuse this below
```

## 2. Memorystore (Redis) + Serverless VPC Access connector

Cloud Run reaches Cloud SQL through a built-in sidecar (no VPC needed, step 1
above is already enough for that), but Memorystore is a private-IP-only
service, so Cloud Run needs a VPC connector to reach it at all.

```bash
gcloud compute networks vpc-access connectors create growthreel-connector \
  --region="$REGION" \
  --network=default \
  --range=10.8.0.0/28

gcloud redis instances create growthreel-redis \
  --size=1 \
  --region="$REGION" \
  --redis-version=redis_7_2 \
  --network=default \
  --connect-mode=DIRECT_PEERING

export REDIS_HOST=$(gcloud redis instances describe growthreel-redis --region="$REGION" --format='value(host)')
echo "$REDIS_HOST"
```

## 3. Secret Manager

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))" | tr -d '\n' | \
  gcloud secrets create django-secret-key --data-file=-

python -c "import secrets; print(secrets.token_urlsafe(64))" | tr -d '\n' | \
  gcloud secrets create shared-jwt-secret --data-file=-

printf '%s' "$DB_PASSWORD" | gcloud secrets create db-password --data-file=-

# Cloud Run's default runtime service account needs read access to all three.
export PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
export RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for secret in django-secret-key shared-jwt-secret db-password; do
  gcloud secrets add-iam-policy-binding "$secret" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role=roles/secretmanager.secretAccessor
done
```

## 4. Build the three images

```bash
gcloud builds submit ./backend \
  --tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest"

# api's image bakes in backend/'s source (see api/Dockerfile.cloudrun's
# header comment) — built from the repo root with a one-step Cloud Build
# config, not api/'s own Dockerfile.
gcloud builds submit . \
  --config=api/cloudbuild.api.yaml \
  --substitutions="_IMAGE=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/api:latest"

gcloud builds submit ./frontend-app \
  --tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend:latest"
```

## 5. Deploy `backend`

```bash
export BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest"

# Shared by both the migrate job (step 6) and the service deploy below.
export DB_ENV_VARS="DJANGO_SETTINGS_MODULE=config.settings.production,DB_ENGINE=django.db.backends.postgresql,DB_NAME=growthreel,DB_USER=growthreel,DB_HOST=/cloudsql/${CONNECTION_NAME},DB_PORT=5432,DB_SSLMODE=disable,REDIS_URL=redis://${REDIS_HOST}:6379/0,DJANGO_FORCE_HTTPS=true"
export SECRET_VARS="DJANGO_SECRET_KEY=django-secret-key:latest,SHARED_JWT_SECRET=shared-jwt-secret:latest,DB_PASSWORD=db-password:latest"

gcloud run deploy backend \
  --image="$BACKEND_IMAGE" \
  --region="$REGION" \
  --allow-unauthenticated \
  --port=8000 \
  --add-cloudsql-instances="$CONNECTION_NAME" \
  --vpc-connector=growthreel-connector \
  --vpc-egress=private-ranges-only \
  --set-env-vars="$DB_ENV_VARS,DJANGO_ALLOWED_HOSTS=placeholder.invalid,APP_FRONTEND_URL=https://placeholder.invalid,CORS_ALLOWED_ORIGINS=https://placeholder.invalid" \
  --set-secrets="$SECRET_VARS"

export BACKEND_URL=$(gcloud run services describe backend --region="$REGION" --format='value(status.url)')
echo "$BACKEND_URL"
```

`DJANGO_ALLOWED_HOSTS`/`APP_FRONTEND_URL`/`CORS_ALLOWED_ORIGINS` are
placeholders here on purpose — you don't know `backend`'s or `frontend`'s real
`*.run.app` URL before the first deploy. Step 8 below fixes all of them in
one pass once every URL is known.

## 6. Run migrations (Cloud Run Job, not SSH)

```bash
gcloud run jobs create backend-migrate \
  --image="$BACKEND_IMAGE" \
  --region="$REGION" \
  --add-cloudsql-instances="$CONNECTION_NAME" \
  --vpc-connector=growthreel-connector \
  --vpc-egress=private-ranges-only \
  --set-env-vars="$DB_ENV_VARS" \
  --set-secrets="$SECRET_VARS" \
  --command=python \
  --args=manage.py,migrate,--noinput

gcloud run jobs execute backend-migrate --region="$REGION" --wait
```

Create a superuser the same way, once:

```bash
gcloud run jobs create backend-createsuperuser \
  --image="$BACKEND_IMAGE" \
  --region="$REGION" \
  --add-cloudsql-instances="$CONNECTION_NAME" \
  --vpc-connector=growthreel-connector \
  --vpc-egress=private-ranges-only \
  --set-env-vars="$DB_ENV_VARS" \
  --set-secrets="$SECRET_VARS" \
  --command=python \
  --args="manage.py,shell,-c,\"from apps.users.models import User; User.objects.create_superuser(email='admin@growthreel.com', password='change-me-immediately')\""

gcloud run jobs execute backend-createsuperuser --region="$REGION" --wait
```

## 7. Deploy `api` and `frontend`

```bash
export API_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/api:latest"

gcloud run deploy api \
  --image="$API_IMAGE" \
  --region="$REGION" \
  --allow-unauthenticated \
  --port=8001 \
  --add-cloudsql-instances="$CONNECTION_NAME" \
  --vpc-connector=growthreel-connector \
  --vpc-egress=private-ranges-only \
  --set-env-vars="$DB_ENV_VARS,ENV=production,APP_FRONTEND_URL=https://placeholder.invalid,CORS_ORIGINS=https://placeholder.invalid" \
  --set-secrets="$SECRET_VARS"

export API_URL=$(gcloud run services describe api --region="$REGION" --format='value(status.url)')
echo "$API_URL"

export FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend:latest"

gcloud run deploy frontend \
  --image="$FRONTEND_IMAGE" \
  --region="$REGION" \
  --allow-unauthenticated \
  --set-env-vars="API_UPSTREAM=${API_URL}"

export FRONTEND_URL=$(gcloud run services describe frontend --region="$REGION" --format='value(status.url)')
echo "$FRONTEND_URL"
```

`frontend`'s own nginx (see `frontend-app/nginx.conf`) proxies same-origin
`/api/` calls to `API_UPSTREAM` — this keeps the httpOnly refresh-token cookie
same-origin from the browser's point of view, exactly like the docker-compose
setup does, just pointed at `api`'s real Cloud Run URL instead of a compose
service name.

## 8. Wire the real URLs together (redeploy `backend` + `api`)

```bash
export BACKEND_HOST=${BACKEND_URL#https://}

gcloud run services update backend \
  --region="$REGION" \
  --update-env-vars="DJANGO_ALLOWED_HOSTS=${BACKEND_HOST},APP_FRONTEND_URL=${FRONTEND_URL},CORS_ALLOWED_ORIGINS=${FRONTEND_URL}"

gcloud run services update api \
  --region="$REGION" \
  --update-env-vars="APP_FRONTEND_URL=${FRONTEND_URL},CORS_ORIGINS=${FRONTEND_URL}"
```

## 9. Verify

```bash
curl -I "$BACKEND_URL/"
curl -I "$FRONTEND_URL/"
curl -s "$API_URL/api/v1/health"   # adjust path if this project's health route differs
```

Visit `$FRONTEND_URL` and `$BACKEND_URL/admin/` (log in with the superuser
from step 6) in a browser.

## Redeploying after a code change

```bash
gcloud builds submit ./backend --tag="$BACKEND_IMAGE"
gcloud run deploy backend --image="$BACKEND_IMAGE" --region="$REGION"
# repeat the matching pair for api / frontend as needed
```

`gcloud run deploy` without the full flag list keeps every env var/secret/
Cloud SQL/VPC setting from the service's last revision — only re-pass flags
you're actually changing.

## Follow-ups not covered here

- **Custom domain**: `gcloud run domain-mappings create --service=frontend
  --domain=app.growthreel.com --region=$REGION` (and similarly for
  `backend`/`growthreel.com`) once DNS is pointed at Cloud Run.
- **`celery_worker`**: needs its own pass — likely a Cloud Run service with
  `--no-cpu-throttling --min-instances=1 --ingress=internal` (no public
  traffic, just a long-lived Redis consumer) rather than a request-driven
  deploy like the three above.
- **Migrations re-tracked in git**: fine for this manual, build-from-local-
  disk flow (`gcloud builds submit` uploads whatever's on disk right now,
  `.gcloudignore` already accounts for this). It becomes a real problem the
  moment you wire up a Cloud Build *trigger* from a GitHub push instead — a
  fresh clone has no `apps/*/migrations/*.py` at all. Worth revisiting
  `backend/.gitignore`'s `apps/*/migrations/` line if/when you set that up.
