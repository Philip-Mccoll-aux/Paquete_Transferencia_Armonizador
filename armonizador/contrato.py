"""Carga y validación del contrato del Sistema Experto para un mes dado.

Este módulo NO decide topología ni medidores: sólo lee las tablas LT_* ya
producidas por el Sistema Experto (LT_ESTADOS_M_MES, LT_COMPOSICION_M) y
arma, por grupo de consulta, la receta `BarraF origen[] -> M persistente`
que el motor de armonización debe ejecutar.

Aísla explícitamente la regla EFE (REPARTO_PC_AUTORIZADO) como módulo no
automatizado en esta primera versión, y bloquea cualquier grupo/mes que no
cumpla el gate documentado en la especificación funcional (sección 9).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from . import columnas as col
from .io_excel import leer_hoja


@dataclass
class RecetaGrupoMes:
    """Receta de armonización para un (grupo de consulta, mes)."""

    id_grupo_consulta: str
    mes: str
    id_m_persistente: str
    id_cliente: str
    rut_integracion: str
    barraf_m: str
    barra_infotecnica_m: str
    id_barra_infotecnica_m: Any
    modo_consulta: str
    version_receta: str = ""
    origenes: set[str] = field(default_factory=set)
    factor_por_origen: dict[str, float] = field(default_factory=dict)
    bloqueada: bool = False
    motivos_bloqueo: list[str] = field(default_factory=list)

    @property
    def id_barra_infotecnica_es_numerico(self) -> bool:
        try:
            int(str(self.id_barra_infotecnica_m))
            return True
        except (TypeError, ValueError):
            return False

    def bloquear(self, motivo: str) -> None:
        self.bloqueada = True
        if motivo not in self.motivos_bloqueo:
            self.motivos_bloqueo.append(motivo)


@dataclass
class ContratoLT:
    """Contrato del Sistema Experto acotado a un mes de energía."""

    mes: str
    recetas: dict[str, RecetaGrupoMes]
    origen_index: dict[tuple[str, str], str]
    advertencias: list[dict[str, Any]]

    def receta_para(self, rut_integracion: str, barraf: str) -> Optional[RecetaGrupoMes]:
        id_grupo = self.origen_index.get((rut_integracion, barraf))
        if id_grupo is None:
            return None
        receta = self.recetas[id_grupo]
        return None if receta.bloqueada else receta

    def recetas_aptas(self) -> list[RecetaGrupoMes]:
        return [r for r in self.recetas.values() if not r.bloqueada]


def _a_texto(valor: Any) -> str:
    return "" if valor is None else str(valor)


def _factor(valor: Any) -> Optional[float]:
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def cargar_contrato(ruta_resultado_experto: str, mes: str) -> ContratoLT:
    estados = leer_hoja(ruta_resultado_experto, col.HOJA_ESTADOS_M_MES)
    composicion = leer_hoja(ruta_resultado_experto, col.HOJA_COMPOSICION_M)

    advertencias: list[dict[str, Any]] = []

    estados_por_grupo = {
        fila[col.C_ID_GRUPO_CONSULTA]: fila
        for fila in estados.filas
        if _a_texto(fila.get(col.C_MES_ENERGIA)) == mes
    }

    filas_por_grupo: dict[str, list[dict[str, Any]]] = {}
    for fila in composicion.filas:
        if _a_texto(fila.get(col.C_MES_ENERGIA)) != mes:
            continue
        id_grupo = fila[col.C_ID_GRUPO_CONSULTA]
        filas_por_grupo.setdefault(id_grupo, []).append(fila)

    recetas: dict[str, RecetaGrupoMes] = {}

    for id_grupo, filas in filas_por_grupo.items():
        primera = filas[0]
        receta = RecetaGrupoMes(
            id_grupo_consulta=id_grupo,
            mes=mes,
            id_m_persistente=primera[col.C_ID_M_PERSISTENTE],
            id_cliente=_a_texto(primera.get(col.C_ID_CLIENTE)),
            rut_integracion=_a_texto(primera.get(col.C_RUT_INTEGRACION)),
            barraf_m=primera.get(col.C_BARRAF_M),
            barra_infotecnica_m=primera.get(col.C_BARRA_INFOTECNICA_M),
            id_barra_infotecnica_m=primera.get(col.C_ID_BARRA_INFOTECNICA_M),
            modo_consulta=_a_texto(primera.get(col.C_MODO_CONSULTA)),
            version_receta=_a_texto(primera.get(col.C_VERSION_RECETA)),
        )
        recetas[id_grupo] = receta

        # Gate 1 (contrato): el mes debe existir en LT_ESTADOS_M_MES y venir
        # con APTO_COMPOSICION=1 y M resuelto. No se admite armonización
        # parcial de un grupo/mes no apto.
        estado = estados_por_grupo.get(id_grupo)
        if estado is None:
            receta.bloquear("MES_NO_EXISTE_EN_LT_ESTADOS_M_MES")
        else:
            if estado.get(col.C_APTO_COMPOSICION) is not True:
                receta.bloquear("APTO_COMPOSICION=0")
            if estado.get(col.C_ESTADO_M) != "RESUELTO":
                receta.bloquear(f"M_NO_RESUELTO:{estado.get(col.C_ESTADO_M)}")

        # EFE es una regla especial ya autorizada (reparto 1/N con
        # homologación propia por PC). No se generaliza al patrón de
        # medidor único/compartido: se aísla como módulo no automatizado.
        if receta.modo_consulta == col.MODO_REPARTO_PC_AUTORIZADO:
            receta.bloquear("EFE_REGLA_ESPECIAL_AISLADA_V1")

        if not receta.rut_integracion or not receta.barraf_m:
            receta.bloquear("IDENTIDAD_M_O_CLIENTE_INCOMPLETA")

        identidades_m = {
            (f.get(col.C_BARRAF_M), f.get(col.C_BARRA_INFOTECNICA_M), f.get(col.C_ID_BARRA_INFOTECNICA_M))
            for f in filas
        }
        if len(identidades_m) > 1:
            receta.bloquear("MULTIPLES_IDENTIDADES_M_CONTRADICTORIAS")

        for fila in filas:
            if fila.get(col.C_APTO_COMPOSICION) is not True:
                receta.bloquear("FILA_DE_COMPOSICION_NO_APTA")
                continue
            barraf_origen = fila.get(col.C_BARRAF_ORIGEN)
            if not barraf_origen:
                continue
            receta.origenes.add(barraf_origen)

            factor = _factor(fila.get(col.C_FACTOR_ORIGEN_M))
            if factor is None:
                contribucion = fila.get(col.C_CONTRIBUCION_MWH)
                if contribucion not in (None, 0):
                    receta.bloquear(f"FACTOR_ORIGEN_M_AUSENTE:{barraf_origen}")
                continue
            previo = receta.factor_por_origen.get(barraf_origen)
            if previo is not None and abs(previo - factor) > 1e-9:
                receta.bloquear(f"FACTOR_ORIGEN_M_CONTRADICTORIO:{barraf_origen}")
            else:
                receta.factor_por_origen[barraf_origen] = factor

        if not receta.id_barra_infotecnica_es_numerico:
            advertencias.append(
                {
                    "tipo": "M_SIN_ID_INFOTECNICA_NUMERICO",
                    "id_grupo_consulta": id_grupo,
                    "id_barra_infotecnica_m": receta.id_barra_infotecnica_m,
                    "detalle": "ID Infotécnica no numérico; el nombre de M puede seguir siendo válido "
                    "según el contrato real del cargador.",
                }
            )

        if receta.bloqueada:
            advertencias.append(
                {
                    "tipo": "GRUPO_MES_BLOQUEADO",
                    "id_grupo_consulta": id_grupo,
                    "mes": mes,
                    "motivos": list(receta.motivos_bloqueo),
                }
            )

    # Índice (rut_integracion, barraf_origen) -> grupo. Si una misma clave
    # es reclamada por más de un grupo, es un mapeo contradictorio: no se
    # puede decidir un único destino, así que se bloquean todos los grupos
    # involucrados y la clave queda fuera del índice activo.
    reclamos: dict[tuple[str, str], set[str]] = {}
    for receta in recetas.values():
        if receta.bloqueada:
            continue
        for barraf in receta.origenes:
            clave = (receta.rut_integracion, barraf)
            reclamos.setdefault(clave, set()).add(receta.id_grupo_consulta)

    for clave, grupos in reclamos.items():
        if len(grupos) > 1:
            for id_grupo in grupos:
                recetas[id_grupo].bloquear(f"CONFLICTO_MAPEO_ORIGEN:{clave[0]}|{clave[1]}")
                advertencias.append(
                    {
                        "tipo": "CONFLICTO_MAPEO_ORIGEN",
                        "id_grupo_consulta": id_grupo,
                        "rut_integracion": clave[0],
                        "barraf_origen": clave[1],
                        "grupos_en_conflicto": sorted(grupos),
                    }
                )

    origen_index: dict[tuple[str, str], str] = {}
    for receta in recetas.values():
        if receta.bloqueada:
            continue
        for barraf in receta.origenes:
            origen_index[(receta.rut_integracion, barraf)] = receta.id_grupo_consulta

    return ContratoLT(mes=mes, recetas=recetas, origen_index=origen_index, advertencias=advertencias)
