from __future__ import annotations

import sqlite3
import unicodedata
from datetime import date, datetime, timedelta, timezone

from database import get_connection, row_to_dict, transaction


REQ_AUTORIZADA = "Autorizada"
REQ_EN_COMPRA = "En compra"
REQ_FACTURADA = "Facturada"
REQ_PAGADA = "Pagada"

ORDEN_EMITIDA = "Emitida"
ORDEN_FACTURADA = "Facturada"
ORDEN_PAGADA = "Pagada"

FACTURA_PENDIENTE = "Pendiente"
FACTURA_PAGADA = "Pagada"

MEDIOS_PAGO = {
    "transferencia",
    "efectivo",
    "tarjeta",
    "cheque",
}

TABLAS_CON_FOLIO = {
    "proveedores",
    "requisiciones",
    "ordenes_compra",
    "facturas",
    "pagos",
}


class BusinessError(ValueError):
    """Error esperado de validación o regla de negocio."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_choice(value: str) -> str:
    normalized = normalize_text(value).lower()
    return "".join(
        character
        for character in unicodedata.normalize("NFD", normalized)
        if unicodedata.category(character) != "Mn"
    )


def normalize_rfc(value: str) -> str:
    return normalize_text(value).upper()


def normalize_code(value: str) -> str:
    return normalize_text(value).upper()


def next_folio(
    connection: sqlite3.Connection,
    table: str,
    prefix: str,
    width: int,
) -> str:
    if table not in TABLAS_CON_FOLIO:
        raise ValueError(
            f"Tabla no permitida para generación de folios: {table}"
        )

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
    condicion_pago = normalize_choice(condicion_pago)

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

    with transaction() as connection:
        duplicate = connection.execute(
            """
            SELECT proveedor_id
            FROM proveedores
            WHERE UPPER(rfc) = UPPER(?)
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


