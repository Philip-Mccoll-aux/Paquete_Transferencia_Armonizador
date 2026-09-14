# Casos y warnings para la primera implementación

## Retiros sin PC
El resultado contiene **21** retiros sin punto de control.
No deben borrarse ni recibir un PC automático.
Se gestionarán en otra etapa.

## Sin medidor asociado
- Aguas Pacífico — S/E Puchuncaví.
- Minera Centinela — S/E Socompa.

No inventar un M.

## ID de M no numérico / S/I
Se observaron **19** entradas de catálogo M sin ID Infotécnica numérico, contando el registro grupal especial EFE.
La lógica debe separar:
- nombre de M resuelto;
- ID numérico faltante;
- exigencia real del cargador.

## Recetas no aptas
`LT_ESTADOS_M_MES` contiene **122** grupos-mes no aptos.
Nunca usar energía parcial para completar una receta.

## Mantenedor
Todos los grupos-mes continúan con `APTO_CARGA_OFICIAL=0` en este resultado.
El armonizador no tiene autoridad para marcar una carga como oficial.
La relación PC→M debe ser aplicada/validada en el mantenedor.

## EFE
25 PC, factor 0,04.
Cada PC conserva su propia homologación de barra.
No obligarlo al patrón M único del resto de grupos compartidos.

## Campo `ID BARRA MEDIDOR`
En las hojas de presentación representa fuentes usadas en la última ventana y puede listar varias BarraF.
No usarlo como M persistente.
