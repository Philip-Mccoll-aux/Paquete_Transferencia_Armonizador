"""Test de aceptación obligatorio: golden case Pelambres 2511 (Gate 4).

Ejecuta el armonizador sobre los insumos reales del paquete de transferencia
y verifica que el resultado coincide exactamente con lo documentado en
`documentacion/04_TESTS_ACEPTACION.md` y `golden_case/`.
"""
from __future__ import annotations

import os

import pytest

from armonizador import columnas as col
from armonizador.contrato import cargar_contrato
from armonizador.io_excel import leer_ens
from armonizador.motor import armonizar
from armonizador.qa import evaluar

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_ENS = os.path.join(RAIZ, "insumos", "07_ENS_Mercado_Libre_2511_ORIGINAL.xlsx")
RUTA_CONTRATO = os.path.join(RAIZ, "insumos", "Resultado_Sistema_Experto_LT_Final_M_Fijo.xlsx")
MES = "2511"

RUT_PELAMBRES = "96790240-3"
BARRAF_M = "QUILLOTA______220"

ESPERADO = {
    "AES Andes S.A.": 28740.712675,
    "Alto Maipo SpA": 65934.576255,
    "Parque Eólico El Arrayán SpA": 4585.622173,
    "Conejo Solar SpA": 16096.239654,
    "Javiera SpA": 12703.286223,
}
TOTAL_ESPERADO = 128060.436980


@pytest.fixture(scope="module")
def resultado():
    if not (os.path.exists(RUTA_ENS) and os.path.exists(RUTA_CONTRATO)):
        pytest.skip("Insumos reales no disponibles en este entorno")
    tabla_ens = leer_ens(RUTA_ENS, col.HOJA_ENS_DATA)
    contrato = cargar_contrato(RUTA_CONTRATO, MES)
    res = armonizar(tabla_ens.encabezados, tabla_ens.filas, contrato)
    qa_global = evaluar(tabla_ens.filas, res)
    return tabla_ens, res, qa_global


def test_pelambres_suma_por_suministrador(resultado):
    _, res, _ = resultado
    filas_m = [
        f
        for f in res.filas
        if f.get(col.ENS_RUT_CLIENTE) == RUT_PELAMBRES and f.get(col.ENS_BARRA_F) == BARRAF_M
    ]
    assert len(filas_m) == 5

    totales = {f[col.ENS_RZ_SOC_SUMINISTRADOR]: f[col.ENS_MWH] for f in filas_m}
    for suministrador, mwh_esperado in ESPERADO.items():
        assert totales[suministrador] == pytest.approx(mwh_esperado, abs=1e-6)

    assert sum(totales.values()) == pytest.approx(TOTAL_ESPERADO, abs=1e-6)


def test_pelambres_identidad_de_medicion_sustituida(resultado):
    _, res, _ = resultado
    filas_m = [
        f
        for f in res.filas
        if f.get(col.ENS_RUT_CLIENTE) == RUT_PELAMBRES and f.get(col.ENS_BARRA_F) == BARRAF_M
    ]
    for f in filas_m:
        assert f[col.ENS_BARRA_INFOTECNICA] == "BA S/E QUILLOTA 220KV BP1-1"
        assert str(f[col.ENS_ID_BARRA_INFOTECNICA]) == "519"


def test_los_vilos_y_quereo_no_se_modifican(resultado):
    tabla_ens, res, _ = resultado
    orig_por_barraf = {}
    for f in tabla_ens.filas:
        if f.get(col.ENS_RUT_CLIENTE) != RUT_PELAMBRES:
            continue
        if f.get(col.ENS_BARRA_F) in ("L.VILOS_______220", "QUEREO________023"):
            orig_por_barraf.setdefault(f[col.ENS_BARRA_F], []).append(f)

    salida_por_barraf = {}
    for f in res.filas:
        if f.get(col.ENS_RUT_CLIENTE) != RUT_PELAMBRES:
            continue
        if f.get(col.ENS_BARRA_F) in ("L.VILOS_______220", "QUEREO________023"):
            salida_por_barraf.setdefault(f[col.ENS_BARRA_F], []).append(f)

    assert orig_por_barraf == salida_por_barraf


def test_diez_filas_origen_pasan_a_cinco_filas_destino(resultado):
    tabla_ens, res, _ = resultado
    origen_relevante = [
        f
        for f in tabla_ens.filas
        if f.get(col.ENS_RUT_CLIENTE) == RUT_PELAMBRES
        and f.get(col.ENS_BARRA_F) in ("CENTELLA______220", "QUILLOTA______220")
    ]
    assert len(origen_relevante) == 10

    destino_relevante = [
        f for f in res.filas if f.get(col.ENS_RUT_CLIENTE) == RUT_PELAMBRES and f.get(col.ENS_BARRA_F) == BARRAF_M
    ]
    assert len(destino_relevante) == 5

    total_origen = sum(float(f[col.ENS_MWH]) for f in origen_relevante)
    total_destino = sum(float(f[col.ENS_MWH]) for f in destino_relevante)
    assert total_origen == pytest.approx(total_destino, abs=1e-6)
    assert total_origen == pytest.approx(TOTAL_ESPERADO, abs=1e-6)


def test_no_aparece_barra_control(resultado):
    _, _, qa_global = resultado
    assert qa_global.contiene_barra_control is False


def test_conserva_energia_total_del_archivo(resultado):
    _, _, qa_global = resultado
    assert qa_global.conserva_total


def test_reduccion_de_filas_coincide_con_fusiones_trazadas(resultado):
    """El armonizador procesa TODOS los grupos aptos del mes, no sólo
    Pelambres (el golden case sólo documenta el diff de ese grupo). La
    reducción total de filas debe explicarse exactamente por las fusiones
    registradas en la traza, e incluir al menos la de Pelambres (10 -> 5).
    """
    tabla_ens, res, _ = resultado
    from collections import Counter

    reduccion = len(tabla_ens.filas) - len(res.filas)
    contador_por_destino = Counter(t.fila_destino_posicion for t in res.traza)
    reduccion_esperada = sum(n - 1 for n in contador_por_destino.values())
    assert reduccion == reduccion_esperada
    assert reduccion >= 5


def test_reejecucion_es_idempotente_desde_el_mismo_original():
    if not (os.path.exists(RUTA_ENS) and os.path.exists(RUTA_CONTRATO)):
        pytest.skip("Insumos reales no disponibles en este entorno")
    tabla_ens = leer_ens(RUTA_ENS, col.HOJA_ENS_DATA)
    contrato = cargar_contrato(RUTA_CONTRATO, MES)
    r1 = armonizar(tabla_ens.encabezados, tabla_ens.filas, contrato)

    tabla_ens_2 = leer_ens(RUTA_ENS, col.HOJA_ENS_DATA)
    contrato_2 = cargar_contrato(RUTA_CONTRATO, MES)
    r2 = armonizar(tabla_ens_2.encabezados, tabla_ens_2.filas, contrato_2)

    assert r1.filas == r2.filas
