#!/bin/bash
# Despliegue de la API en Cloud Run.
# Ejecutar desde la raiz del proyecto: bash despliegue.sh
set -e

PROJECT=dp-mlops17-ohuaman-pf-proc
FUENTE=dp-mlops17-ohuaman-pf-fuente
REGION=us-central1
REPO=api-prediccion
SERVICIO=api-prediccion-casas
SA=sa-api-prediccion
IMAGEN="$REGION-docker.pkg.dev/$PROJECT/$REPO/$SERVICIO"

echo "== 1. Habilitar las APIs necesarias =="
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  bigquery.googleapis.com \
  --project "$PROJECT"

echo "== 2. Crear el repositorio en Artifact Registry =="
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="Imagenes de la API de prediccion" \
  --project "$PROJECT" 2>/dev/null || echo "   ya existe, se reutiliza"

echo "== 3. Crear la cuenta de servicio personalizada =="
gcloud iam service-accounts create "$SA" \
  --display-name="SA API Prediccion - Tarea modulo 4" \
  --project "$PROJECT" 2>/dev/null || echo "   ya existe, se reutiliza"

SA_EMAIL="$SA@$PROJECT.iam.gserviceaccount.com"

echo "== 4. Crear la tabla de salida =="
bq query --use_legacy_sql=false --project_id="$PROJECT" < sql/tabla_salida.sql

echo "== 5. Permisos de la cuenta de servicio =="
# Roles de ejecucion, a nivel de proyecto: lanzar consultas y leer resultados.
# Ninguno de los dos da acceso a datos.
for ROL in roles/bigquery.jobUser roles/bigquery.readSessionUser; do
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:$SA_EMAIL" --role="$ROL" --condition=None --quiet > /dev/null
done

# Acceso a datos, a nivel de dataset. `bq add-iam-policy-binding` solo admite
# tablas y vistas, asi que para datasets se parchea su lista de accesos.
python permisos/conceder_dataset.py "$FUENTE:hist_table"      "$SA_EMAIL" READER
python permisos/conceder_dataset.py "$PROJECT:ds_tarea_api"   "$SA_EMAIL" WRITER

echo "== 6. Construir la imagen con Cloud Build =="
gcloud builds submit --tag "$IMAGEN:latest" --project "$PROJECT"

echo "== 7. Desplegar en Cloud Run con la cuenta de servicio personalizada =="
gcloud run deploy "$SERVICIO" \
  --image "$IMAGEN:latest" \
  --region "$REGION" \
  --platform managed \
  --service-account "$SA_EMAIL" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars "PROJECT=$PROJECT,INPUT_TABLE=$FUENTE.hist_table.input_data,FEATURES_TABLE=$FUENTE.hist_table.selected_features,OUTPUT_TABLE=$PROJECT.ds_tarea_api.predicciones_api,MODEL_PATH=model/linear_regression.joblib" \
  --project "$PROJECT"

URL=$(gcloud run services describe "$SERVICIO" --region "$REGION" \
  --project "$PROJECT" --format="value(status.url)")

echo
echo "Desplegado en: $URL"
echo
echo "Probar:"
echo "  curl $URL/health"
echo "  curl -X POST \"$URL/predict?limite=100\""
