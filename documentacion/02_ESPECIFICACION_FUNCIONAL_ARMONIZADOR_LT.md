# Especificación funcional — Armonizador mensual de energía LT

## 1. Problema

Los archivos ENS mensuales registran energía bajo `BarraF` que puede cambiar a través del tiempo.
La Plataforma no reconstruye esa genealogía. Su mantenedor interno relaciona cada Punto de Control con un medidor persistente `M`.

El armonizador debe transformar los registros mensuales para que toda y sólo la energía que corresponde a un grupo quede publicada bajo M.

## 2. Separación de responsabilidades

### Sistema Experto
Decide y exporta:
- grupos de medición/consulta;
- PC pertenecientes al grupo;
- M persistente;
- composición mensual `MES → BarraF origen[]`;
- estados/QA de la receta.

### Armonizador
NO decide topología, familias ni medidores.
Aplica una versión del contrato del experto sobre un ENS original.

### Plataforma
Usa su mantenedor `PC → M`.
El ENS armonizado contiene M, cliente, suministrador y energía. **No se agrega BARRA CONTROL al ENS.**

## 3. Tablas del Sistema Experto que deben consumirse

### `LT_M_PERSISTENTES`
Catálogo versionado de M.

Claves relevantes:
- `ID_GRUPO_CONSULTA`
- `ID_M_PERSISTENTE`
- `ID_CLIENTE`
- `BARRAF_M`
- `BarraInfotecnica_M`
- `ID_BARRA_INFOTECNICA_M`
- `MODO_CONSULTA`

### `LT_PC_M`
Relación para preparar/revisar el mantenedor PC→M.
No usar para duplicar energía.

### `LT_COMPOSICION_M`
Contrato principal de transformación.
Una o varias filas de origen pueden contribuir al mismo M en un mes.

Usar:
- `RUT_INTEGRACION`
- `ID_GRUPO_CONSULTA`
- `ID_M_PERSISTENTE`
- `MES_ENERGIA`
- `BARRAF_ORIGEN`
- discriminantes disponibles
- `FACTOR_ORIGEN_M`
- `CONTRIBUCION_MWH`
- `ESTADO_REGLA`
- `APTO_COMPOSICION`

### `LT_ESTADOS_M_MES`
Gate de la receta mensual.
Nunca ejecutar una receta con `APTO_COMPOSICION=0`.

### `LT_SUMINISTROS_M`
QA agregado por suministrador. No sustituye las filas originales del ENS.

## 4. Algoritmo mensual

1. Leer ENS ORIGINAL y determinar mes.
2. Leer contrato del Sistema Experto correspondiente a la misma versión.
3. Conservar una copia íntegra del original.
4. Para cada grupo/mes apto:
   - obtener M;
   - obtener las `BarraF` de origen;
   - seleccionar en el ENS sólo registros del mismo cliente/RUT y alcance correcto;
   - preservar `RzSocSuministrador`, `RUTSuministrador`, tipo, condición de conexión y MWh;
   - reemplazar los tres campos de identidad de medición por los de M:
     `BarraInfotecnica`, `BarraF`, `IdBarraInfotecnica`;
   - agregar únicamente filas que, después de la sustitución, representen el mismo M, cliente, suministrador y demás campos de salida compatibles;
   - sumar MWh.
5. No crear una copia por cada PC.
6. Dejar intactas las filas que no están dentro de una receta aprobada.
7. Emitir trazabilidad fila origen → fila destino.
8. Ejecutar QA de conservación.
9. Guardar un nuevo archivo; nunca armonizar sobre una salida ya armonizada.

## 5. Identidades

La Sábana define el RUT/razón social rector según el contrato del proceso.
El ENS original aporta los registros de energía y suministradores.

No mezclar todos los retiros de un RUT:
el alcance se aplica a las filas correctas, incluyendo `Distribuidora_Conec` y otros discriminantes cuando sean necesarios.

No inventar una identidad si el cliente aparece `S/I`.

## 6. Conservación

Para cada grupo, mes y suministrador:

`SUM(MWh origen admitido × factor) = SUM(MWh salida bajo M)`

Y para el grupo completo:

`SUM(MWh origen) = SUM(MWh destino)`

salvo reglas de reparto expresamente documentadas.

No comparar totales de universos distintos.

## 7. Medidor compartido por PC

Si Piuquenes y Mauro apuntan al mismo M:
- la energía se armoniza una sola vez;
- el mantenedor contiene dos relaciones PC→M;
- el archivo ENS no recibe dos copias del vector.

## 8. Golden case Pelambres 2511

M:
- `QUILLOTA______220`
- `BA S/E QUILLOTA 220KV BP1-1`
- ID 519.

Orígenes:
- `CENTELLA______220`
- `QUILLOTA______220`

Cinco suministradores.
Diez filas originales pasan a cinco filas bajo M.

Energía:
- Centella = 91.552,117116 MWh
- Quillota = 36.508,319864 MWh
- M = 128.060,436980 MWh

Los Vilos queda intacto.
Quereo de distribución queda intacto.

## 9. Estados que deben detener automatización

- `APTO_COMPOSICION=0`
- M inexistente o `SIN MEDIDOR ASOCIADO`
- BarraF requerida ausente del ENS del mes
- identidad cliente no conciliada
- doble asignación del mismo registro a destinos incompatibles
- factor requerido pero ausente
- múltiples mappings de M contradictorios
- archivo ya armonizado
- versión de contrato incompatible

## 10. Retiros sin PC

No se resuelven en la primera versión.
Deben quedar en una bandeja de gestión y nunca provocar que el resto del archivo deje de procesarse.

## 11. EFE

Es una regla especial ya autorizada.
No generalizar su reparto `1/N` a otros clientes.
La primera versión del armonizador puede aislarla como módulo/regla explícita.

## 12. Salidas

- ENS armonizado.
- TRAZA de filas origen→destino.
- QA por grupo/mes/suministrador.
- Pendientes y warnings.
- Manifiesto con hashes, versiones, fecha, mes y parámetros.