def crear_requisicion(
    solicitante: str,
    area: str,
    tipo: str,
    descripcion: str,
    importe_estimado: float,
    proyecto: str | None = None,
    confirmar: bool = False,
) -> dict:
    solicitante = normalize_text(solicitante)
    area = normalize_text(area)
    tipo = normalize_text(tipo)
    descripcion = normalize_text(descripcion)
    proyecto = normalize_text(proyecto) if proyecto else None

    if not solicitante:
        raise BusinessError("El solicitante es obligatorio.")

    if not area:
        raise BusinessError("El área es obligatoria.")

    if not tipo:
        raise BusinessError("El tipo de requisición es obligatorio.")

    if not descripcion:
        raise BusinessError("La descripción es obligatoria.")

    if importe_estimado <= 0:
        raise BusinessError(
            "El importe estimado debe ser mayor que cero."
        )

    if not confirmar:
        return {
            "creado": False,
            "requiere_confirmacion": True,
            "mensaje": (
                f"Se creará una requisición de tipo {tipo} "
                f"para el área {area}, solicitada por {solicitante}, "
                f"con importe estimado de {importe_estimado}."
            ),
        }

    with transaction() as connection:
        folio = next_folio(
            connection,
            table="requisiciones",
            prefix="REQ",
            width=4,
        )

        connection.execute(
            """
            INSERT INTO requisiciones (
                folio,
                solicitante,
                area,
                tipo,
                descripcion,
                importe_estimado,
                proyecto,
                estado,
                fecha_creacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                folio,
                solicitante,
                area,
                tipo,
                descripcion,
                importe_estimado,
                proyecto,
                REQ_AUTORIZADA,
                utc_now_iso(),
            ),
        )

    return {
        "creado": True,
        "folio": folio,
        "solicitante": solicitante,
        "area": area,
        "tipo": tipo,
        "descripcion": descripcion,
        "estado": REQ_AUTORIZADA,
        "importe_estimado": importe_estimado,
        "proyecto": proyecto,
    }


def crear_orden_compra(
    requisicion_folio: str,
    proveedor_id: str,
    importe: float,
    confirmar: bool = False,
) -> dict:
    requisicion_folio = normalize_code(requisicion_folio)
    proveedor_id = normalize_code(proveedor_id)

    if not requisicion_folio:
        raise BusinessError(
            "El folio de la requisición es obligatorio."
        )

    if not proveedor_id:
        raise BusinessError("El ID del proveedor es obligatorio.")

    if importe <= 0:
        raise BusinessError("El importe debe ser mayor que cero.")

    if not confirmar:
        return {
            "creado": False,
            "requiere_confirmacion": True,
            "mensaje": (
                f"Se creará la orden de compra para la requisición "
                f"{requisicion_folio} con el proveedor {proveedor_id} "
                f"y un importe de {importe}."
            ),
        }

    with transaction() as connection:
        requisicion = connection.execute(
            """
            SELECT estado
            FROM requisiciones
            WHERE UPPER(folio) = UPPER(?)
            """,
            (requisicion_folio,),
        ).fetchone()

        if not requisicion:
            raise BusinessError(
                f"No se encontró la requisición {requisicion_folio}."
            )

        orden_existente = connection.execute(
            """
            SELECT folio
            FROM ordenes_compra
            WHERE UPPER(requisicion_folio) = UPPER(?)
            """,
            (requisicion_folio,),
        ).fetchone()

        if orden_existente:
            raise BusinessError(
                f"La requisición {requisicion_folio} ya tiene "
                f"la orden {orden_existente['folio']}."
            )

        if requisicion["estado"] != REQ_AUTORIZADA:
            raise BusinessError(
                f"La requisición {requisicion_folio} no está autorizada."
            )

        proveedor = connection.execute(
            """
            SELECT proveedor_id
            FROM proveedores
            WHERE UPPER(proveedor_id) = UPPER(?)
            """,
            (proveedor_id,),
        ).fetchone()

        if not proveedor:
            raise BusinessError(
                f"No se encontró el proveedor {proveedor_id}."
            )

        folio_orden = next_folio(
            connection,
            table="ordenes_compra",
            prefix="OC",
            width=4,
        )

        connection.execute(
            """
            INSERT INTO ordenes_compra (
                folio,
                requisicion_folio,
                proveedor_id,
                importe,
                estado,
                fecha_creacion
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                folio_orden,
                requisicion_folio,
                proveedor["proveedor_id"],
                importe,
                ORDEN_EMITIDA,
                utc_now_iso(),
            ),
        )

        connection.execute(
            """
            UPDATE requisiciones
            SET estado = ?
            WHERE UPPER(folio) = UPPER(?)
            """,
            (REQ_EN_COMPRA, requisicion_folio),
        )

    return {
        "creado": True,
        "orden_folio": folio_orden,
        "requisicion_folio": requisicion_folio,
        "proveedor_id": proveedor["proveedor_id"],
        "importe": importe,
        "estado": ORDEN_EMITIDA,
    }


