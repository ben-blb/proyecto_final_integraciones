from __future__ import annotations

import argparse
from datetime import date, timedelta

from database import get_connection, init_database, transaction
from services import (
    crear_orden_compra,
    crear_requisicion,
    registrar_factura,
    registrar_pago,
    registrar_proveedor,
)


def has_existing_data() -> bool:
    connection = get_connection()

    try:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM proveedores"
        ).fetchone()
        return bool(row["total"])
    finally:
        connection.close()


def reset_database() -> None:
    """
    Elimina únicamente los datos de demostración.

    Se respeta el orden inverso de las relaciones para no violar
    las claves foráneas.
    """
    with transaction() as connection:
        connection.execute("DELETE FROM pagos")
        connection.execute("DELETE FROM facturas")
        connection.execute("DELETE FROM ordenes_compra")
        connection.execute("DELETE FROM requisiciones")
        connection.execute("DELETE FROM proveedores")

        # Reinicia los IDs AUTOINCREMENT para que los folios vuelvan
        # a comenzar desde PROV-001, REQ-0001, etc.
        connection.execute(
            """
            DELETE FROM sqlite_sequence
            WHERE name IN (
                'pagos',
                'facturas',
                'ordenes_compra',
                'requisiciones',
                'proveedores'
            )
            """
        )


def create_provider(
    nombre: str,
    rfc: str,
    condicion_pago: str,
    dias_credito: int,
) -> dict:
    return registrar_proveedor(
        nombre=nombre,
        rfc=rfc,
        condicion_pago=condicion_pago,
        dias_credito=dias_credito,
        confirmar=True,
    )


def create_requisition(
    solicitante: str,
    area: str,
    tipo: str,
    descripcion: str,
    importe_estimado: float,
    proyecto: str | None,
) -> dict:
    return crear_requisicion(
        solicitante=solicitante,
        area=area,
        tipo=tipo,
        descripcion=descripcion,
        importe_estimado=importe_estimado,
        proyecto=proyecto,
        confirmar=True,
    )


def create_order(
    requisicion_folio: str,
    proveedor_id: str,
    importe: float,
) -> dict:
    return crear_orden_compra(
        requisicion_folio=requisicion_folio,
        proveedor_id=proveedor_id,
        importe=importe,
        confirmar=True,
    )


def create_invoice(
    orden_folio: str,
    numero_factura: str,
    fecha_factura: date,
    subtotal: float,
    impuestos: float,
) -> dict:
    total = round(subtotal + impuestos, 2)

    return registrar_factura(
        orden_folio=orden_folio,
        numero_factura=numero_factura,
        fecha_factura=fecha_factura.isoformat(),
        subtotal=subtotal,
        impuestos=impuestos,
        total=total,
        confirmar=True,
    )


def create_payment(
    factura_id: str,
    fecha_pago: date,
    importe: float,
    medio: str,
    referencia: str,
) -> dict:
    return registrar_pago(
        factura_id=factura_id,
        fecha_pago=fecha_pago.isoformat(),
        importe=importe,
        medio=medio,
        referencia=referencia,
        confirmar=True,
    )


