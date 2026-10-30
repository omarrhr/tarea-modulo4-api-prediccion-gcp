# Asignación módulo 4 — API de predicción en GCP

Omar Rodrigo Huaman Rivera · DataPath, MLOps Engineer 17ª Edición

API de predicción construida con FastAPI, desplegada en Cloud Run con una
cuenta de servicio personalizada. Lee los datos de BigQuery y guarda las
predicciones en BigQuery.

```
BigQuery (entrada) → FastAPI en Cloud Run → modelo dentro de la imagen
                                          → predicción
                                          → BigQuery (salida)
```

---

## 1. Qué hace

| Endpoint | Método | Qué hace |
|---|---|---|
| `/` | GET | Devuelve el estado del servicio y las tablas que usa |
| `/health` | GET | Comprueba que el contenedor responde y el modelo está cargado |
| `/predict` | POST | Lee de BigQuery, predice y escribe el resultado en BigQuery |

`/predict` acepta `?limite=N` para acotar cuántas filas procesa. Sin él las
procesa todas.

El modelo es un `Lasso` que predice el **logaritmo** del precio de venta, así
que la tabla de salida guarda las tres formas: el entero truncado, el valor
crudo y el precio reconstruido en dólares.

---

## 2. Tablas de BigQuery

| | Tabla |
|---|---|
| **Entrada** | `dp-mlops17-ohuaman-pf-fuente.hist_table.input_data` |
| **Variables del modelo** | `dp-mlops17-ohuaman-pf-fuente.hist_table.selected_features` |
| **Salida** | `dp-mlops17-ohuaman-pf-proc.ds_tarea_api.predicciones_api` |

La tabla de salida vive en un dataset propio, `ds_tarea_api`, para no mezclar
los resultados de esta asignación con los del proyecto final. El SQL que la
crea está en `sql/tabla_salida.sql`.

---

## 3. Estructura

```
app/
  main.py                   la API FastAPI
model/
  linear_regression.joblib  el modelo, viaja dentro de la imagen
sql/
  tabla_salida.sql          dataset y tabla de salida
requirements.txt
Dockerfile
despliegue.sh               script con los 7 pasos del despliegue
```

---

## 4. Despliegue

Todo está en `despliegue.sh`:

```bash
bash despliegue.sh
```

Hace, en orden:

1. Habilita Cloud Run, Cloud Build, Artifact Registry y BigQuery
2. Crea el repositorio `api-prediccion` en **Artifact Registry**
3. Crea la cuenta de servicio `sa-api-prediccion`
4. Le da los permisos mínimos: `dataViewer` sobre el dataset de entrada,
   `dataEditor` sobre el de salida, y `jobUser` + `readSessionUser` para poder
   lanzar consultas
5. Crea el dataset y la tabla de salida
6. Construye la imagen con **Cloud Build** y la publica en Artifact Registry
7. Despliega en **Cloud Run** con `--service-account`, que es el requisito de
   la asignación

Al terminar imprime la URL del servicio.

### Probarlo

```bash
curl $URL/health
curl -X POST "$URL/predict?limite=100"
```

La respuesta trae el número de filas escritas y la tabla de destino.

---

## 5. Notas

**El modelo va dentro de la imagen.** El `Dockerfile` copia `model/` y la API
lo carga con `joblib.load` al arrancar, no en cada petición. No hay servicio
aparte que lo sirva, que es lo que pide el enunciado.

**Configuración por variables de entorno.** El enunciado permite valores fijos
en el código, pero están como variables con valor por defecto, de modo que la
misma imagen sirve para otro entorno cambiando solo el despliegue.

**Permisos.** El enunciado no exige una matriz de permisos mínimos, solo que
Cloud Run corra con una cuenta propia. Aun así se conceden a nivel de dataset
y no de proyecto.