def registrar_factura(
    orden_folio: str,
    numero_factura: str,
    fecha_factura: str,
    subtotal: float,
    impuestos: float,
    total: float,
    confirmar: bool = False,
) -> dict:
    orden_folio = normalize_code(orden_folio)
    numero_factura = normalize_text(numero_factura)
    fecha_factura = normalize_text(fecha_factura)

    if not orden_folio:
        raise BusinessError("El folio de la orden es obligatorio.")

    if not numero_factura:
        raise BusinessError("El número de factura es obligatorio.")

    if not fecha_factura:
        raise BusinessError("La fecha de factura es obligatoria.")

    if subtotal < 0:
        raise BusinessError("El subtotal no puede ser negativo.")

    if impuestos < 0:
        raise BusinessError("Los impuestos no pueden ser negativos.")

    if total <= 0:
        raise BusinessError("El total debe ser mayor que cero.")

    if abs((subtotal + impuestos) - total) > 0.01:
        raise BusinessError(
            "El subtotal más los impuestos no coincide con el total."
        )

    try:
        fecha = date.fromisoformat(fecha_factura)
    except ValueError as exc:
        raise BusinessError(
            "La fecha de factura debe tener formato AAAA-MM-DD."
        ) from exc

    if not confirmar:
        return {
            "creado": False,
            "requiere_confirmacion": True,
            "mensaje": (
                f"Se registrará la factura {numero_factura} "
                f"para la orden {orden_folio}, con subtotal {subtotal}, "
                f"impuestos {impuestos} y total {total}."
            ),
        }

    with transaction() as connection:
        orden = connection.execute(
            """
            SELECT
                oc.estado,
                oc.requisicion_folio,
                p.condicion_pago,
                p.dias_credito
            FROM ordenes_compra AS oc
            JOIN proveedores AS p
              ON p.proveedor_id = oc.proveedor_id
            WHERE UPPER(oc.folio) = UPPER(?)
            """,
            (orden_folio,),
        ).fetchone()

        if not orden:
            raise BusinessError(
                f"No se encontró la orden {orden_folio}."
            )

        factura_existente = connection.execute(
            """
            SELECT factura_id
            FROM facturas
            WHERE UPPER(orden_folio) = UPPER(?)
            """,
            (orden_folio,),
        ).fetchone()

        if factura_existente:
            raise BusinessError(
                f"La orden {orden_folio} ya tiene la factura "
                f"{factura_existente['factura_id']}."
            )

        if orden["estado"] != ORDEN_EMITIDA:
            raise BusinessError(
                f"La orden {orden_folio} no está emitida."
            )

        dias_vencimiento = (
            orden["dias_credito"]
            if orden["condicion_pago"] == "credito"
            else 0
        )

        fecha_vencimiento = (
            fecha + timedelta(days=dias_vencimiento)
        ).isoformat()

        factura_id = next_folio(
            connection,
            table="facturas",
            prefix="FAC",
            width=4,
        )

        connection.execute(
            """
            INSERT INTO facturas (
                factura_id,
                orden_folio,
                numero_factura,
                fecha_factura,
                subtotal,
                impuestos,
                total,
                fecha_vencimiento,
                estado_pago,
                fecha_creacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                factura_id,
                orden_folio,
                numero_factura,
                fecha_factura,
                subtotal,
                impuestos,
                total,
                fecha_vencimiento,
                FACTURA_PENDIENTE,
                utc_now_iso(),
            ),
        )

        connection.execute(
            """
            UPDATE ordenes_compra
            SET estado = ?
            WHERE UPPER(folio) = UPPER(?)
            """,
            (ORDEN_FACTURADA, orden_folio),
        )

        connection.execute(
            """
            UPDATE requisiciones
            SET estado = ?
            WHERE UPPER(folio) = UPPER(?)
            """,
            (REQ_FACTURADA, orden["requisicion_folio"]),
        )

    return {
        "creado": True,
        "factura_id": factura_id,
        "orden_folio": orden_folio,
        "numero_factura": numero_factura,
        "fecha_factura": fecha_factura,
        "subtotal": subtotal,
        "impuestos": impuestos,
        "total": total,
        "condicion_pago": orden["condicion_pago"],
        "dias_credito": orden["dias_credito"],
        "fecha_vencimiento": fecha_vencimiento,
        "estado_pago": FACTURA_PENDIENTE,
    }


def registrar_pago(
    factura_id: str,
    fecha_pago: str,
    importe: float,
    medio: str,
    referencia: str,
    confirmar: bool = False,
) -> dict:
    factura_id = normalize_code(factura_id)
    fecha_pago = normalize_text(fecha_pago)
    medio = normalize_choice(medio)
    referencia = normalize_text(referencia)

    if not factura_id:
        raise BusinessError("El ID de la factura es obligatorio.")

    if not fecha_pago:
        raise BusinessError("La fecha de pago es obligatoria.")

    if importe <= 0:
        raise BusinessError("El importe debe ser mayor que cero.")

    if medio not in MEDIOS_PAGO:
        raise BusinessError(
            "El medio debe ser transferencia, efectivo, tarjeta o cheque."
        )

    if not referencia:
        raise BusinessError("La referencia es obligatoria.")

    try:
        date.fromisoformat(fecha_pago)
    except ValueError as exc:
        raise BusinessError(
            "La fecha de pago debe tener formato AAAA-MM-DD."
        ) from exc

    if not confirmar:
        return {
            "registrado": False,
            "requiere_confirmacion": True,
            "mensaje": (
                f"Se registrará el pago de {importe} para la factura "
                f"{factura_id}, mediante {medio}, con referencia "
                f"{referencia} y fecha {fecha_pago}."
            ),
        }

    with transaction() as connection:
        factura = connection.execute(
            """
            SELECT
                f.estado_pago,
                f.total,
                f.orden_folio,
                oc.requisicion_folio
            FROM facturas AS f
            JOIN ordenes_compra AS oc
              ON oc.folio = f.orden_folio
            WHERE UPPER(f.factura_id) = UPPER(?)
            """,
            (factura_id,),
        ).fetchone()

        if not factura:
            raise BusinessError(
                f"No se encontró la factura {factura_id}."
            )

        pago_existente = connection.execute(
            """
            SELECT pago_id
            FROM pagos
            WHERE UPPER(factura_id) = UPPER(?)
            """,
            (factura_id,),
        ).fetchone()

        if pago_existente:
            raise BusinessError(
                f"La factura {factura_id} ya tiene el pago "
                f"{pago_existente['pago_id']}."
            )

        if factura["estado_pago"] != FACTURA_PENDIENTE:
            raise BusinessError(
                f"La factura {factura_id} no está pendiente de pago."
            )

        if abs(importe - factura["total"]) > 0.01:
            raise BusinessError(
                "La PoC solo permite pagos completos. "
                f"El total de la factura es {factura['total']}."
            )

        pago_id = next_folio(
            connection,
            table="pagos",
            prefix="PAG",
            width=4,
        )

        connection.execute(
            """
            INSERT INTO pagos (
                pago_id,
                factura_id,
                fecha_pago,
                importe,
                medio,
                referencia,
                fecha_creacion
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pago_id,
                factura_id,
                fecha_pago,
                importe,
                medio,
                referencia,
                utc_now_iso(),
            ),
        )

        connection.execute(
            """
            UPDATE facturas
            SET estado_pago = ?
            WHERE UPPER(factura_id) = UPPER(?)
            """,
            (FACTURA_PAGADA, factura_id),
        )

        connection.execute(
            """
            UPDATE ordenes_compra
            SET estado = ?
            WHERE UPPER(folio) = UPPER(?)
            """,
            (ORDEN_PAGADA, factura["orden_folio"]),
        )

        connection.execute(
            """
            UPDATE requisiciones
            SET estado = ?
            WHERE UPPER(folio) = UPPER(?)
            """,
            (REQ_PAGADA, factura["requisicion_folio"]),
        )

    return {
        "registrado": True,
        "pago_id": pago_id,
        "factura_id": factura_id,
        "fecha_pago": fecha_pago,
        "importe": importe,
        "medio": medio,
        "referencia": referencia,
        "estado_pago": FACTURA_PAGADA,
    }


