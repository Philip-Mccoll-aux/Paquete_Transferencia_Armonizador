"""Pruebas del cargador de contrato: gating, EFE aislado y conflictos."""
from __future__ import annotations

import openpyxl
import pytest

from armonizador import columnas as col
from armonizador.contrato import cargar_contrato

ESTADOS_HDR = [
    col.C_ID_GRUPO_CONSULTA,
    col.C_ID_M_PERSISTENTE,
    col.C_ID_CLIENTE,
    col.C_MES_ENERGIA,
    col.C_APTO_COMPOSICION,
    col.C_ESTADO_M,
]

COMPOSICION_HDR = [
    col.C_ID_CLIENTE,
    col.C_RUT_INTEGRACION,
    "CLIENTE",
    col.C_ID_M_PERSISTENTE,
    col.C_ID_GRUPO_CONSULTA,
    col.C_BARRAF_M,
    col.C_BARRA_INFOTECNICA_M,
    col.C_ID_BARRA_INFOTECNICA_M,
    col.C_MODO_CONSULTA,
    col.C_MES_ENERGIA,
    col.C_BARRAF_ORIGEN,
    "SUMINISTRADOR",
    col.C_FACTOR_ORIGEN_M,
    col.C_CONTRIBUCION_MWH,
    col.C_APTO_COMPOSICION,
    col.C_VERSION_RECETA,
]


def _construir_xlsx(ruta, filas_estados, filas_composicion):
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = col.HOJA_ESTADOS_M_MES
    ws1.append(ESTADOS_HDR)
    for fila in filas_estados:
        ws1.append(fila)
    ws2 = wb.create_sheet(col.HOJA_COMPOSICION_M)
    ws2.append(COMPOSICION_HDR)
    for fila in filas_composicion:
        ws2.append(fila)
    wb.save(ruta)


def test_grupo_apto_queda_activo(tmp_path):
    ruta = tmp_path / "contrato.xlsx"
    _construir_xlsx(
        ruta,
        filas_estados=[["CONSULTA:1", "M:1", "111", "2511", True, "RESUELTO"]],
        filas_composicion=[
            ["111", "111-1", "CLIENTE", "M:1", "CONSULTA:1", "B______220", "BA B 220", "1", "VECTOR_UNICO", "2511", "A______220", "SUP", 1, 10.0, True, "v1"],
        ],
    )
    contrato = cargar_contrato(str(ruta), "2511")
    receta = contrato.recetas["CONSULTA:1"]
    assert not receta.bloqueada
    assert receta.origenes == {"A______220"}
    assert contrato.origen_index[("111-1", "A______220")] == "CONSULTA:1"


def test_grupo_no_apto_composicion_queda_bloqueado(tmp_path):
    ruta = tmp_path / "contrato.xlsx"
    _construir_xlsx(
        ruta,
        filas_estados=[["CONSULTA:1", "M:1", "111", "2511", False, "RESUELTO"]],
        filas_composicion=[
            ["111", "111-1", "CLIENTE", "M:1", "CONSULTA:1", "B______220", "BA B 220", "1", "VECTOR_UNICO", "2511", "A______220", "SUP", 1, 10.0, True, "v1"],
        ],
    )
    contrato = cargar_contrato(str(ruta), "2511")
    receta = contrato.recetas["CONSULTA:1"]
    assert receta.bloqueada
    assert "APTO_COMPOSICION=0" in receta.motivos_bloqueo
    assert ("111-1", "A______220") not in contrato.origen_index


def test_efe_reparto_pc_autorizado_se_aisla(tmp_path):
    ruta = tmp_path / "contrato.xlsx"
    _construir_xlsx(
        ruta,
        filas_estados=[["CONSULTA:EFE", "M:1", "612", "2511", True, "RESUELTO"]],
        filas_composicion=[
            ["612", "612-7", "FERROCARRILES", "M:1", "CONSULTA:EFE", "", "BA VICTORIA", "1162", "REPARTO_PC_AUTORIZADO", "2511", "A______066", "SUP", 1, 10.0, True, "v1"],
        ],
    )
    contrato = cargar_contrato(str(ruta), "2511")
    receta = contrato.recetas["CONSULTA:EFE"]
    assert receta.bloqueada
    assert "EFE_REGLA_ESPECIAL_AISLADA_V1" in receta.motivos_bloqueo


def test_conflicto_de_mapeo_bloquea_ambos_grupos(tmp_path):
    ruta = tmp_path / "contrato.xlsx"
    _construir_xlsx(
        ruta,
        filas_estados=[
            ["CONSULTA:1", "M:1", "111", "2511", True, "RESUELTO"],
            ["CONSULTA:2", "M:2", "111", "2511", True, "RESUELTO"],
        ],
        filas_composicion=[
            ["111", "111-1", "CLIENTE", "M:1", "CONSULTA:1", "B______220", "BA B 220", "1", "VECTOR_UNICO", "2511", "A______220", "SUP", 1, 10.0, True, "v1"],
            ["111", "111-1", "CLIENTE", "M:2", "CONSULTA:2", "C______220", "BA C 220", "2", "VECTOR_UNICO", "2511", "A______220", "SUP", 1, 5.0, True, "v1"],
        ],
    )
    contrato = cargar_contrato(str(ruta), "2511")
    assert contrato.recetas["CONSULTA:1"].bloqueada
    assert contrato.recetas["CONSULTA:2"].bloqueada
    assert ("111-1", "A______220") not in contrato.origen_index


def test_id_infotecnica_no_numerico_genera_advertencia_no_bloqueante(tmp_path):
    ruta = tmp_path / "contrato.xlsx"
    _construir_xlsx(
        ruta,
        filas_estados=[["CONSULTA:1", "M:1", "111", "2511", True, "RESUELTO"]],
        filas_composicion=[
            ["111", "111-1", "CLIENTE", "M:1", "CONSULTA:1", "B______220", "BA B 220", "S/I", "VECTOR_UNICO", "2511", "A______220", "SUP", 1, 10.0, True, "v1"],
        ],
    )
    contrato = cargar_contrato(str(ruta), "2511")
    receta = contrato.recetas["CONSULTA:1"]
    assert not receta.bloqueada
    assert any(a["tipo"] == "M_SIN_ID_INFOTECNICA_NUMERICO" for a in contrato.advertencias)
