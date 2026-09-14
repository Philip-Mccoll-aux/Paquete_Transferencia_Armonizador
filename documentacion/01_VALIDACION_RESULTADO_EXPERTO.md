# Validación del resultado `Resultado_Sistema_Experto_LT_Final_M_Fijo.xlsx`

## Conclusión

El nuevo resultado es **suficiente para iniciar el desarrollo del armonizador en modo piloto**, porque ya separa:
- Punto de Control.
- Grupo de medición/consulta.
- Medidor persistente `M`.
- Fuentes `BarraF` mensuales que aportan a M.
- Suministradores y energía.
- Estados de aptitud de la receta.

No debe considerarse todavía una carga oficial: el propio resultado mantiene `APTO_CARGA_OFICIAL=0` mientras el mantenedor de la Plataforma no haya sido aplicado/validado.

## Comprobaciones

- `BASE_LT`: 296 filas y 15 columnas.
- Las 15 columnas de `BASE_LT` coinciden con las 15 primeras de `01_BASE_LT_PROPUESTA`: **sí**.
- `POTENCIAS`: 296 filas y detalle mensual visible desde 2025.
- El XLSX no contiene partes de comentarios de celda; el detalle está escrito en celdas.
- Grupos de M: 194.
- Modos: {'VECTOR_UNICO': 149, 'REPARTO_PC_AUTORIZADO': 1, 'VECTOR_COMPARTIDO': 44}.
- Fuera de la regla especial EFE, no se encontraron grupos con más de un M persistente.
- `04_RETIROS_SIN_PUNTO`: 21 registros. Su gestión queda fuera de la primera implementación.
- Dos filas conservan explícitamente `SIN MEDIDOR ASOCIADO`: Aguas Pacífico y S/E Socompa de Minera Centinela.
- 19 entradas de catálogo M no tienen ID Infotécnica numérico (incluye el registro de grupo EFE). El nombre de barra puede existir igualmente; el cargador debe tratar el ID faltante según su contrato real.

## Golden case Pelambres 2511

Piuquenes y Mauro:
- `ID_GRUPO_MEDICION = 96790240_FAM_001`
- `ID_VECTOR = GRUPO:28652cb9be6322f4f3a38b50`
- M = `QUILLOTA______220`
- Barra Infotécnica M = `BA S/E QUILLOTA 220KV BP1-1`
- ID = `519`
- modo = `VECTOR_COMPARTIDO`
- dos PC consultan el mismo M.

Para 2511, `LT_COMPOSICION_M` y `LT_SUMINISTROS_M` reconstruyen:
- `CENTELLA______220`
- `QUILLOTA______220`

Total: **128.060,436980 MWh**.

El total coincide exactamente con el balance original y con el golden case esperado. La suma se realiza por suministrador y se materializa una sola vez bajo M.

Estado del grupo/mes:
- `APTO_COMPOSICION=1`
- `ESTADO_M=RESUELTO`
- `ESTADO_ARMONIZACION_M_MES=RECETA_APTA_ENSAYO_MANTENEDOR_PENDIENTE`
- `APTO_CARGA_OFICIAL=0`

Esto es consistente: la receta energética está resuelta para el ensayo, pero la relación PC→M aún debe estar aplicada/validada en el mantenedor antes de una carga oficial.

## Precaución de lectura del Excel

En las hojas principales:
- `BarraInfotecnica` e `ID MEDIDOR INFOTECNICA` representan la homologación adoptada para M.
- `ID BARRA MEDIDOR` representa las BarraF de origen usadas por la última ventana de potencia y puede contener varias.

Por ello, el armonizador **NO debe usar `ID BARRA MEDIDOR` como identificador persistente M**.
Para integración automática debe consumir las tablas dedicadas:
`LT_M_PERSISTENTES`, `LT_PC_M`, `LT_COMPOSICION_M`, `LT_ESTADOS_M_MES` y, para QA de suministros, `LT_SUMINISTROS_M`.

## Advertencias globales

- 122 grupos-mes están con `APTO_COMPOSICION=0`; no se deben armonizar parcialmente.
- Los RUT y razones sociales de salida deben reconciliarse con la Sábana/archivo original según la regla vigente.
- `LT_SUMINISTROS_M` es útil para QA, pero el nombre/RUT de suministrador de la salida debe preservarse desde el archivo ENS original.
- EFE es una excepción explícita: 25 PC, reparto `1/25`, y homologación propia por PC; no debe forzarse al patrón general de un único M físico.
- Aguas Pacífico y Socompa siguen sin medidor asociado; no inventar destinos.
