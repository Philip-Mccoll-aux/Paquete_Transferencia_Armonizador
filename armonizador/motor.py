"""Motor de transformación: aplica las recetas del contrato sobre el ENS.

Regla de posicionamiento de la fila fusionada: cuando varias filas origen
(de distintas BarraF) se funden en una sola fila bajo M, la fila resultante
ocupa la posición de la fila origen cuya BarraF ya coincidía con la BarraF
de M (si existe); en caso contrario, ocupa la posición de la primera fila
origen encontrada en el archivo. El resto de filas origen fusionadas se
elimina de la salida. Esta regla es determinista y reproduce el
comportamiento observado en el golden case Pelambres 2511.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import columnas as col
from .contrato import ContratoLT, RecetaGrupoMes

TOLERANCIA_MWH = 1e-6


@dataclass
class FilaTraza:
    id_grupo_consulta: str
    mes: str
    id_m_persistente: str
    version_receta: str
    barraf_origen: str
    factor_origen_m: float
    fila_origen_posicion: int
    rz_soc_suministrador: str
    rut_suministrador: str
    mwh_origen: float
    mwh_destino_agregado: float
    fila_destino_posicion: int


@dataclass
class QAGrupo:
    id_grupo_consulta: str
    mes: str
    total_origen_mwh: float
    total_destino_mwh: float
    conserva: bool
    por_suministrador: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ResultadoArmonizacion:
    encabezados: list[str]
    filas: list[dict[str, Any]]
    traza: list[FilaTraza]
    advertencias: list[dict[str, Any]]
    qa_grupos: list[QAGrupo]
    grupos_procesados: int
    grupos_omitidos: int


def _valor(fila: dict[str, Any], nombre: str) -> Any:
    return fila.get(nombre)


def _id_barra_infotecnica_salida(valor: Any) -> Any:
    """Normaliza el ID de barra Infotécnica al mismo tipo que usa el ENS.

    El contrato del Sistema Experto guarda el ID siempre como texto (p.ej.
    '519', 'S/I'). El ENS lo guarda como número cuando es numérico. Se
    coerciona a int para que la fila armonizada sea comparable byte a byte
    con una fila que nunca pasó por el contrato (caso de auto-mapeo BarraF
    -> misma BarraF), y se conserva como texto cuando no es numérico.
    """
    if valor is None:
        return None
    try:
        return int(str(valor))
    except (TypeError, ValueError):
        return valor


def _clave_agregacion(fila: dict[str, Any], receta: RecetaGrupoMes) -> tuple:
    clave = []
    for campo in col.ENS_CLAVE_AGREGACION:
        if campo == col.ENS_BARRA_INFOTECNICA:
            clave.append(receta.barra_infotecnica_m)
        elif campo == col.ENS_BARRA_F:
            clave.append(receta.barraf_m)
        elif campo == col.ENS_ID_BARRA_INFOTECNICA:
            clave.append(receta.id_barra_infotecnica_m)
        else:
            clave.append(_valor(fila, campo))
    return tuple(clave)


def armonizar(encabezados: list[str], filas_ens: list[dict[str, Any]], contrato: ContratoLT) -> ResultadoArmonizacion:
    encabezados = list(encabezados)
    advertencias: list[dict[str, Any]] = list(contrato.advertencias)

    indice_por_origen: dict[tuple[str, str], list[int]] = {}
    for posicion, fila in enumerate(filas_ens):
        rut = fila.get(col.ENS_RUT_CLIENTE)
        barraf = fila.get(col.ENS_BARRA_F)
        indice_por_origen.setdefault((rut, barraf), []).append(posicion)

    reemplazos: dict[int, dict[str, Any]] = {}
    consumidas: set[int] = set()
    traza: list[FilaTraza] = []
    qa_grupos: list[QAGrupo] = []
    grupos_procesados = 0
    grupos_omitidos = 0

    for receta in contrato.recetas_aptas():
        if not receta.origenes:
            advertencias.append(
                {"tipo": "RECETA_SIN_ORIGENES", "id_grupo_consulta": receta.id_grupo_consulta, "mes": receta.mes}
            )
            grupos_omitidos += 1
            continue

        posiciones_por_origen: dict[str, list[int]] = {}
        origen_ausente = False
        for barraf in receta.origenes:
            posiciones = indice_por_origen.get((receta.rut_integracion, barraf), [])
            if not posiciones:
                advertencias.append(
                    {
                        "tipo": "BARRAF_ORIGEN_AUSENTE_EN_ENS",
                        "id_grupo_consulta": receta.id_grupo_consulta,
                        "mes": receta.mes,
                        "rut_integracion": receta.rut_integracion,
                        "barraf_origen": barraf,
                    }
                )
                origen_ausente = True
            else:
                posiciones_por_origen[barraf] = posiciones

        if origen_ausente:
            # Gate: no se demuestra una transformación completa del grupo.
            grupos_omitidos += 1
            continue

        # Agrupa las posiciones origen por la clave de agregación de salida.
        grupos_salida: dict[tuple, list[int]] = {}
        for barraf, posiciones in posiciones_por_origen.items():
            for posicion in posiciones:
                fila = filas_ens[posicion]
                clave = _clave_agregacion(fila, receta)
                grupos_salida.setdefault(clave, []).append(posicion)

        total_origen_grupo = 0.0
        total_destino_grupo = 0.0
        por_suministrador: dict[tuple[str, str], dict[str, float]] = {}

        for clave, posiciones in grupos_salida.items():
            ancla = None
            for posicion in posiciones:
                if filas_ens[posicion].get(col.ENS_BARRA_F) == receta.barraf_m:
                    ancla = posicion
                    break
            if ancla is None:
                ancla = min(posiciones)

            suma_mwh = 0.0
            entradas_traza = []
            for posicion in posiciones:
                fila = filas_ens[posicion]
                barraf_origen = fila.get(col.ENS_BARRA_F)
                factor = receta.factor_por_origen.get(barraf_origen, 1.0)
                mwh_origen = float(fila.get(col.ENS_MWH) or 0.0)
                contribucion = mwh_origen * factor
                suma_mwh += contribucion
                total_origen_grupo += mwh_origen

                sup_key = (fila.get(col.ENS_RZ_SOC_SUMINISTRADOR), fila.get(col.ENS_RUT_SUMINISTRADOR))
                acumulado = por_suministrador.setdefault(sup_key, {"origen": 0.0, "destino": 0.0})
                acumulado["origen"] += mwh_origen

                entradas_traza.append((posicion, fila, barraf_origen, factor, mwh_origen))

            fila_ancla = filas_ens[ancla]
            fila_destino = dict(fila_ancla)
            fila_destino[col.ENS_BARRA_INFOTECNICA] = receta.barra_infotecnica_m
            fila_destino[col.ENS_BARRA_F] = receta.barraf_m
            fila_destino[col.ENS_ID_BARRA_INFOTECNICA] = _id_barra_infotecnica_salida(receta.id_barra_infotecnica_m)
            fila_destino[col.ENS_MWH] = suma_mwh
            reemplazos[ancla] = fila_destino
            total_destino_grupo += suma_mwh

            for posicion, fila, barraf_origen, factor, mwh_origen in entradas_traza:
                if posicion != ancla:
                    consumidas.add(posicion)
                traza.append(
                    FilaTraza(
                        id_grupo_consulta=receta.id_grupo_consulta,
                        mes=receta.mes,
                        id_m_persistente=receta.id_m_persistente,
                        version_receta=receta.version_receta,
                        barraf_origen=barraf_origen,
                        factor_origen_m=factor,
                        fila_origen_posicion=posicion,
                        rz_soc_suministrador=fila.get(col.ENS_RZ_SOC_SUMINISTRADOR),
                        rut_suministrador=fila.get(col.ENS_RUT_SUMINISTRADOR),
                        mwh_origen=mwh_origen,
                        mwh_destino_agregado=suma_mwh,
                        fila_destino_posicion=ancla,
                    )
                )
                sup_key = (fila.get(col.ENS_RZ_SOC_SUMINISTRADOR), fila.get(col.ENS_RUT_SUMINISTRADOR))
                por_suministrador[sup_key]["destino"] += mwh_origen * factor

        grupos_procesados += 1
        conserva_grupo = abs(total_origen_grupo - total_destino_grupo) <= TOLERANCIA_MWH
        qa_grupos.append(
            QAGrupo(
                id_grupo_consulta=receta.id_grupo_consulta,
                mes=receta.mes,
                total_origen_mwh=total_origen_grupo,
                total_destino_mwh=total_destino_grupo,
                conserva=conserva_grupo,
                por_suministrador=[
                    {
                        "rz_soc_suministrador": k[0],
                        "rut_suministrador": k[1],
                        "origen_mwh": v["origen"],
                        "destino_mwh": v["destino"],
                        "conserva": abs(v["origen"] - v["destino"]) <= TOLERANCIA_MWH,
                    }
                    for k, v in por_suministrador.items()
                ],
            )
        )
        if not conserva_grupo:
            advertencias.append(
                {
                    "tipo": "NO_CONSERVACION_MWH_GRUPO",
                    "id_grupo_consulta": receta.id_grupo_consulta,
                    "mes": receta.mes,
                    "total_origen_mwh": total_origen_grupo,
                    "total_destino_mwh": total_destino_grupo,
                }
            )

    filas_salida: list[dict[str, Any]] = []
    for posicion, fila in enumerate(filas_ens):
        if posicion in consumidas:
            continue
        if posicion in reemplazos:
            filas_salida.append(reemplazos[posicion])
        else:
            filas_salida.append(dict(fila))

    return ResultadoArmonizacion(
        encabezados=encabezados,
        filas=filas_salida,
        traza=traza,
        advertencias=advertencias,
        qa_grupos=qa_grupos,
        grupos_procesados=grupos_procesados,
        grupos_omitidos=grupos_omitidos,
    )
