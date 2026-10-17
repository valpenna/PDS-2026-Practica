import csv
from io import StringIO

from src.core.personal import Personal
from src.web.validators.personal import validar_fila_csv


COLUMNAS_ESPERADAS = (
    "dni",
    "nombre",
    "apellido",
    "tipo_personal",
    "sector",
    "menu",
)
NOMBRES_CAMPOS = {
    "dni": "DNI",
    "nombre": "nombre",
    "apellido": "apellido",
    "tipo_personal": "tipo de personal",
    "tipo_personal_id": "tipo de personal",
    "sector": "sector",
    "sector_id": "sector",
    "menu": "menú",
    "menu_id": "menú",
}
CLAVE_COLUMNAS_EXTRA = "__columnas_extra__"


def procesar_csv_personal(contenido: str) -> dict:
    """Valida las filas de un CSV e importa las que cumplen las reglas."""
    lector = csv.DictReader(
        StringIO(contenido),
        delimiter=",",
        restkey=CLAVE_COLUMNAS_EXTRA,
        restval=None,
    )

    if lector.fieldnames is None:
        return _resultado_archivo(
            [
                {
                    "campo": "Archivo",
                    "motivo": "El CSV está vacío o no contiene encabezado.",
                }
            ]
        )

    if (
        len(lector.fieldnames) != len(COLUMNAS_ESPERADAS)
        or set(lector.fieldnames) != set(COLUMNAS_ESPERADAS)
    ):
        detalles = [
            {
                "campo": "Encabezado",
                "motivo": f"Falta la columna '{columna}' en el encabezado.",
            }
            for columna in COLUMNAS_ESPERADAS
            if columna not in lector.fieldnames
        ] + [
            {
                "campo": "Encabezado",
                "motivo": f"La columna '{columna}' no es reconocida.",
            }
            for columna in lector.fieldnames
            if columna not in COLUMNAS_ESPERADAS
        ] + [
            {
                "campo": "Encabezado",
                "motivo": f"La columna '{columna}' aparece más de una vez.",
            }
            for columna in set(lector.fieldnames)
            if lector.fieldnames.count(columna) > 1
        ]
        return _resultado_archivo(detalles)

    procesados = 0
    importados = 0
    rechazados = 0
    filas_importadas = []
    errores_filas = []
    dnis_en_csv = set()

    for numero_fila, fila in enumerate(lector, start=2):
        procesados += 1
        dni = (fila.get("dni") or "").strip()
        columnas_faltantes = [
            columna
            for columna in COLUMNAS_ESPERADAS
            if fila.get(columna) is None
        ]
        columnas_extra = fila.get(CLAVE_COLUMNAS_EXTRA) or []

        if columnas_faltantes or columnas_extra:
            rechazados += 1
            detalles = []
            columnas_encontradas = (
                len(COLUMNAS_ESPERADAS)
                - len(columnas_faltantes)
                + len(columnas_extra)
            )
            if columnas_faltantes:
                detalles.append(
                    {
                        "campo": "Columnas",
                        "motivo": (
                            f"Falta{'n' if len(columnas_faltantes) > 1 else ''}: "
                            f"{', '.join(NOMBRES_CAMPOS[columna] for columna in columnas_faltantes)}. "
                            f"Se esperaban {len(COLUMNAS_ESPERADAS)} columnas y "
                            f"se encontraron {columnas_encontradas}."
                        ),
                    }
                )
            if columnas_extra:
                detalles.append(
                    {
                        "campo": "Columnas",
                        "motivo": (
                            f"Sobran {len(columnas_extra)} columna(s). "
                            f"Se esperaban {len(COLUMNAS_ESPERADAS)} columnas y "
                            f"se encontraron {columnas_encontradas}."
                        ),
                    }
                )
            if dni and dni in dnis_en_csv:
                detalles.append(
                    {
                        "campo": "DNI",
                        "motivo": "Está duplicado dentro del archivo CSV.",
                    }
                )
            elif dni:
                dnis_en_csv.add(dni)

            errores_filas.append(
                {"fila": numero_fila, "detalles": detalles}
            )
            continue

        datos, errores = validar_fila_csv(fila, dnis_en_csv)
        if errores:
            rechazados += 1
            errores_filas.append(
                {
                    "fila": numero_fila,
                    "detalles": [
                        {
                            "campo": NOMBRES_CAMPOS.get(campo, campo),
                            "motivo": motivo,
                        }
                        for campo, motivo in errores.items()
                    ],
                }
            )
            continue

        Personal.crear_personal(datos.model_dump())
        importados += 1
        filas_importadas.append(
            {
                "fila": numero_fila,
                "nombre": datos.nombre,
                "apellido": datos.apellido,
                "tipo_personal": fila.get("tipo_personal", "").strip(),
                "sector": fila.get("sector", "").strip() or "Sin sector",
                "menu": fila.get("menu", "").strip(),
            }
        )

    return {
        "procesados": procesados,
        "importados": importados,
        "rechazados": rechazados,
        "filas_importadas": filas_importadas,
        "errores": errores_filas,
    }


def _resultado_archivo(detalles: list[dict]) -> dict:
    """Construye el resumen de error cuando no se pueden procesar filas."""
    return {
        "procesados": 0,
        "importados": 0,
        "rechazados": 0,
        "filas_importadas": [],
        "errores": [{"fila": None, "detalles": detalles}],
    }
