from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", "data/compras.db")
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS proveedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proveedor_id TEXT UNIQUE NOT NULL,
    nombre TEXT NOT NULL,
    rfc TEXT UNIQUE NOT NULL,
    condicion_pago TEXT NOT NULL,
    dias_credito INTEGER NOT NULL DEFAULT 0,
    fecha_creacion TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS requisiciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folio TEXT UNIQUE NOT NULL,
    solicitante TEXT NOT NULL,
    area TEXT NOT NULL,
    tipo TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    importe_estimado REAL NOT NULL,
    proyecto TEXT,
    estado TEXT NOT NULL,
    fecha_creacion TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ordenes_compra (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folio TEXT UNIQUE NOT NULL,
    requisicion_folio TEXT UNIQUE NOT NULL,
    proveedor_id TEXT NOT NULL,
    importe REAL NOT NULL,
    estado TEXT NOT NULL,
    fecha_creacion TEXT NOT NULL,
    FOREIGN KEY (requisicion_folio)
        REFERENCES requisiciones(folio),
    FOREIGN KEY (proveedor_id)
        REFERENCES proveedores(proveedor_id)
);

CREATE TABLE IF NOT EXISTS facturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factura_id TEXT UNIQUE NOT NULL,
    orden_folio TEXT UNIQUE NOT NULL,
    numero_factura TEXT NOT NULL,
    fecha_factura TEXT NOT NULL,
    subtotal REAL NOT NULL,
    impuestos REAL NOT NULL,
    total REAL NOT NULL,
    fecha_vencimiento TEXT NOT NULL,
    estado_pago TEXT NOT NULL,
    fecha_creacion TEXT NOT NULL,
    FOREIGN KEY (orden_folio)
        REFERENCES ordenes_compra(folio)
);

CREATE TABLE IF NOT EXISTS pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pago_id TEXT UNIQUE NOT NULL,
    factura_id TEXT UNIQUE NOT NULL,
    fecha_pago TEXT NOT NULL,
    importe REAL NOT NULL,
    medio TEXT NOT NULL,
    referencia TEXT NOT NULL,
    fecha_creacion TEXT NOT NULL,
    FOREIGN KEY (factura_id)
        REFERENCES facturas(factura_id)
);

CREATE INDEX IF NOT EXISTS idx_proveedores_nombre
    ON proveedores(nombre);

CREATE INDEX IF NOT EXISTS idx_facturas_vencimiento
    ON facturas(fecha_vencimiento, estado_pago);
"""


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    connection = get_connection()

    try:
        # Bloquea escrituras concurrentes mientras se calcula el folio.
        connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database() -> None:
    connection = get_connection()

    try:
        connection.executescript(SCHEMA_SQL)
        connection.commit()
    finally:
        connection.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


if __name__ == "__main__":
    init_database()
    print(f"Base creada en: {DATABASE_PATH.resolve()}")