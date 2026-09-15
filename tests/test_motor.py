"""Pruebas unitarias del motor de armonización con datos sintéticos.

Reproduce, a escala reducida, el patrón del golden case Pelambres: dos
BarraF de origen (una de ellas igual a la BarraF de M) que se funden en una
sola fila por suministrador bajo el medidor persistente M.
"""
from __future__ import annotations

from armonizador import columnas as col
from armonizador.contrato import ContratoLT, RecetaGrupoMes
from armonizador.motor import armonizar


def _fila(barraf, barra_infotecnica, id_barra, suministrador, rut_sum, mwh, rut_cliente="11111111-1"):
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


def _receta_dos_origenes():
    return RecetaGrupoMes(
        id_grupo_consulta="CONSULTA:test",
        mes="2511",
        id_m_persistente="M:test",
        id_cliente="11111111",
        rut_integracion="11111111-1",
        barraf_m="ORIGEN_B______220",
        barra_infotecnica_m="BA S/E ORIGEN B 220KV",
        id_barra_infotecnica_m="999",
        modo_consulta="VECTOR_COMPARTIDO",
        version_receta="v1",
        origenes={"ORIGEN_A______220", "ORIGEN_B______220"},
        factor_por_origen={"ORIGEN_A______220": 1.0, "ORIGEN_B______220": 1.0},
    )


def test_fusiona_dos_origenes_en_fila_de_m_y_conserva_energia():
    receta = _receta_dos_origenes()
    filas = [
        _fila("ORIGEN_A______220", "BA S/E ORIGEN A 220KV", "111", "Suministrador Uno", "1-1", 100.0),
        _fila("ORIGEN_A______220", "BA S/E ORIGEN A 220KV", "111", "Suministrador Dos", "2-2", 50.0),
        _fila("OTRO_CLIENTE__220", "BA S/E NO TOCAR", "222", "Otro Suministrador", "3-3", 10.0, rut_cliente="22222222-2"),
        _fila("ORIGEN_B______220", "BA S/E ORIGEN B 220KV", "999", "Suministrador Uno", "1-1", 200.0),
        _fila("ORIGEN_B______220", "BA S/E ORIGEN B 220KV", "999", "Suministrador Dos", "2-2", 80.0),
    ]
    contrato = ContratoLT(
        mes="2511",
        recetas={receta.id_grupo_consulta: receta},
        origen_index={
            ("11111111-1", "ORIGEN_A______220"): receta.id_grupo_consulta,
            ("11111111-1", "ORIGEN_B______220"): receta.id_grupo_consulta,
        },
        advertencias=[],
    )

    resultado = armonizar(list(filas[0].keys()), filas, contrato)

    # 4 filas armonizadas -> 2 (una por suministrador) + 1 fila intacta de otro cliente = 3
    assert len(resultado.filas) == 3
    assert resultado.grupos_procesados == 1
    assert resultado.grupos_omitidos == 0

    filas_m = [f for f in resultado.filas if f[col.ENS_BARRA_F] == "ORIGEN_B______220" and f[col.ENS_RUT_CLIENTE] == "11111111-1"]
    assert len(filas_m) == 2
    total_por_suministrador = {f[col.ENS_RUT_SUMINISTRADOR]: f[col.ENS_MWH] for f in filas_m}
    assert total_por_suministrador["1-1"] == 300.0
    assert total_por_suministrador["2-2"] == 130.0

    # La fila del otro cliente no se toca.
    fila_intacta = [f for f in resultado.filas if f[col.ENS_RUT_CLIENTE] == "22222222-2"][0]
    assert fila_intacta[col.ENS_BARRA_F] == "OTRO_CLIENTE__220"
    assert fila_intacta[col.ENS_MWH] == 10.0

    # Conservación exacta de energía del grupo armonizado.
    qa = resultado.qa_grupos[0]
    assert qa.total_origen_mwh == 430.0
    assert qa.total_destino_mwh == 430.0
    assert qa.conserva

    # La fila fusionada quedó en la posición de la fila cuya BarraF ya era
    # la de M (posición 3, la primera fila de ORIGEN_B), no duplicada.
    assert resultado.filas[1][col.ENS_RUT_SUMINISTRADOR] == "1-1"
    assert resultado.filas[1][col.ENS_MWH] == 300.0


def test_no_duplica_energia_cuando_dos_pc_comparten_m():
    # El origen_index simula dos PC (dos claves de origen distintas)
    # apuntando al mismo grupo/receta; la fusión sigue siendo una sola vez.
    receta = _receta_dos_origenes()
    filas = [
        _fila("ORIGEN_A______220", "BA S/E ORIGEN A 220KV", "111", "Suministrador Uno", "1-1", 40.0),
        _fila("ORIGEN_B______220", "BA S/E ORIGEN B 220KV", "999", "Suministrador Uno", "1-1", 60.0),
    ]
    contrato = ContratoLT(
        mes="2511",
        recetas={receta.id_grupo_consulta: receta},
        origen_index={
            ("11111111-1", "ORIGEN_A______220"): receta.id_grupo_consulta,
            ("11111111-1", "ORIGEN_B______220"): receta.id_grupo_consulta,
        },
        advertencias=[],
    )
    resultado = armonizar(list(filas[0].keys()), filas, contrato)
    assert len(resultado.filas) == 1
    assert resultado.filas[0][col.ENS_MWH] == 100.0


def test_bloquea_grupo_si_falta_barraf_origen_en_ens():
    receta = _receta_dos_origenes()
    filas = [
        _fila("ORIGEN_A______220", "BA S/E ORIGEN A 220KV", "111", "Suministrador Uno", "1-1", 40.0),
        # Falta ORIGEN_B en el ENS.
    ]
    contrato = ContratoLT(
        mes="2511",
        recetas={receta.id_grupo_consulta: receta},
        origen_index={("11111111-1", "ORIGEN_A______220"): receta.id_grupo_consulta},
        advertencias=[],
    )
    resultado = armonizar(list(filas[0].keys()), filas, contrato)
    # No se toca nada: no se demuestra una transformación completa.
    assert resultado.filas == filas
    assert resultado.grupos_omitidos == 1
    assert any(a["tipo"] == "BARRAF_ORIGEN_AUSENTE_EN_ENS" for a in resultado.advertencias)


def test_receta_bloqueada_deja_filas_intactas():
    receta = _receta_dos_origenes()
    receta.bloquear("APTO_COMPOSICION=0")
    filas = [
        _fila("ORIGEN_A______220", "BA S/E ORIGEN A 220KV", "111", "Suministrador Uno", "1-1", 40.0),
        _fila("ORIGEN_B______220", "BA S/E ORIGEN B 220KV", "999", "Suministrador Uno", "1-1", 60.0),
    ]
    contrato = ContratoLT(mes="2511", recetas={receta.id_grupo_consulta: receta}, origen_index={}, advertencias=[])
    resultado = armonizar(list(filas[0].keys()), filas, contrato)
    assert resultado.filas == filas
    assert resultado.grupos_procesados == 0
