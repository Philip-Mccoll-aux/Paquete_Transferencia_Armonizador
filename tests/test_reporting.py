"""Pruebas del listado de grupos aptos/omitidos/bloqueados."""
from __future__ import annotations

import csv

from armonizador import columnas as col
from armonizador.contrato import ContratoLT, RecetaGrupoMes
from armonizador.motor import armonizar
from armonizador.reporting import escribir_listado_grupos


def _fila(barraf, barra_infotecnica, id_barra, suministrador, rut_sum, mwh, rut_cliente):
    return {
        col.ENS_CLAVE_ANIO_MES: 2511,
        col.ENS_BARRA_INFOTECNICA: barra_infotecnica,
        col.ENS_BARRA_F: barraf,
        col.ENS_ID_BARRA_INFOTECNICA: id_barra,
        col.ENS_TIPO: "LIBRE",
        col.ENS_RZ_SOC_CLIENTE: "CLIENTE X",
        col.ENS_RUT_CLIENTE: rut_cliente,
        col.ENS_DISTRIBUIDORA_CONEC: "Cliente AT",
        col.ENS_RZ_SOC_SUMINISTRADOR: suministrador,
        col.ENS_RUT_SUMINISTRADOR: rut_sum,
        col.ENS_MWH: mwh,
        col.ENS_RUT_DISTRIBUIDORA: None,
        col.ENS_ID_PUNTO_SUMINISTRO: "S/I",
    }


def test_listado_incluye_apto_omitido_y_bloqueado(tmp_path):
    receta_apta = RecetaGrupoMes(
        id_grupo_consulta="CONSULTA:apta",
        mes="2511",
        id_m_persistente="M:1",
        id_cliente="11111111",
        rut_integracion="11111111-1",
        barraf_m="B______220",
        barra_infotecnica_m="BA B 220",
        id_barra_infotecnica_m="1",
        modo_consulta="VECTOR_UNICO",
        cliente="CLIENTE UNO",
        origenes={"A______220"},
        factor_por_origen={"A______220": 1.0},
    )
    receta_omitida = RecetaGrupoMes(
        id_grupo_consulta="CONSULTA:omitida",
        mes="2511",
        id_m_persistente="M:2",
        id_cliente="22222222",
        rut_integracion="22222222-2",
        barraf_m="D______220",
        barra_infotecnica_m="BA D 220",
        id_barra_infotecnica_m="2",
        modo_consulta="VECTOR_UNICO",
        cliente="CLIENTE DOS",
        origenes={"C______220"},
        factor_por_origen={"C______220": 1.0},
    )
    receta_bloqueada = RecetaGrupoMes(
        id_grupo_consulta="CONSULTA:bloqueada",
        mes="2511",
        id_m_persistente="M:3",
        id_cliente="33333333",
        rut_integracion="33333333-3",
        barraf_m="F______220",
        barra_infotecnica_m="BA F 220",
        id_barra_infotecnica_m="3",
        modo_consulta="VECTOR_UNICO",
        cliente="CLIENTE TRES",
    )
    receta_bloqueada.bloquear("APTO_COMPOSICION=0")

    contrato = ContratoLT(
        mes="2511",
        recetas={
            receta_apta.id_grupo_consulta: receta_apta,
            receta_omitida.id_grupo_consulta: receta_omitida,
            receta_bloqueada.id_grupo_consulta: receta_bloqueada,
        },
        origen_index={
            ("11111111-1", "A______220"): receta_apta.id_grupo_consulta,
            ("22222222-2", "C______220"): receta_omitida.id_grupo_consulta,
        },
        advertencias=[],
    )

    filas = [_fila("A______220", "BA A 220", "9", "Suministrador Uno", "1-1", 10.0, "11111111-1")]
    encabezados = list(filas[0].keys())
    resultado = armonizar(encabezados, filas, contrato)

    ruta = tmp_path / "GRUPOS_2511.csv"
    escribir_listado_grupos(str(ruta), contrato, resultado)

    with open(ruta, encoding="utf-8") as fh:
        filas_csv = {r["id_grupo_consulta"]: r for r in csv.DictReader(fh)}

    assert filas_csv["CONSULTA:apta"]["estado"] == "APTO_ARMONIZADO"
    assert filas_csv["CONSULTA:apta"]["cliente"] == "CLIENTE UNO"
    assert filas_csv["CONSULTA:apta"]["mwh_armonizado"] == "10.0"

    assert filas_csv["CONSULTA:omitida"]["estado"] == "OMITIDO_BARRAF_AUSENTE_EN_ENS"
    assert filas_csv["CONSULTA:omitida"]["mwh_armonizado"] == ""

    assert filas_csv["CONSULTA:bloqueada"]["estado"] == "BLOQUEADO"
    assert filas_csv["CONSULTA:bloqueada"]["motivos_bloqueo"] == "APTO_COMPOSICION=0"