def seed_database() -> dict:
    today = date.today()

    # ------------------------------------------------------------------
    # Proveedores
    # ------------------------------------------------------------------
    papeleria = create_provider(
        nombre="Papelería Central",
        rfc="PCE010101ABC",
        condicion_pago="contado",
        dias_credito=0,
    )

    tecnologia = create_provider(
        nombre="Tecnología Norte",
        rfc="TNO020202DEF",
        condicion_pago="credito",
        dias_credito=30,
    )

    muebles = create_provider(
        nombre="Muebles del Centro",
        rfc="MCE030303GHI",
        condicion_pago="credito",
        dias_credito=7,
    )

    servicios = create_provider(
        nombre="Servicios Express",
        rfc="SEX040404JKL",
        condicion_pago="credito",
        dias_credito=60,
    )

    # ------------------------------------------------------------------
    # Escenario 1: compra pagada
    # ------------------------------------------------------------------
    req_pagada = create_requisition(
        solicitante="Ana Torres",
        area="Operaciones",
        tipo="Compra operativa",
        descripcion="Laptops para el equipo de supervisión",
        importe_estimado=58000.00,
        proyecto="Renovación tecnológica",
    )

    orden_pagada = create_order(
        requisicion_folio=req_pagada["folio"],
        proveedor_id=tecnologia["proveedor_id"],
        importe=58000.00,
    )

    factura_pagada = create_invoice(
        orden_folio=orden_pagada["orden_folio"],
        numero_factura="TEC-1001",
        fecha_factura=today - timedelta(days=45),
        subtotal=50000.00,
        impuestos=8000.00,
    )

    pago = create_payment(
        factura_id=factura_pagada["factura_id"],
        fecha_pago=today - timedelta(days=20),
        importe=factura_pagada["total"],
        medio="transferencia",
        referencia="TRX-DEMO-1001",
    )

    # ------------------------------------------------------------------
    # Escenario 2: factura pendiente que vence en 3 días
    # Proveedor con 7 días de crédito; factura emitida hace 4 días.
    # ------------------------------------------------------------------
    req_proxima = create_requisition(
        solicitante="Luis Mendoza",
        area="Administración",
        tipo="Compra de mobiliario",
        descripcion="Escritorios y sillas ergonómicas",
        importe_estimado=34800.00,
        proyecto="Adecuación de oficinas",
    )

    orden_proxima = create_order(
        requisicion_folio=req_proxima["folio"],
        proveedor_id=muebles["proveedor_id"],
        importe=34800.00,
    )

    factura_proxima = create_invoice(
        orden_folio=orden_proxima["orden_folio"],
        numero_factura="MOB-2001",
        fecha_factura=today - timedelta(days=4),
        subtotal=30000.00,
        impuestos=4800.00,
    )

    # ------------------------------------------------------------------
    # Escenario 3: factura pendiente que vence en 5 días
    # Proveedor con 30 días de crédito; factura emitida hace 25 días.
    # ------------------------------------------------------------------
    req_cinco_dias = create_requisition(
        solicitante="Mariana López",
        area="Sistemas",
        tipo="Compra de equipo",
        descripcion="Monitores para estaciones de desarrollo",
        importe_estimado=23200.00,
        proyecto="Expansión del equipo",
    )

    orden_cinco_dias = create_order(
        requisicion_folio=req_cinco_dias["folio"],
        proveedor_id=tecnologia["proveedor_id"],
        importe=23200.00,
    )

    factura_cinco_dias = create_invoice(
        orden_folio=orden_cinco_dias["orden_folio"],
        numero_factura="TEC-1002",
        fecha_factura=today - timedelta(days=25),
        subtotal=20000.00,
        impuestos=3200.00,
    )

    # ------------------------------------------------------------------
    # Escenario 4: factura vencida y todavía pendiente
    # Proveedor con 7 días de crédito; factura emitida hace 15 días.
    # ------------------------------------------------------------------
    req_vencida = create_requisition(
        solicitante="Carlos Ramírez",
        area="Ventas",
        tipo="Compra operativa",
        descripcion="Mobiliario para sala de atención",
        importe_estimado=17400.00,
        proyecto="Sucursal Centro",
    )

    orden_vencida = create_order(
        requisicion_folio=req_vencida["folio"],
        proveedor_id=muebles["proveedor_id"],
        importe=17400.00,
    )

    factura_vencida = create_invoice(
        orden_folio=orden_vencida["orden_folio"],
        numero_factura="MOB-2002",
        fecha_factura=today - timedelta(days=15),
        subtotal=15000.00,
        impuestos=2400.00,
    )

    # ------------------------------------------------------------------
    # Escenario 5: requisición autorizada, todavía sin orden
    # ------------------------------------------------------------------
    req_sin_orden = create_requisition(
        solicitante="Fernanda Ruiz",
        area="Recursos Humanos",
        tipo="Compra administrativa",
        descripcion="Papelería para capacitación interna",
        importe_estimado=4500.00,
        proyecto="Programa de inducción",
    )

    # ------------------------------------------------------------------
    # Escenario 6: orden emitida, todavía sin factura
    # ------------------------------------------------------------------
    req_sin_factura = create_requisition(
        solicitante="Jorge Salas",
        area="Mantenimiento",
        tipo="Servicio",
        descripcion="Mantenimiento preventivo de instalaciones",
        importe_estimado=12000.00,
        proyecto="Mantenimiento trimestral",
    )

    orden_sin_factura = create_order(
        requisicion_folio=req_sin_factura["folio"],
        proveedor_id=servicios["proveedor_id"],
        importe=12000.00,
    )

    # ------------------------------------------------------------------
    # Escenario 7: compra de contado con factura pendiente para hoy
    # ------------------------------------------------------------------
    req_contado = create_requisition(
        solicitante="Sofía Herrera",
        area="Dirección",
        tipo="Compra administrativa",
        descripcion="Consumibles de oficina",
        importe_estimado=2900.00,
        proyecto=None,
    )

    orden_contado = create_order(
        requisicion_folio=req_contado["folio"],
        proveedor_id=papeleria["proveedor_id"],
        importe=2900.00,
    )

    factura_contado = create_invoice(
        orden_folio=orden_contado["orden_folio"],
        numero_factura="PAP-3001",
        fecha_factura=today,
        subtotal=2500.00,
        impuestos=400.00,
    )

    return {
        "proveedores": [
            papeleria,
            tecnologia,
            muebles,
            servicios,
        ],
        "requisiciones": [
            req_pagada,
            req_proxima,
            req_cinco_dias,
            req_vencida,
            req_sin_orden,
            req_sin_factura,
            req_contado,
        ],
        "ordenes": [
            orden_pagada,
            orden_proxima,
            orden_cinco_dias,
            orden_vencida,
            orden_sin_factura,
            orden_contado,
        ],
        "facturas": [
            factura_pagada,
            factura_proxima,
            factura_cinco_dias,
            factura_vencida,
            factura_contado,
        ],
        "pagos": [pago],
    }


