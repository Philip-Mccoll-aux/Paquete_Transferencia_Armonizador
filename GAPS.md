# Brechas que requieren definición de negocio

Lista de decisiones que esta primera versión del armonizador **no toma por
sí sola** porque exceden su rol (no decide topología, familias ni
medidores) o porque el contrato actual no trae la información necesaria
para decidirlas de forma no ambigua.

## 1. EFE (`REPARTO_PC_AUTORIZADO`)
El armonizador aísla explícitamente cualquier grupo con
`MODO_CONSULTA=REPARTO_PC_AUTORIZADO` y no lo procesa (queda bloqueado con
motivo `EFE_REGLA_ESPECIAL_AISLADA_V1`). La especificación autoriza el
reparto 1/25 de EFE pero pide no generalizarlo; implementarlo como módulo
propio requiere que negocio confirme la fuente exacta de la relación
PC→homologación individual (`PC_HOMOLOGACIONES`) que se debe volcar al ENS
y cómo reparte contribuciones cuando hay más de un suministrador por PC.

## 2. Retiros sin punto de control (21 registros)
`04_RETIROS_SIN_PUNTO` no se procesa en esta versión (así lo pide la
especificación). El armonizador no los borra ni les asigna un PC
automático: simplemente no hay receta para ellos, así que sus filas de ENS
(si existen) quedan intactas. Falta definir el flujo operativo de la
"bandeja de gestión" — quién la revisa, con qué SLA, y si eventualmente
esos registros entran al armonizador o se gestionan fuera de él.

## 3. Exigencia real de ID Infotécnica numérico
19 entradas de catálogo M no tienen ID Infotécnica numérico (incluye el
registro grupal de EFE). El armonizador las trata como advertencia
informativa (`M_SIN_ID_INFOTECNICA_NUMERICO`) y sigue usando el nombre de
`BarraF`/`BarraInfotecnica` de M sin bloquear el grupo. Falta que el
cargador real de la Plataforma confirme si puede aceptar `IdBarraInfotecnica
= "S/I"` o si exige un número — en ese caso estos grupos deberían pasar a
bloqueantes.

## 4. Sin medidor asociado (Aguas Pacífico, Minera Centinela–Socompa)
El armonizador no inventa un M para estos dos casos: como no hay receta que
los reclame, sus filas de ENS permanecen intactas. Falta decisión de
negocio sobre si deben excluirse explícitamente del ENS, quedar marcados
de alguna forma, o esperar a que se les asigne un medidor.

## 5. `APTO_CARGA_OFICIAL`
Todos los grupos-mes del resultado usado como insumo tienen
`APTO_CARGA_OFICIAL=0`: la relación PC→M vive en el mantenedor interno de
la Plataforma y aún no ha sido aplicada/validada allí. El armonizador nunca
cambia ni interpreta este campo — sólo lo deja pasar en el reporte de QA.
La salida de esta herramienta (`ENS_ARMONIZADO_*.xlsx`) es material de
ensayo, no una carga oficial, hasta que ese mantenedor se aplique.

## 6. Conflictos de mapeo (`BarraF` reclamada por más de un grupo)
Cuando una misma `(RUT_INTEGRACION, BarraF)` aparece en más de una receta
del mismo mes, el armonizador bloquea **todos** los grupos involucrados
(no arma una fila parcial). En el ENS 2511 real no se observó ningún caso,
pero si llegara a ocurrir en otro mes, falta que negocio defina el criterio
de desempate (¿prioridad por versión de contrato? ¿por fecha de adopción?)
en vez de bloquear ambos grupos.

## 7. `FACTOR_ORIGEN_M` distinto de 1
En los meses observados el factor siempre es `1`. El motor ya soporta
aplicar un factor explícito por `(grupo, BarraF origen)` y bloquea si el
factor es contradictorio o falta cuando hay contribución, pero no ha sido
ejercitado contra un caso real con factor de reparto fraccional. Conviene
validar con un mes/grupo real antes de confiar en ese camino para
producción.

## 8. Identidad Sábana vs. ENS
La especificación indica que la Sábana define el RUT/razón social rector
del cliente. Esta versión usa siempre `RUT_INTEGRACION` del contrato para
seleccionar filas del ENS y preserva `RzSocCliente`/`RUTCliente` tal como
vienen en el ENS original — no reconcilia contra la Sábana ni resuelve
casos `S/I`. Es una integración explícitamente fuera de alcance de este
armonizador (spec §5) hasta que se defina el proceso/fuente de esa
reconciliación.
