from __future__ import annotations

from fastmcp import FastMCP

from database import init_database
from services import BusinessError
from services import consultar_proveedor as consultar_proveedor_service
from services import registrar_proveedor as registrar_proveedor_service


mcp = FastMCP(
    name="ComprasMCP",
    instructions=(
        "Servidor MCP para registrar y consultar información "
        "de proveedores, requisiciones, órdenes, facturas y pagos. "
        "Las operaciones de escritura requieren confirmar=true."
    ),
)


def execute_service(service, **kwargs) -> dict:
    try:
        return service(**kwargs)
    except BusinessError as exc:
        return {
            "ok": False,
            "tipo_error": "regla_negocio",
            "mensaje": str(exc),
        }
    except Exception:
        return {
            "ok": False,
            "tipo_error": "error_interno",
            "mensaje": "Ocurrió un error interno controlado.",
        }


@mcp.tool
def registrar_proveedor(
    nombre: str,
    rfc: str,
    condicion_pago: str,
    dias_credito: int = 0,
    confirmar: bool = False,
) -> dict:
    """
    Registra un proveedor.

    Esta operación modifica la base de datos y requiere
    confirmar=True. No debe utilizarse para actualizar proveedores.
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
def consultar_proveedor(criterio: str) -> dict:
    """
    Busca un proveedor por ID, RFC o parte de su nombre.
    No modifica información.
    """
    return execute_service(
        consultar_proveedor_service,
        criterio=criterio,
    )


if __name__ == "__main__":
    init_database()

    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000,
    )