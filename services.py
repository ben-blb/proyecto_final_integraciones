from __future__ import annotations
from datetime import datetime, timezone
from database import get_connection, row_to_dict, transaction


class BusinessError(ValueError):
    """Error esperado de validación o regla de negocio."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_rfc(value: str) -> str:
    return normalize_text(value).upper()


def next_folio(
    connection,
    table: str,
    prefix: str,
    width: int,
) -> str:
    # table y prefix solo se proporcionan internamente.
    row = connection.execute(
        f"SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM {table}"
    ).fetchone()

    return f"{prefix}-{row['next_id']:0{width}d}"


def registrar_proveedor(
    nombre: str,
    rfc: str,
    condicion_pago: str,
    dias_credito: int = 0,
    confirmar: bool = False,
) -> dict:
    nombre = normalize_text(nombre)
    rfc = normalize_rfc(rfc)
    condicion_pago = normalize_text(condicion_pago).lower()

    if not confirmar:
        return {
            "creado": False,
            "requiere_confirmacion": True,
            "mensaje": (
                f"Se registrará el proveedor {nombre}, RFC {rfc}, "
                f"con condición {condicion_pago} y "
                f"{dias_credito} días de crédito."
            ),
        }

    if not nombre:
        raise BusinessError("El nombre es obligatorio.")

    if not rfc:
        raise BusinessError("El RFC es obligatorio.")

    if condicion_pago not in {"contado", "credito"}:
        raise BusinessError(
            "La condición de pago debe ser contado o credito."
        )

    if condicion_pago == "contado" and dias_credito != 0:
        raise BusinessError(
            "Un proveedor de contado debe tener cero días de crédito."
        )

    if condicion_pago == "credito" and dias_credito <= 0:
        raise BusinessError(
            "Un proveedor a crédito debe tener más de cero días."
        )

    with transaction() as connection:
        duplicate = connection.execute(
            """
            SELECT proveedor_id
            FROM proveedores
            WHERE UPPER(rfc) = ?
            """,
            (rfc,),
        ).fetchone()

        if duplicate:
            raise BusinessError(
                f"Ya existe un proveedor con RFC {rfc}."
            )

        proveedor_id = next_folio(
            connection,
            table="proveedores",
            prefix="PROV",
            width=3,
        )

        connection.execute(
            """
            INSERT INTO proveedores (
                proveedor_id,
                nombre,
                rfc,
                condicion_pago,
                dias_credito,
                fecha_creacion
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                proveedor_id,
                nombre,
                rfc,
                condicion_pago,
                dias_credito,
                utc_now_iso(),
            ),
        )

    return {
        "creado": True,
        "proveedor_id": proveedor_id,
        "nombre": nombre,
        "rfc": rfc,
        "condicion_pago": condicion_pago,
        "dias_credito": dias_credito,
    }


def consultar_proveedor(criterio: str) -> dict:
    criterio = normalize_text(criterio)

    if not criterio:
        raise BusinessError(
            "Debes proporcionar un ID, RFC o nombre."
        )

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                proveedor_id,
                nombre,
                rfc,
                condicion_pago,
                dias_credito
            FROM proveedores
            WHERE UPPER(proveedor_id) = UPPER(?)
               OR UPPER(rfc) = UPPER(?)
               OR UPPER(nombre) LIKE UPPER(?)
            ORDER BY
                CASE
                    WHEN UPPER(proveedor_id) = UPPER(?) THEN 1
                    WHEN UPPER(rfc) = UPPER(?) THEN 2
                    ELSE 3
                END
            LIMIT 1
            """,
            (
                criterio,
                criterio,
                f"%{criterio}%",
                criterio,
                criterio,
            ),
        ).fetchone()
    finally:
        connection.close()

    proveedor = row_to_dict(row)

    if proveedor is None:
        return {
            "encontrado": False,
            "criterio": criterio,
            "mensaje": "No se encontró ningún proveedor.",
        }

    return {
        "encontrado": True,
        **proveedor,
    }