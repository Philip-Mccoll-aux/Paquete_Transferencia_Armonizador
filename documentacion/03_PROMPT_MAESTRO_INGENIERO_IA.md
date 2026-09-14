# Prompt maestro para implementar el Armonizador LT

Actúa como ingeniero de software responsable de implementar un proceso mensual auditable de armonización de energía LT.

## Materiales obligatorios

Lee primero:
- `00_LEER_PRIMERO.md`
- `documentacion/01_VALIDACION_RESULTADO_EXPERTO.md`
- `documentacion/02_ESPECIFICACION_FUNCIONAL_ARMONIZADOR_LT.md`
- `documentacion/04_TESTS_ACEPTACION.md`

Usa como inputs de referencia:
- `insumos/Resultado_Sistema_Experto_LT_Final_M_Fijo.xlsx`
- `insumos/07_ENS_Mercado_Libre_2511_ORIGINAL.xlsx`

Golden case:
- `golden_case/07_ENS_Mercado_Libre_2511_ESPERADO_PELAMBRES.xlsx`
- `golden_case/Revision_Pelambres_2511_M.xlsx`
- `golden_case/Maqueta_Pelambres_2511.html`

## Objetivo

Construir una herramienta que, dado:
1. un ENS mensual original; y
2. una versión del resultado del Sistema Experto,

genere un nuevo ENS armonizado bajo medidores persistentes M, conservando energía y suministradores, más trazabilidad y QA.

## Regla arquitectónica principal

NO vuelvas a inferir familias, medidores ni topología.

El Sistema Experto ya entrega la receta:
`ID_GRUPO_CONSULTA + MES → BarraF origen[] → M persistente`.

El armonizador ejecuta esa receta.

La `BARRA CONTROL` NO se escribe en el ENS.
La relación `PC → M` pertenece al mantenedor interno de la Plataforma y se exporta/revisa por separado desde `LT_PC_M`/`BASE_LT_PLATAFORMA`.

## Tablas contractuales

Consume como contrato:
- `LT_M_PERSISTENTES`
- `LT_PC_M`
- `LT_COMPOSICION_M`
- `LT_ESTADOS_M_MES`

Usa como QA:
- `LT_SUMINISTROS_M`
- `LT_QA_M`
- `POTENCIAS`
- `LT_GRUPOS_ENERGIA`

NO interpretes `ID BARRA MEDIDOR` de las hojas principales como M persistente: ese campo puede listar varias BarraF que participaron en la última ventana de potencia.

## Transformación

Por cada receta apta del mes:

1. Selecciona registros del ENS original por cliente/RUT, BarraF de origen y discriminantes aplicables.
2. Preserva:
   - mes,
   - RUT/razón social según la política de identidad,
   - suministrador y RUT suministrador,
   - Tipo,
   - Distribuidora_Conec,
   - IdPuntoSuministro cuando corresponda,
   - MWh antes de la agregación.
3. Sustituye identidad de medición por:
   - `BARRAF_M`
   - `BarraInfotecnica_M`
   - `ID_BARRA_INFOTECNICA_M`
4. Aplica `FACTOR_ORIGEN_M` sólo cuando esté explícito.
5. Agrupa filas equivalentes resultantes y suma MWh.
6. Nunca multipliques por cantidad de PC.
7. Conserva filas fuera de alcance sin modificarlas.
8. No armonices una salida ya armonizada.

## Gate

No transformes un grupo/mes si:
- `APTO_COMPOSICION != 1`;
- M está sin resolver;
- falta una BarraF requerida;
- existe conflicto de identidad o doble asignación;
- falta un factor obligatorio.

La salida debe indicar el motivo de cada omisión.

`APTO_CARGA_OFICIAL=0` no debe ser cambiado por el programa.
Es un estado de integración/mantenedor, no una autorización que el armonizador pueda autoasignarse.

## Pelambres 2511 — test obligatorio

Grupo:
`96790240_FAM_001`

M:
- BarraF `QUILLOTA______220`
- BarraInfotecnica `BA S/E QUILLOTA 220KV BP1-1`
- ID `519`

PC:
- Los Piuquenes
- Mauro

Fuentes 2511:
- `CENTELLA______220`
- `QUILLOTA______220`

El ENS original contiene 10 filas de esas fuentes, cinco suministradores por cada BarraF.

La salida esperada contiene 5 filas bajo M:
- AES Andes: 28.740,712675 MWh
- Alto Maipo: 65.934,576255 MWh
- Parque Eólico El Arrayán: 4.585,622173 MWh
- Conejo Solar: 16.096,239654 MWh
- Javiera: 12.703,286223 MWh

Total: 128.060,436980 MWh.

Los Vilos no se modifica.
Quereo de distribución no se incorpora al grupo.
No se agrega BARRA CONTROL.
No se generan dos copias por Piuquenes/Mauro.

La salida debe coincidir con el golden XLSX para las filas objeto del test.

## QA obligatorio

- conservación MWh por grupo;
- conservación por suministrador;
- cero filas fuente perdidas sin explicación;
- cero filas procesadas dos veces;
- cero destinos improvisados;
- identidad M corresponde a la misma versión del contrato;
- salida idempotente desde originales;
- warning claro para retiros sin PC;
- warning para M sin ID Infotécnica numérico cuando ese dato sea requerido;
- Aguas Pacífico y Socompa permanecen sin asociación;
- EFE no se trata con la regla genérica de vector compartido.

## Ingeniería

- Trabaja con Git.
- No sobrescribas originales.
- Separa motor, validaciones, IO y reporting.
- Añade pruebas unitarias y golden tests.
- Mantén logs sin información sensible.
- No uses fuzzy/IA para decidir destinos.
- No dependas de comentarios de celdas.
- Usa las tablas estructuradas.

## Entregables

1. Código.
2. Tests.
3. Configuración.
4. ENS armonizado de prueba 2511.
5. Traza 2511.
6. Reporte QA.
7. README de operación mensual.
8. Comparación contra golden case.
9. Lista de brechas que requieren definición de negocio.

Antes de ampliar a todos los meses, consigue PASS exacto del golden case Pelambres 2511.
