# Tests de aceptación del Armonizador LT

## Gate 0 — Input
- El archivo de entrada debe ser un ENS ORIGINAL.
- Debe detectarse el mes real.
- El resultado experto debe declarar versión/contrato compatible.

## Gate 1 — Contrato
- El mes existe en `LT_ESTADOS_M_MES`.
- `APTO_COMPOSICION=1`.
- M está resuelto.
- Cada BarraF requerida puede buscarse en el ENS con identidad compatible.

## Gate 2 — Conservación
Por grupo/mes:
- total origen = total destino.
Por suministrador:
- total origen = total destino.
No aceptar redondeos silenciosos.

## Gate 3 — No duplicación
- Varios PC→M no generan varias series.
- Una fila origen no puede consumirse dos veces en dos destinos incompatibles.

## Gate 4 — Golden case Pelambres 2511

Fuentes:
Centella + Quillota.

Esperado bajo M Quillota/519:
- AES Andes 28.740,712675
- Alto Maipo 65.934,576255
- Arrayán 4.585,622173
- Conejo Solar 16.096,239654
- Javiera 12.703,286223
- Total 128.060,436980 MWh.

Además:
- Los Vilos permanece igual.
- Quereo distribución permanece igual.
- no aparece BARRA CONTROL;
- se pasa de 10 filas de origen objeto de armonización a 5 filas de destino;
- total de energía de esas diez filas se conserva exactamente.

## Gate 5 — Warnings

El proceso no debe fallar globalmente por:
- retiro sin PC;
- grupo/mes pendiente;
- M sin ID numérico cuando el contrato permita seguir usando nombre;
- identidad S/I.

Debe aislar esos casos.

Debe BLOQUEAR el grupo/mes cuando no pueda demostrar una transformación completa.

## Gate 6 — Trazabilidad

Cada fila destino debe poder enumerar:
- filas origen;
- regla;
- grupo;
- M;
- versión;
- factor;
- energía antes/después.

## Gate 7 — Reejecución

Ejecutar dos veces desde el mismo original produce la misma salida.
Nunca usar la primera salida armonizada como entrada de la segunda.
