-- Dataset y tabla de salida de la API.
-- Se ejecuta una sola vez, antes del primer despliegue.

CREATE SCHEMA IF NOT EXISTS `dp-mlops17-ohuaman-pf-proc.ds_tarea_api`
OPTIONS (location = 'us-central1');

CREATE TABLE IF NOT EXISTS
  `dp-mlops17-ohuaman-pf-proc.ds_tarea_api.predicciones_api`
(
  prediction      INT64     OPTIONS (description = 'Prediccion truncada a entero'),
  prediction_log  FLOAT64   OPTIONS (description = 'Salida cruda del modelo, en logaritmo'),
  precio_usd      FLOAT64   OPTIONS (description = 'Precio reconstruido: exp(prediction_log)'),
  creation_user   STRING    OPTIONS (description = 'Proceso que escribio la fila'),
  process_date    DATE      OPTIONS (description = 'Fecha del proceso'),
  load_date       TIMESTAMP OPTIONS (description = 'Momento exacto de la carga')
);