def consultar_requisicion(folio: str) -> dict:
    folio = normalize_code(folio)

    if not folio:
        raise BusinessError(
            "El folio de la requisición es obligatorio."
        )

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                folio,
                solicitante,
                area,
                tipo,
                descripcion,
                importe_estimado,
                proyecto,
                estado,
                fecha_creacion
            FROM requisiciones
            WHERE UPPER(folio) = UPPER(?)
            """,
            (folio,),
        ).fetchone()
    finally:
        connection.close()

    requisicion = row_to_dict(row)

    if requisicion is None:
        return {
            "encontrada": False,
            "folio": folio,
            "mensaje": "No se encontró la requisición.",
        }

    return {
        "encontrada": True,
        **requisicion,
    }


def consultar_orden_compra(folio: str) -> dict:
    folio = normalize_code(folio)

    if not folio:
        raise BusinessError(
            "El folio de la orden de compra es obligatorio."
        )

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT
                folio,
                requisicion_folio,
                proveedor_id,
                importe,
                estado,
                fecha_creacion
            FROM ordenes_compra
            WHERE UPPER(folio) = UPPER(?)
            """,
            (folio,),
        ).fetchone()
    finally:
        connection.close()

    orden = row_to_dict(row)

    if orden is None:
        return {
            "encontrada": False,
            "folio": folio,
            "mensaje": "No se encontró la orden de compra.",
        }

    return {
        "encontrada": True,
        **orden,
    }


