"""Chequeos de QA transversales al archivo completo.

Los chequeos por grupo/suministrador ya los calcula el motor (QAGrupo). Aquí
se agregan los chequeos globales de archivo completo exigidos por los
tests de aceptación: conservación total, cero filas perdidas sin
explicación, y ausencia de BARRA CONTROL en la salida.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import columnas as col
from .motor import TOLERANCIA_MWH, ResultadoArmonizacion


@dataclass
class ReporteQAGlobal:
    filas_entrada: int
    filas_salida: int
    filas_eliminadas_por_fusion: int
    mwh_entrada_total: float
    mwh_salida_total: float
    conserva_total: bool
    contiene_barra_control: bool
    grupos_procesados: int
    grupos_omitidos: int
    grupos_no_conservan: list[str]


def _suma_mwh(filas: list[dict[str, Any]]) -> float:
    return sum(float(f.get(col.ENS_MWH) or 0.0) for f in filas)


def evaluar(filas_entrada: list[dict[str, Any]], resultado: ResultadoArmonizacion) -> ReporteQAGlobal:
    mwh_entrada_total = _suma_mwh(filas_entrada)
    mwh_salida_total = _suma_mwh(resultado.filas)

    contiene_barra_control = any(
        "BARRA CONTROL" in str(f.get(col.ENS_BARRA_INFOTECNICA) or "").upper()
        or "BARRA CONTROL" in str(f.get(col.ENS_BARRA_F) or "").upper()
        for f in resultado.filas
    )

    grupos_no_conservan = [g.id_grupo_consulta for g in resultado.qa_grupos if not g.conserva]

    return ReporteQAGlobal(
        filas_entrada=len(filas_entrada),
        filas_salida=len(resultado.filas),
        filas_eliminadas_por_fusion=len(filas_entrada) - len(resultado.filas),
        mwh_entrada_total=mwh_entrada_total,
        mwh_salida_total=mwh_salida_total,
        conserva_total=abs(mwh_entrada_total - mwh_salida_total) <= TOLERANCIA_MWH,
        contiene_barra_control=contiene_barra_control,
        grupos_procesados=resultado.grupos_procesados,
        grupos_omitidos=resultado.grupos_omitidos,
        grupos_no_conservan=grupos_no_conservan,
    )
