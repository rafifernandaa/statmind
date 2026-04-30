#!/bin/bash
# StatMind — One-time GCP setup
# Run this ONCE before first deployment.
# Includes: SA creation, role grants (all roles from previous build lessons), Cloud SQL, Secret Manager
set -e

PROJECT_ID="YOUR-PROJECT-ID"
REGION="YOUR-REGION"
SA_NAME="statmind-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> Creating service account..."
gcloud iam service-accounts create "${SA_NAME}" \
  --display-name "StatMind Service Account" \
  --project "${PROJECT_ID}" || echo "SA already exists, skipping."

echo "==> Granting roles..."
for ROLE in \
  roles/bigquery.dataViewer \
  roles/bigquery.jobUser \
  roles/cloudsql.client \
  roles/secretmanager.secretAccessor \
  roles/aiplatform.user \
  roles/run.invoker; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member "serviceAccount:${SA_EMAIL}" \
    --role "${ROLE}"
done

echo "==> Creating Cloud SQL instance (PostgreSQL 15)..."
gcloud sql instances create statmind-db \
  --database-version POSTGRES_15 \
  --tier db-f1-micro \
  --region "${REGION}" \
  --project "${PROJECT_ID}" || echo "Instance may already exist."

echo "==> Creating database..."
gcloud sql databases create statmind \
  --instance statmind-db \
  --project "${PROJECT_ID}" || echo "Database may already exist."

echo "==> Creating DB user (save the password securely)..."
DB_PASS=$(openssl rand -base64 20)
gcloud sql users create statmind-user \
  --instance statmind-db \
  --password "${DB_PASS}" \
  --project "${PROJECT_ID}" || echo "User may already exist."

echo "==> Storing secrets..."
echo -n "statmind-user" | gcloud secrets create statmind-db-user --data-file=- --project "${PROJECT_ID}" 2>/dev/null || \
  echo -n "statmind-user" | gcloud secrets versions add statmind-db-user --data-file=-

echo -n "${DB_PASS}" | gcloud secrets create statmind-db-pass --data-file=- --project "${PROJECT_ID}" 2>/dev/null || \
  echo -n "${DB_PASS}" | gcloud secrets versions add statmind-db-pass --data-file=-

echo -n "statmind" | gcloud secrets create statmind-db-name --data-file=- --project "${PROJECT_ID}" 2>/dev/null || \
  echo -n "statmind" | gcloud secrets versions add statmind-db-name --data-file=-

echo ""
echo "==> GCP setup complete."
