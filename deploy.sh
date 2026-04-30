set -e

PROJECT_ID="my-project-31-491314"
REGION="us-central1"
SERVICE="statmind-v1-1"
SA="statmind-sa@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE}"
SQL_INSTANCE="${PROJECT_ID}:${REGION}:statmind-db"

echo "==> Building image..."
gcloud builds submit --tag "${IMAGE}" .

echo "==> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --service-account "${SA}" \
  --set-env-vars "ENV=production,PROJECT_ID=${PROJECT_ID}" \
  --set-secrets "DB_USER=statmind-db-user:latest,DB_PASS=statmind-db-pass:latest,DB_NAME=statmind-db-name:latest" \
  --add-cloudsql-instances "${SQL_INSTANCE}" \
  --memory 1Gi \
  --cpu 1 \
  --concurrency 80 \
  --clear-base-image 

echo ""
echo "==> Deployed. URL:"
gcloud run services describe "${SERVICE}" --region "${REGION}" --format "value(status.url)"
