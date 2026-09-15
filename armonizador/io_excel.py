"""Lectura y escritura de archivos xlsx.

Se apoya únicamente en openpyxl (sin pandas) y no depende de comentarios de
celda: todo el contrato se lee de columnas de datos, tal como exige la
especificación funcional.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import openpyxl
import xlsxwriter


def _limpiar_encabezado(valor: Any) -> str:
    if valor is None:
        return ""
    texto = str(valor)
    # Algunas hojas exportadas traen BOM en la primera celda del encabezado.
    return texto.replace("﻿", "").strip()


@dataclass
class TablaHoja:
    """Filas de una hoja como diccionarios, en el orden original del archivo."""

    encabezados: list[str]
    filas: list[dict[str, Any]]


def leer_hoja(ruta: str, nombre_hoja: str) -> TablaHoja:
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    try:
        if nombre_hoja not in wb.sheetnames:
            raise ValueError(f"La hoja '{nombre_hoja}' no existe en {ruta}")
        ws = wb[nombre_hoja]
        filas_iter = ws.iter_rows(values_only=True)
        encabezados_crudos = next(filas_iter)
        encabezados = [_limpiar_encabezado(h) for h in encabezados_crudos]
        filas = []
        for fila in filas_iter:
            if all(v is None for v in fila):
                continue
            filas.append({encabezados[i]: fila[i] for i in range(len(encabezados)) if encabezados[i]})
        return TablaHoja(encabezados=encabezados, filas=filas)
    finally:
        wb.close()


def leer_ens(ruta: str, nombre_hoja: str = "DATA") -> TablaHoja:
    return leer_hoja(ruta, nombre_hoja)


def escribir_ens(ruta: str, encabezados: Iterable[str], filas: Iterable[dict[str, Any]]) -> None:
    """Escribe la hoja DATA del ENS armonizado.

    Se usa xlsxwriter (no openpyxl) porque produce las celdas de texto como
    cadenas compartidas clásicas (`xl/sharedStrings.xml` + `t="s"`), el
    formato que consumen tanto Excel/las plataformas de carga como el
    script de verificación del golden case. openpyxl >= 3.1 escribe texto
    como `inlineStr`, válido en el estándar OOXML pero no soportado por
    lectores que sólo entienden `t="s"`.
    """
    encabezados = list(encabezados)
    wb = xlsxwriter.Workbook(ruta)
    ws = wb.add_worksheet("DATA")
    for c, encabezado in enumerate(encabezados):
        ws.write(0, c, encabezado)
    for r, fila in enumerate(filas, start=1):
        for c, columna in enumerate(encabezados):
            valor = fila.get(columna)
            if valor is None:
                continue
            ws.write(r, c, valor)
    wb.close()
