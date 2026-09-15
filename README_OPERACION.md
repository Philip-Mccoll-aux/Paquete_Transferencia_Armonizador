# Armonizador LT — operación mensual

Herramienta que aplica, sobre un ENS mensual original, la receta ya
producida por el Sistema Experto (`Resultado_Sistema_Experto_LT_*.xlsx`) y
publica la energía bajo el medidor persistente M correspondiente. No decide
topología, familias ni medidores: sólo ejecuta la receta y produce
trazabilidad y QA. Ver `documentacion/` para la especificación completa.

## 1. Instalación

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt   # incluye pytest para poder testear
```

## 2. Ejecución mensual

```bash
python3 -m armonizador.cli \
  --ens insumos/07_ENS_Mercado_Libre_<MES>_ORIGINAL.xlsx \
  --contrato insumos/Resultado_Sistema_Experto_LT_Final_M_Fijo.xlsx \
  --mes <MES> \
  --out-dir salida/<MES>
```

`<MES>` es la clave tal como aparece en la columna `Clave Año_Mes` del ENS
(p. ej. `2511`). El comando nunca sobrescribe el ENS original: siempre
genera un archivo nuevo en `--out-dir`.

Salidas generadas en `salida/<MES>/`:

| Archivo | Contenido |
|---|---|
| `ENS_ARMONIZADO_<MES>.xlsx` | ENS con la energía de cada grupo/mes apto publicada bajo M. |
| `GRUPOS_<MES>.csv` | **Todos** los grupos de consulta del mes, uno por fila: cliente, M, `estado` (`APTO_ARMONIZADO` / `OMITIDO_BARRAF_AUSENTE_EN_ENS` / `BLOQUEADO`), motivo de bloqueo si aplica, y MWh armonizado. Es la respuesta directa a "qué grupos fueron aptos para armonización". |
| `TRAZA_<MES>.csv` | Traza fila origen → fila destino: grupo, M, BarraF origen, factor, MWh antes/después, posición destino. |
| `QA_<MES>.json` | Conservación global y por grupo/suministrador (sólo grupos armonizados). |
| `WARNINGS_<MES>.json` | Motivos de cada grupo/mes bloqueado u observado (ver §4). |
| `MANIFIESTO_<MES>.json` | Hashes SHA-256 de entradas y salidas, versión del armonizador, parámetros, fecha. |

Para ver rápido los grupos aptos de un mes ya corrido:

```bash
# Windows / PowerShell:
Import-Csv salida\<MES>\GRUPOS_<MES>.csv | Where-Object estado -eq APTO_ARMONIZADO | Format-Table cliente, barraf_m, mwh_armonizado

# Linux/macOS:
awk -F, '$8=="APTO_ARMONIZADO"' salida/<MES>/GRUPOS_<MES>.csv | cut -d, -f2,4,10
```

El proceso retorna código de salida `1` si detecta `BARRA CONTROL` en la
salida o si la conservación global de MWh no cuadra; en cualquier otro caso
retorna `0`, incluso si hubo grupos omitidos (eso es un warning, no un
error fatal — ver §4).

## 3. Qué hace el armonizador, en una frase por grupo/mes apto

Selecciona en el ENS las filas del cliente cuya `BarraF` está en la lista de
orígenes de la receta, reemplaza `BarraInfotecnica`/`BarraF`/
`IdBarraInfotecnica` por los de M, agrupa las filas resultantes por
suministrador (y demás campos de salida) y suma `MWh`. La fila fusionada
ocupa la posición de la fila origen cuya `BarraF` ya era igual a la de M (si
existe); si no, la de la primera fila origen encontrada. El resto de filas
fusionadas se elimina del archivo. Las filas fuera de una receta apta
quedan intactas. `BARRA CONTROL` nunca se escribe en el ENS.

## 4. Gate y warnings

Un grupo/mes se **bloquea** (no se toca ninguna fila) cuando:

- no existe en `LT_ESTADOS_M_MES` para el mes pedido;
- `APTO_COMPOSICION != 1`;
- `ESTADO_M != RESUELTO`;
- el modo de consulta es `REPARTO_PC_AUTORIZADO` (regla EFE, aislada
  explícitamente en esta versión — ver `documentacion/05_CASOS_Y_WARNINGS.md`);
- hay más de una identidad de M para el mismo grupo/mes;
- alguna fila de `LT_COMPOSICION_M` del grupo no es apta;
- el `FACTOR_ORIGEN_M` es contradictorio o falta cuando hay contribución;
- una `BarraF` origen es reclamada por más de un grupo (mapeo contradictorio).

Además, en tiempo de ejecución (con el ENS ya cargado), un grupo apto se
**omite** si alguna de sus `BarraF` origen no aparece en el ENS del mes —
nunca se arma una receta parcial.

Todo motivo de bloqueo/omisión queda en `WARNINGS_<MES>.json`, junto con
advertencias informativas no bloqueantes (p. ej. M sin ID Infotécnica
numérico). El listado completo de tipos de warning está en
`armonizador/contrato.py` y `armonizador/motor.py`.

## 5. Golden case obligatorio (Pelambres 2511)

```bash
python3 -m armonizador.cli --ens insumos/07_ENS_Mercado_Libre_2511_ORIGINAL.xlsx \
  --contrato insumos/Resultado_Sistema_Experto_LT_Final_M_Fijo.xlsx \
  --mes 2511 --out-dir salida/2511

python3 scripts/verificar_golden_pelambres_2511.py salida/2511/ENS_ARMONIZADO_2511.xlsx
# -> PASS {...} 128060.43698
```

El mismo caso está cubierto por `tests/test_golden_pelambres.py`, que corre
contra los insumos reales y valida: suma exacta por suministrador y total,
sustitución de identidad de medición, 10 filas origen → 5 filas destino,
Los Vilos y Quereo intactos, ausencia de `BARRA CONTROL`, conservación
global de MWh y reejecución idempotente desde el mismo original.

## 6. Tests

```bash
python3 -m pytest tests/ -v
```

- `test_motor.py` — fusión de orígenes, no duplicación con M compartido,
  bloqueo por `BarraF` ausente, receta bloqueada deja filas intactas.
- `test_contrato.py` — gating (`APTO_COMPOSICION`), aislamiento de EFE,
  conflicto de mapeo, warning no bloqueante de ID no numérico.
- `test_golden_pelambres.py` — Gate 4 completo sobre los insumos reales.

## 7. Reejecución y no-armonizar-lo-ya-armonizado

El armonizador siempre parte del ENS **ORIGINAL**. Ejecutarlo dos veces
desde el mismo original produce exactamente la misma salida (Gate 7,
cubierto por test). Nunca se debe pasar `ENS_ARMONIZADO_*.xlsx` como
`--ens` de una segunda corrida: el motor no detecta ese caso por sí mismo
(no hay una marca de "ya armonizado" en el ENS), así que es responsabilidad
operativa partir siempre del archivo original del mes.

## 8. Límites conocidos de esta primera versión

Ver `GAPS.md` para la lista completa de brechas que requieren definición de
negocio (EFE, retiros sin PC, exigencia real de ID numérico, etc.).
