"""Punto de entrada de línea de comandos del armonizador mensual.

Uso:
    python -m armonizador.cli --ens insumos/07_ENS_..._ORIGINAL.xlsx \\
        --contrato insumos/Resultado_Sistema_Experto_LT_Final_M_Fijo.xlsx \\
        --mes 2511 --out-dir salida/2511
"""
from __future__ import annotations

import argparse
import sys

from . import columnas as col
from .contrato import cargar_contrato
from .io_excel import leer_ens
from .motor import armonizar
from .qa import evaluar
from .reporting import escribir_salidas


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Armonizador mensual de energía LT")
    parser.add_argument("--ens", required=True, help="Ruta del ENS ORIGINAL del mes a armonizar")
    parser.add_argument(
        "--contrato",
        required=True,
        help="Ruta del resultado del Sistema Experto (Resultado_Sistema_Experto_LT_*.xlsx)",
    )
    parser.add_argument("--mes", required=True, help="Mes a armonizar en formato del ENS, p.ej. 2511")
    parser.add_argument("--out-dir", required=True, help="Directorio de salida")
    return parser


def ejecutar(ruta_ens: str, ruta_contrato: str, mes: str, directorio_salida: str) -> int:
    tabla_ens = leer_ens(ruta_ens, col.HOJA_ENS_DATA)
    contrato = cargar_contrato(ruta_contrato, mes)
    resultado = armonizar(tabla_ens.encabezados, tabla_ens.filas, contrato)
    qa_global = evaluar(tabla_ens.filas, resultado)

    rutas = escribir_salidas(
        directorio_salida,
        mes,
        ruta_ens,
        ruta_contrato,
        resultado,
        qa_global,
        parametros={"mes": mes, "ens_original": ruta_ens, "contrato": ruta_contrato},
    )

    print(f"Grupos procesados: {resultado.grupos_procesados}")
    print(f"Grupos omitidos:   {resultado.grupos_omitidos}")
    print(f"Filas entrada -> salida: {qa_global.filas_entrada} -> {qa_global.filas_salida}")
    print(f"MWh entrada -> salida:   {qa_global.mwh_entrada_total:.6f} -> {qa_global.mwh_salida_total:.6f}")
    print(f"Conserva total: {qa_global.conserva_total}")
    print(f"Contiene BARRA CONTROL: {qa_global.contiene_barra_control}")
    for nombre, ruta in rutas.items():
        print(f"  {nombre}: {ruta}")

    if qa_global.contiene_barra_control or not qa_global.conserva_total:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    return ejecutar(args.ens, args.contrato, args.mes, args.out_dir)


if __name__ == "__main__":
    sys.exit(main())
