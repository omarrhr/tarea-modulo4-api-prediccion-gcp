"""Concede un rol a una cuenta de servicio sobre un dataset de BigQuery.

`bq add-iam-policy-binding` solo admite tablas y vistas, no datasets. Para un
dataset hay que parchear su lista `access`, que es lo que hace este script.

Uso:
    python conceder_dataset.py <proyecto:dataset> <email_sa> <READER|WRITER>

Equivalencias:
    READER -> roles/bigquery.dataViewer
    WRITER -> roles/bigquery.dataEditor
"""

import json
import subprocess
import sys
import tempfile
import os


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    dataset, email, rol = sys.argv[1], sys.argv[2], sys.argv[3].upper()
    if rol not in ("READER", "WRITER", "OWNER"):
        print(f"Rol no valido: {rol}")
        sys.exit(1)

    # shell=True con la orden como texto: asi funciona igual en Windows, donde
    # `bq` es un .cmd, que en Linux o Mac.
    meta = subprocess.run(
        f'bq show --format=prettyjson "{dataset}"',
        capture_output=True, text=True, shell=True,
    )
    if meta.returncode != 0:
        print(meta.stderr)
        sys.exit(1)

    datos = json.loads(meta.stdout)
    accesos = datos.setdefault("access", [])

    entrada = {"role": rol, "userByEmail": email}
    if entrada in accesos:
        print(f"   ya tenia {rol} sobre {dataset}, no se toca")
        return

    accesos.append(entrada)

    fd, ruta = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(datos, f)

    try:
        upd = subprocess.run(
            f'bq update --source "{ruta}" "{dataset}"',
            capture_output=True, text=True, shell=True,
        )
        if upd.returncode != 0:
            print(upd.stderr)
            sys.exit(1)
        print(f"   {rol} concedido a {email} sobre {dataset}")
    finally:
        os.unlink(ruta)


if __name__ == "__main__":
    main()