def consultar_trazabilidad_compra(
    requisicion_folio: str,
) -> dict:
    requisicion_folio = normalize_code(requisicion_folio)

    if not requisicion_folio:
        raise BusinessError(
            "El folio de la requisición es obligatorio."
        )

    connection = get_connection()

    try:
        requisicion = row_to_dict(
            connection.execute(
                """
                SELECT
                    folio,
                    solicitante,
                    area,
                    tipo,
                    descripcion,
                    importe_estimado,
                    proyecto,
                    estado,
                    fecha_creacion
                FROM requisiciones
                WHERE UPPER(folio) = UPPER(?)
                """,
                (requisicion_folio,),
            ).fetchone()
        )

        if requisicion is None:
            return {
                "encontrada": False,
                "folio": requisicion_folio,
                "mensaje": "No se encontró la requisición.",
            }

        orden = row_to_dict(
            connection.execute(
                """
                SELECT
                    folio,
                    requisicion_folio,
                    proveedor_id,
                    importe,
                    estado,
                    fecha_creacion
                FROM ordenes_compra
                WHERE UPPER(requisicion_folio) = UPPER(?)
                """,
                (requisicion_folio,),
            ).fetchone()
        )

        proveedor = None
        factura = None
        pago = None

        if orden is not None:
            proveedor = row_to_dict(
                connection.execute(
                    """
                    SELECT
                        proveedor_id,
                        nombre,
                        rfc,
                        condicion_pago,
                        dias_credito
                    FROM proveedores
                    WHERE UPPER(proveedor_id) = UPPER(?)
                    """,
                    (orden["proveedor_id"],),
                ).fetchone()
            )

            factura = row_to_dict(
                connection.execute(
                    """
                    SELECT
                        factura_id,
                        orden_folio,
                        numero_factura,
                        fecha_factura,
                        subtotal,
                        impuestos,
                        total,
                        fecha_vencimiento,
                        estado_pago,
                        fecha_creacion
                    FROM facturas
                    WHERE UPPER(orden_folio) = UPPER(?)
                    """,
                    (orden["folio"],),
                ).fetchone()
            )

        if factura is not None:
            pago = row_to_dict(
                connection.execute(
                    """
                    SELECT
                        pago_id,
                        factura_id,
                        fecha_pago,
                        importe,
                        medio,
                        referencia,
                        fecha_creacion
                    FROM pagos
                    WHERE UPPER(factura_id) = UPPER(?)
                    """,
                    (factura["factura_id"],),
                ).fetchone()
            )
    finally:
        connection.close()

    return {
        "encontrada": True,
        "requisicion": requisicion,
        "orden_compra": orden,
        "proveedor": proveedor,
        "factura": factura,
        "pago": pago,
    }


def listar_pagos_por_vencer(dias: int) -> dict:
    if dias <= 0:
        raise BusinessError(
            "El número de días debe ser mayor que cero."
        )

    if dias > 90:
        raise BusinessError(
            "El rango máximo permitido es de 90 días."
        )

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                f.factura_id,
                f.numero_factura,
                f.total,
                f.fecha_vencimiento,
                f.estado_pago,
                oc.folio AS orden_folio,
                oc.requisicion_folio,
                p.proveedor_id,
                p.nombre AS proveedor,
                CAST(
                    JULIANDAY(DATE(f.fecha_vencimiento))
                    - JULIANDAY(DATE('now'))
                    AS INTEGER
                ) AS dias_restantes
            FROM facturas AS f
            JOIN ordenes_compra AS oc
              ON oc.folio = f.orden_folio
            JOIN proveedores AS p
              ON p.proveedor_id = oc.proveedor_id
            WHERE f.estado_pago = ?
              AND DATE(f.fecha_vencimiento)
                  BETWEEN DATE('now')
                      AND DATE('now', ?)
            ORDER BY DATE(f.fecha_vencimiento)
            """,
            (
                FACTURA_PENDIENTE,
                f"+{dias} days",
            ),
        ).fetchall()
    finally:
        connection.close()

    pagos = [row_to_dict(row) for row in rows]

    return {
        "dias_consultados": dias,
        "cantidad": len(pagos),
        "pagos": pagos,
    }