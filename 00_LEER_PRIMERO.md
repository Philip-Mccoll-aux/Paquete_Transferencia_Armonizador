# Paquete de transferencia — Armonizador de energía LT

## Orden de lectura

1. `documentacion/01_VALIDACION_RESULTADO_EXPERTO.md`
2. `documentacion/02_ESPECIFICACION_FUNCIONAL_ARMONIZADOR_LT.md`
3. `golden_case/Maqueta_Pelambres_2511.html`
4. `documentacion/03_PROMPT_MAESTRO_INGENIERO_IA.md`
5. `documentacion/04_TESTS_ACEPTACION.md`

## Archivos centrales

- `insumos/Resultado_Sistema_Experto_LT_Final_M_Fijo.xlsx`: contrato mensual producido por el Sistema Experto.
- `insumos/07_ENS_Mercado_Libre_2511_ORIGINAL.xlsx`: archivo original de energía.
- `golden_case/07_ENS_Mercado_Libre_2511_ESPERADO_PELAMBRES.xlsx`: golden case. **NO ES ARCHIVO OFICIAL DE CARGA**.
- `golden_case/Revision_Pelambres_2511_M.xlsx`: explicación antes/después.

## Regla vigente

La energía se armoniza bajo el **medidor persistente M**. La `BARRA CONTROL` no se agrega al archivo ENS.
La relación `PC → M` vive en el mantenedor interno de puntos de control de la Plataforma.

El armonizador no decide familias ni reconstruye grafos. Consume la receta mensual ya producida por el Sistema Experto.
