import os
from pathlib import Path

import pytest

os.environ["DATABASE_PATH"] = "data/test_compras.db"

from database import init_database
from services import BusinessError
from services import consultar_proveedor
from services import registrar_proveedor


TEST_DATABASE = Path("data/test_compras.db")


@pytest.fixture(autouse=True)
def clean_database():
    if TEST_DATABASE.exists():
        TEST_DATABASE.unlink()

    init_database()
    yield

    if TEST_DATABASE.exists():
        TEST_DATABASE.unlink()


def test_registrar_proveedor_requiere_confirmacion():
    result = registrar_proveedor(
        nombre="Tecnología Norte",
        rfc="TNO010101ABC",
        condicion_pago="credito",
        dias_credito=30,
    )

    assert result["creado"] is False
    assert result["requiere_confirmacion"] is True


def test_registrar_y_consultar_proveedor():
    creado = registrar_proveedor(
        nombre="Tecnología Norte",
        rfc="TNO010101ABC",
        condicion_pago="credito",
        dias_credito=30,
        confirmar=True,
    )

    consultado = consultar_proveedor(
        creado["proveedor_id"]
    )

    assert creado["creado"] is True
    assert consultado["encontrado"] is True
    assert consultado["rfc"] == "TNO010101ABC"


def test_no_permite_rfc_duplicado():
    registrar_proveedor(
        nombre="Proveedor Uno",
        rfc="AAA010101AAA",
        condicion_pago="contado",
        confirmar=True,
    )

    with pytest.raises(BusinessError):
        registrar_proveedor(
            nombre="Proveedor Dos",
            rfc="AAA010101AAA",
            condicion_pago="contado",
            confirmar=True,
        )