"""Escritura de las salidas del armonizador: ENS, traza, QA y manifiesto."""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from . import __version__
from .io_excel import escribir_ens
from .motor import ResultadoArmonizacion
from .qa import ReporteQAGlobal


def _sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def escribir_traza_csv(ruta: str, resultado: ResultadoArmonizacion) -> None:
    import csv

    campos = [f.name for f in dataclasses.fields(resultado.traza[0])] if resultado.traza else [
        "id_grupo_consulta",
        "mes",
        "id_m_persistente",
        "version_receta",
        "barraf_origen",
        "factor_origen_m",
        "fila_origen_posicion",
        "rz_soc_suministrador",
        "rut_suministrador",
        "mwh_origen",
        "mwh_destino_agregado",
        "fila_destino_posicion",
    ]
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(campos)
        for entrada in resultado.traza:
            writer.writerow([getattr(entrada, campo) for campo in campos])


def _reporte_qa_dict(resultado: ResultadoArmonizacion, qa_global: ReporteQAGlobal) -> dict[str, Any]:
    return {
        "global": dataclasses.asdict(qa_global),
        "por_grupo": [dataclasses.asdict(g) for g in resultado.qa_grupos],
    }


def escribir_salidas(
    directorio_salida: str,
    mes: str,
    ruta_ens_original: str,
    ruta_contrato: str,
    resultado: ResultadoArmonizacion,
    qa_global: ReporteQAGlobal,
    parametros: dict[str, Any] | None = None,
) -> dict[str, str]:
    os.makedirs(directorio_salida, exist_ok=True)

    ruta_ens_salida = os.path.join(directorio_salida, f"ENS_ARMONIZADO_{mes}.xlsx")
    ruta_traza = os.path.join(directorio_salida, f"TRAZA_{mes}.csv")
    ruta_qa = os.path.join(directorio_salida, f"QA_{mes}.json")
    ruta_warnings = os.path.join(directorio_salida, f"WARNINGS_{mes}.json")
    ruta_manifiesto = os.path.join(directorio_salida, f"MANIFIESTO_{mes}.json")

    escribir_ens(ruta_ens_salida, resultado.encabezados, resultado.filas)
    escribir_traza_csv(ruta_traza, resultado)

    with open(ruta_qa, "w", encoding="utf-8") as fh:
        json.dump(_reporte_qa_dict(resultado, qa_global), fh, ensure_ascii=False, indent=2)

    with open(ruta_warnings, "w", encoding="utf-8") as fh:
        json.dump(resultado.advertencias, fh, ensure_ascii=False, indent=2)

    manifiesto = {
        "version_armonizador": __version__,
        "mes": mes,
        "generado_en_utc": datetime.now(timezone.utc).isoformat(),
        "parametros": parametros or {},
        "entradas": {
            "ens_original": {"ruta": ruta_ens_original, "sha256": _sha256(ruta_ens_original)},
            "resultado_sistema_experto": {"ruta": ruta_contrato, "sha256": _sha256(ruta_contrato)},
        },
        "salidas": {
            "ens_armonizado": {"ruta": ruta_ens_salida, "sha256": None},
            "traza": {"ruta": ruta_traza, "sha256": None},
            "qa": {"ruta": ruta_qa, "sha256": None},
            "warnings": {"ruta": ruta_warnings, "sha256": None},
        },
        "resumen": {
            "grupos_procesados": resultado.grupos_procesados,
            "grupos_omitidos": resultado.grupos_omitidos,
            "filas_entrada": qa_global.filas_entrada,
            "filas_salida": qa_global.filas_salida,
            "mwh_entrada_total": qa_global.mwh_entrada_total,
            "mwh_salida_total": qa_global.mwh_salida_total,
            "conserva_total": qa_global.conserva_total,
        },
    }
    # Hashea las salidas ya escritas (excepto el propio manifiesto).
    manifiesto["salidas"]["ens_armonizado"]["sha256"] = _sha256(ruta_ens_salida)
    manifiesto["salidas"]["traza"]["sha256"] = _sha256(ruta_traza)
    manifiesto["salidas"]["qa"]["sha256"] = _sha256(ruta_qa)
    manifiesto["salidas"]["warnings"]["sha256"] = _sha256(ruta_warnings)

    with open(ruta_manifiesto, "w", encoding="utf-8") as fh:
        json.dump(manifiesto, fh, ensure_ascii=False, indent=2)

    return {
        "ens_armonizado": ruta_ens_salida,
        "traza": ruta_traza,
        "qa": ruta_qa,
        "warnings": ruta_warnings,
        "manifiesto": ruta_manifiesto,
    }
