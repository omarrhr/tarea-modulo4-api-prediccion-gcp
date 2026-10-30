"""API de prediccion de precios de vivienda.

Flujo: BigQuery (entrada) -> FastAPI en Cloud Run -> modelo dentro de la
imagen -> prediccion -> BigQuery (salida).

El modelo viaja dentro de la imagen Docker y se carga una sola vez al
arrancar el contenedor, no en cada peticion.
"""

import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pandas_gbq
from fastapi import FastAPI, HTTPException
from google.cloud import bigquery
from joblib import load

# Configuracion. El enunciado permite valores fijos en el codigo, pero por
# variables de entorno la misma imagen sirve para cualquier entorno.
PROJECT = os.getenv("PROJECT", "dp-mlops17-ohuaman-pf-proc")
INPUT_TABLE = os.getenv(
    "INPUT_TABLE", "dp-mlops17-ohuaman-pf-fuente.hist_table.input_data"
)
FEATURES_TABLE = os.getenv(
    "FEATURES_TABLE", "dp-mlops17-ohuaman-pf-fuente.hist_table.selected_features"
)
OUTPUT_TABLE = os.getenv(
    "OUTPUT_TABLE", "dp-mlops17-ohuaman-pf-proc.ds_tarea_api.predicciones_api"
)
MODEL_PATH = os.getenv("MODEL_PATH", "model/linear_regression.joblib")

app = FastAPI(
    title="API de prediccion de precios de vivienda",
    description="Asignacion modulo 4 - MLOps 17 - DataPath",
    version="1.0.0",
)

# El modelo se carga al arrancar, no en cada peticion.
modelo = load(MODEL_PATH)


@app.get("/")
def raiz():
    return {
        "servicio": "api-prediccion-casas",
        "estado": "activo",
        "tabla_entrada": INPUT_TABLE,
        "tabla_salida": OUTPUT_TABLE,
    }


@app.get("/health")
def health():
    """Para que Cloud Run compruebe que el contenedor responde."""
    return {"estado": "ok", "modelo_cargado": modelo is not None}


@app.post("/predict")
def predict(limite: int = 0):
    """Lee de BigQuery, predice y escribe el resultado en BigQuery.

    `limite` acota cuantas filas se leen; 0 las lee todas.
    """
    try:
        client = bigquery.Client(project=PROJECT)

        # 1. Las variables con las que se entreno el modelo
        features = client.query(f"SELECT * FROM `{FEATURES_TABLE}`").to_dataframe()
        features = features["string_field_0"].tolist()

        # 2. Los datos de entrada
        sql = f"SELECT * FROM `{INPUT_TABLE}`"
        if limite > 0:
            sql += f" LIMIT {limite}"
        datos = client.query(sql).to_dataframe()

        faltantes = [c for c in features if c not in datos.columns]
        if faltantes:
            raise ValueError(f"La tabla de entrada no tiene estas columnas: {faltantes}")

        X = datos[features]

        # 3. Prediccion. El modelo devuelve el logaritmo del precio.
        pred_log = modelo.predict(X)

        ahora = datetime.now(timezone.utc)
        salida = pd.DataFrame(
            {
                "prediction": pred_log.astype("int64"),
                "prediction_log": pred_log,
                "precio_usd": np.exp(pred_log).round(2),
                "creation_user": "api-prediccion-casas",
                "process_date": ahora.date(),
                "load_date": ahora,
            }
        )

        # 4. Guardar en BigQuery
        pandas_gbq.to_gbq(
            salida, OUTPUT_TABLE, project_id=PROJECT, if_exists="append"
        )

        return {
            "mensaje": "Prediccion generada y guardada en BigQuery",
            "filas": int(len(salida)),
            "tabla_entrada": INPUT_TABLE,
            "tabla_salida": OUTPUT_TABLE,
            "load_date": ahora.isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