def print_summary(result: dict) -> None:
    print("\nDatos de demostración creados correctamente.\n")

    print(f"Proveedores:   {len(result['proveedores'])}")
    print(f"Requisiciones: {len(result['requisiciones'])}")
    print(f"Órdenes:       {len(result['ordenes'])}")
    print(f"Facturas:      {len(result['facturas'])}")
    print(f"Pagos:         {len(result['pagos'])}")

    print("\nEscenarios disponibles:")

    print(
        f"- Compra pagada: "
        f"{result['requisiciones'][0]['folio']}"
    )
    print(
        f"- Vence en 3 días: "
        f"{result['facturas'][1]['factura_id']}"
    )
    print(
        f"- Vence en 5 días: "
        f"{result['facturas'][2]['factura_id']}"
    )
    print(
        f"- Factura vencida: "
        f"{result['facturas'][3]['factura_id']}"
    )
    print(
        f"- Requisición sin orden: "
        f"{result['requisiciones'][4]['folio']}"
    )
    print(
        f"- Orden sin factura: "
        f"{result['ordenes'][4]['orden_folio']}"
    )
    print(
        f"- Factura de contado que vence hoy: "
        f"{result['facturas'][4]['factura_id']}"
    )

    print("\nConsultas sugeridas:")
    print("- Muéstrame la trazabilidad de REQ-0001.")
    print("- ¿Qué pagos vencen en los próximos siete días?")
    print("- Consulta la requisición REQ-0005.")
    print("- Consulta la orden OC-0005.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Carga datos ficticios para la PoC de compras."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Elimina los datos actuales antes de insertar "
            "los datos de demostración."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    init_database()

    if has_existing_data():
        if not args.reset:
            print(
                "La base ya contiene datos. Ejecuta:\n\n"
                "    python seed_data.py --reset\n\n"
                "para reemplazarlos por los datos de demostración."
            )
            return

        reset_database()

    result = seed_database()
    print_summary(result)


if __name__ == "__main__":
    main()