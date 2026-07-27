from __future__ import annotations

import logging
import os
import sqlite3
from collections.abc import Callable
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from database import init_database
from services import (
    BusinessError,
    consultar_orden_compra as consultar_orden_compra_service,
    consultar_proveedor as consultar_proveedor_service,
    consultar_requisicion as consultar_requisicion_service,
    consultar_trazabilidad_compra as consultar_trazabilidad_compra_service,
    crear_orden_compra as crear_orden_compra_service,
    crear_requisicion as crear_requisicion_service,
    listar_pagos_por_vencer as listar_pagos_por_vencer_service,
    registrar_factura as registrar_factura_service,
    registrar_pago as registrar_pago_service,
    registrar_proveedor as registrar_proveedor_service,
)


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("compras_mcp")

MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))


mcp = FastMCP(
    name="Asistente de Compras MCP",
    instructions=(
        "Servidor MCP para consultar y registrar proveedores, requisiciones, "
        "órdenes de compra, facturas y pagos. Las operaciones de escritura "
        "requieren confirmar=true. No existen operaciones públicas para "
        "actualizar o eliminar registros. La PoC solo admite pagos completos."
    ),
    mask_error_details=True,
)


def execute_service(
    service: Callable[..., dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Ejecuta una operación de negocio y normaliza su respuesta MCP."""
    try:
        result = service(**kwargs)
        return {
            "ok": True,
            **result,
        }
    except BusinessError as exc:
        logger.info(
            "Regla de negocio rechazada en %s: %s",
            service.__name__,
            exc,
        )
        return {
            "ok": False,
            "tipo_error": "regla_negocio",
            "mensaje": str(exc),
        }
    except sqlite3.IntegrityError as exc:
        logger.exception(
            "Error de integridad en %s",
            service.__name__,
        )
        return {
            "ok": False,
            "tipo_error": "integridad_datos",
            "mensaje": (
                "La operación viola una restricción de integridad. "
                "Es posible que el registro ya exista o que falte "
                "un documento relacionado."
            ),
        }
    except Exception as exc:
        logger.exception(
            "Error inesperado en %s",
            service.__name__,
        )
        raise ToolError(
            "Ocurrió un error interno al ejecutar la operación."
        ) from exc


@mcp.tool
def registrar_proveedor(
    nombre: str,
    rfc: str,
    condicion_pago: str,
    dias_credito: int = 0,
    confirmar: bool = False,
) -> dict[str, Any]:
    """Registra un proveedor nuevo.

    Usa condicion_pago='contado' con dias_credito=0 o
    condicion_pago='credito' con dias_credito mayor que cero.
    Esta tool modifica datos únicamente cuando confirmar=True.
    Si confirmar=False, devuelve un resumen para solicitar confirmación.
    """
    return execute_service(
        registrar_proveedor_service,
        nombre=nombre,
        rfc=rfc,
        condicion_pago=condicion_pago,
        dias_credito=dias_credito,
        confirmar=confirmar,
    )


@mcp.tool
def consultar_proveedor(criterio: str) -> dict[str, Any]:
    """Consulta un proveedor por ID, RFC o parte de su nombre.

    No modifica información. Usa esta tool siempre que una respuesta dependa
    de datos reales del proveedor almacenados en SQLite.
    """
    return execute_service(
        consultar_proveedor_service,
        criterio=criterio,
    )


@mcp.tool
def crear_requisicion(
    solicitante: str,
    area: str,
    tipo: str,
    descripcion: str,
    importe_estimado: float,
    proyecto: str | None = None,
    confirmar: bool = False,
) -> dict[str, Any]:
    """Crea una requisición simplificada en estado Autorizada.

    Requiere solicitante, área, tipo, descripción e importe mayor que cero.
    El proyecto es opcional. Esta tool modifica datos únicamente cuando
    confirmar=True; con confirmar=False devuelve el resumen de confirmación.
    """
    return execute_service(
        crear_requisicion_service,
        solicitante=solicitante,
        area=area,
        tipo=tipo,
        descripcion=descripcion,
        importe_estimado=importe_estimado,
        proyecto=proyecto,
        confirmar=confirmar,
    )


@mcp.tool
def consultar_requisicion(folio: str) -> dict[str, Any]:
    """Consulta una requisición por su folio, por ejemplo REQ-0001.

    Devuelve los datos y el estado actual de la requisición. No modifica
    información.
    """
    return execute_service(
        consultar_requisicion_service,
        folio=folio,
    )


@mcp.tool
def crear_orden_compra(
    requisicion_folio: str,
    proveedor_id: str,
    importe: float,
    confirmar: bool = False,
) -> dict[str, Any]:
    """Crea una orden de compra para una requisición autorizada.

    La requisición y el proveedor deben existir. Solo se permite una orden
    por requisición. Esta tool modifica datos únicamente cuando
    confirmar=True; con confirmar=False devuelve el resumen de confirmación.
    """
    return execute_service(
        crear_orden_compra_service,
        requisicion_folio=requisicion_folio,
        proveedor_id=proveedor_id,
        importe=importe,
        confirmar=confirmar,
    )


@mcp.tool
def consultar_orden_compra(folio: str) -> dict[str, Any]:
    """Consulta una orden de compra por su folio, por ejemplo OC-0001.

    Esta operación es adicional al alcance mínimo de la PoC y no modifica
    información.
    """
    return execute_service(
        consultar_orden_compra_service,
        folio=folio,
    )


@mcp.tool
def registrar_factura(
    orden_folio: str,
    numero_factura: str,
    fecha_factura: str,
    subtotal: float,
    impuestos: float,
    total: float,
    confirmar: bool = False,
) -> dict[str, Any]:
    """Registra la única factura permitida para una orden de compra.

    fecha_factura debe usar el formato AAAA-MM-DD. El subtotal más los
    impuestos debe coincidir con el total. El vencimiento se calcula usando
    la condición de pago del proveedor. Esta tool modifica datos únicamente
    cuando confirmar=True.
    """
    return execute_service(
        registrar_factura_service,
        orden_folio=orden_folio,
        numero_factura=numero_factura,
        fecha_factura=fecha_factura,
        subtotal=subtotal,
        impuestos=impuestos,
        total=total,
        confirmar=confirmar,
    )


@mcp.tool
def registrar_pago(
    factura_id: str,
    fecha_pago: str,
    importe: float,
    medio: str,
    referencia: str,
    confirmar: bool = False,
) -> dict[str, Any]:
    """Registra el pago completo de una factura pendiente.

    fecha_pago debe usar el formato AAAA-MM-DD. Los medios permitidos son
    transferencia, efectivo, tarjeta y cheque. El importe debe coincidir con
    el total completo de la factura; no se admiten pagos parciales. Esta tool
    modifica datos únicamente cuando confirmar=True.
    """
    return execute_service(
        registrar_pago_service,
        factura_id=factura_id,
        fecha_pago=fecha_pago,
        importe=importe,
        medio=medio,
        referencia=referencia,
        confirmar=confirmar,
    )


@mcp.tool
def consultar_trazabilidad_compra(
    requisicion_folio: str,
) -> dict[str, Any]:
    """Consulta la cadena completa asociada a una requisición.

    Devuelve requisición, orden de compra, proveedor, factura y pago cuando
    existan. Usa esta tool para preguntas compuestas sobre estado,
    vencimiento o trazabilidad. No modifica información.
    """
    return execute_service(
        consultar_trazabilidad_compra_service,
        requisicion_folio=requisicion_folio,
    )


@mcp.tool
def listar_pagos_por_vencer(dias: int) -> dict[str, Any]:
    """Lista facturas pendientes que vencen desde hoy hasta N días.

    dias debe ser mayor que cero y no puede superar 90. La tool devuelve el
    proveedor, factura, importe, fecha de vencimiento y días restantes. No
    modifica información.
    """
    return execute_service(
        listar_pagos_por_vencer_service,
        dias=dias,
    )


def main() -> None:
    """Inicializa SQLite e inicia el servidor MCP por HTTP."""
    init_database()

    logger.info(
        "Iniciando MCP de compras en http://%s:%s/mcp",
        "127.0.0.1",
        8000,
    )

    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000,
    )


if __name__ == "__main__":
    main()