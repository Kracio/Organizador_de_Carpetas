# Organizador de Carpetas

CLI en Python para organizar archivos sueltos de una carpeta de forma segura. Está pensado especialmente para carpetas como `Downloads`, donde suelen acumularse documentos, imágenes, instaladores, comprimidos y archivos multimedia sin una estructura clara.

El proyecto prioriza un flujo conservador: primero muestra un preview del plan de organización y recién mueve archivos cuando existe una confirmación explícita.

## Qué problema resuelve

Organizar una carpeta de descargas a mano es repetitivo. Automatizarlo sin controles también puede ser riesgoso: una herramienta de este tipo no debería sobrescribir archivos, recorrer carpetas internas inesperadamente ni mover contenido sin mostrar antes qué va a hacer.

Organizador de Carpetas resuelve ese caso con reglas simples, salida clara en terminal y un modelo de seguridad diseñado para evitar sorpresas.

## Características

- Menú guiado para Windows.
- Ejecutable publicado como `OrganizadorDeCarpetas.exe` en GitHub Releases.
- Launcher local `abrir-organizador.bat` para entornos de desarrollo instalados.
- Comandos CLI para preview, análisis de limpieza, revisión con cuarentena, apply confirmado y consulta de reglas.
- Clasificación por categorías habituales: documentos, fotos, capturas, comprimidos, multimedia, instaladores y otros.
- Preview antes de modificar el disco.
- Organización opcional por fecha de modificación: sin fecha, por año o por año/mes.
- Resolución de colisiones sin sobrescribir archivos.
- Progreso y resumen durante la organización.
- Reporte TXT de limpieza para detectar archivos viejos, pesados, duplicados exactos, instaladores/comprimidos viejos y nombres sospechosos.
- Revisión asistida de hallazgos para mover seleccionados a `_cleanup_quarantine`, sin borrado permanente.
- Suite de tests automatizados con `pytest`.

## Modelo de seguridad

El comportamiento por defecto está diseñado para ser predecible y reversible antes de aplicar cambios:

- `preview` sólo muestra el plan: no crea carpetas, no mueve archivos y no borra nada.
- `analyze` sólo genera un reporte: no crea carpetas de organización, no mueve archivos, no renombra archivos y no borra nada. Puede leer contenido de archivos para calcular hashes SHA-256 y detectar duplicados exactos.
- `review` analiza y permite seleccionar hallazgos para moverlos a una cuarentena timestamped dentro de la carpeta analizada. No borra permanentemente y pide confirmación explícita antes de mover.
- `apply` requiere `--confirm`; sin esa opción se niega a ejecutar movimientos reales.
- El menú guiado siempre muestra el preview antes de pedir confirmación para organizar.
- El escaneo es no recursivo: sólo toma archivos directos de la carpeta elegida.
- Las carpetas existentes se ignoran: no se mueven, no se recorren y no se modifican.
- Nunca sobrescribe archivos existentes; si hay colisión, genera nombres como `archivo (1).pdf`.
- Si un archivo no se puede mover por permisos, ausencia o error del sistema, se salta y el proceso continúa con el resto.
- La cuarentena nunca sobrescribe destinos existentes; ante colisión usa nombres como `archivo (1).pdf`.

## Uso con el ejecutable de Windows

Para usar la aplicación sin instalar Python:

1. Abrí la sección **Releases** del repositorio.
2. Descargá `OrganizadorDeCarpetas.exe` desde la última release.
3. Ejecutá el archivo con doble clic.
4. Elegí una carpeta.
5. Usá primero el preview para revisar el plan.
6. Confirmá sólo si querés mover los archivos.

> En Windows puede aparecer una advertencia de SmartScreen porque el ejecutable no está firmado digitalmente. Esto es habitual en binarios generados con PyInstaller sin certificado de firma.

## Uso local con `.bat`

Si el proyecto ya está instalado en un entorno virtual local, podés abrir el menú con doble clic en:

```text
abrir-organizador.bat
```

El launcher activa `.venv`, valida que el comando `organizer` esté instalado y abre el menú guiado.

## Instalación para desarrollo

Requisitos:

- Python 3.11 o superior.
- Windows, PowerShell o CMD para el flujo con `.bat`.

Instalación editable con dependencias de desarrollo:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Para incluir herramientas de empaquetado con PyInstaller:

```bash
pip install -e ".[dev,packaging]"
```

## Comandos

Abrir el menú guiado:

```bash
organizer menu
```

Mostrar el plan sin mover archivos:

```bash
organizer preview "C:\Users\tu-usuario\Downloads"
```

También podés agregar carpetas por fecha de modificación sin cambiar la clasificación principal:

```bash
organizer preview "C:\Users\tu-usuario\Downloads" --date-mode year-month
```

Aplicar el plan con confirmación explícita:

```bash
organizer apply "C:\Users\tu-usuario\Downloads" --confirm
```

### Análisis de limpieza: reporte solamente

Generar un reporte de limpieza sin modificar archivos:

```bash
organizer analyze "C:\Users\tu-usuario\Downloads"
```

El análisis crea por defecto un archivo TXT dentro de la carpeta analizada con nombre similar a:

```text
cleanup-report-20260610-153012.txt
```

`organizer analyze PATH` es un flujo de **informe solamente**. Genera un TXT, imprime un resumen en terminal y no mueve, renombra ni borra archivos. Detecta y resume:

- Archivos viejos (`--old-days 180` por defecto).
- Archivos pesados (`--large-mb 100` por defecto).
- Duplicados exactos, comparando primero tamaño y después hash SHA-256.
- Instaladores/comprimidos viejos (`--archive-days 180` por defecto).
- Nombres sospechosos como `copy`, `copia`, `(1)`, `backup`, `temp`, `download`, `final`, `v2`, etc.

El análisis es no recursivo por defecto y cuenta las carpetas ignoradas. Para incluir archivos dentro de subcarpetas, usá el flag explícito:

```bash
organizer analyze "C:\Users\tu-usuario\Downloads" --recursive
```

También podés elegir dónde guardar el TXT:

```bash
organizer analyze "C:\Users\tu-usuario\Downloads" --output "C:\Users\tu-usuario\Desktop\reporte-limpieza.txt"
```

Si querés abrir el reporte al terminar y el sistema lo permite:

```bash
organizer analyze "C:\Users\tu-usuario\Downloads" --open-report
```

### Revisión segura: cuarentena recuperable

Revisar hallazgos y mover sólo los seleccionados a cuarentena:

```bash
organizer review "C:\Users\tu-usuario\Downloads"
```

`organizer review PATH` usa los mismos umbrales principales del análisis (`--old-days`, `--large-mb`, `--archive-days`) y también acepta `--recursive` para revisar subcarpetas de forma explícita. La revisión permite elegir categorías como duplicados extra, nombres sospechosos, instaladores/comprimidos viejos, archivos viejos, archivos pesados o todos los hallazgos revisables. La selección acepta:

```text
1,3,5
1-10
all
none
q
```

Antes de mover, muestra una vista previa y pide confirmación. Si respondés que no, no se crea cuarentena y no se mueve nada. Los archivos confirmados van a una carpeta similar a:

```text
_cleanup_quarantine\2026-06-10_153012\
```

Después de revisar una categoría, el menú pregunta si querés revisar más hallazgos para poder empezar por nombres sospechosos, cuarentenar lo elegido y seguir con duplicados, instaladores viejos u otras categorías.

**Importante:** la revisión no elimina archivos automáticamente. Sólo mueve los hallazgos seleccionados a `_cleanup_quarantine` para que los puedas revisar y recuperar. Si más adelante decidís que ya no los necesitás, el borrado manual queda bajo tu control.

### Integración en el menú

El menú guiado incluye dos entradas para limpieza:

- **Analyze selected folder**: ejecuta el análisis, guarda el TXT y después pregunta si querés revisar hallazgos para cuarentena. La respuesta por defecto es No.
- **Review findings**: abre directamente la revisión interactiva para seleccionar hallazgos, ver la vista previa de cuarentena y confirmar. Después de cada acción ofrece revisar más hallazgos.

Modos de fecha disponibles:

- `none` (default): mantiene destinos como `Documentos/PDF/reporte.pdf`.
- `year`: agrega el año, por ejemplo `Documentos/PDF/2025/reporte.pdf`.
- `year-month`: agrega año y mes, por ejemplo `Documentos/PDF/2025/06-Junio/reporte.pdf`.

La fecha usada es la modificación del archivo. El menú guiado pregunta el modo antes del preview y, si organizás, aplica exactamente ese mismo plan.

Ver las reglas incorporadas:

```bash
organizer rules show
```

Ejecutar `organizer` sin argumentos no organiza archivos; sólo muestra una sugerencia para abrir el menú guiado.

## Tests

La suite usa `pytest`:

```bash
.venv\Scripts\python.exe -m pytest
```

## Arquitectura

El flujo principal está separado en módulos pequeños y testeables:

```text
scanner -> rules -> planner -> reporter -> mover
analyzer -> cleanup_review -> reporter -> mover
analyzer -> reporter -> TXT export
```

- `scanner`: escanea archivos directos de la carpeta objetivo e ignora subcarpetas.
- `rules`: clasifica cada archivo con reglas determinísticas incorporadas.
- `planner`: construye un plan de movimientos, agrega carpetas opcionales por fecha y resuelve colisiones de nombres.
- `reporter`: muestra previews, reglas, progreso y resúmenes en terminal.
- `mover`: ejecuta los movimientos confirmados sin sobrescribir destinos existentes.
- `analyzer`: genera reportes informativos de limpieza sin mutar archivos originales.
- `cleanup_review`: convierte reportes en candidatos revisables, parsea selecciones y planifica cuarentena segura.

El ejecutable de Windows usa PyInstaller y entra por `packaging/run_menu.py`, que abre el menú guiado por defecto.

## Stack

- Python 3.11+
- Typer para la CLI.
- Rich para salida de terminal.
- Pytest para tests.
- PyInstaller para generar el ejecutable de Windows.

## Categorías incorporadas

- `Fotos/WhatsApp`
- `Fotos/Capturas`
- `Fotos/General`
- `Documentos/PDF`
- `Documentos/Word`
- `Documentos/PowerPoint`
- `Documentos/Excel-CSV`
- `Comprimidos`
- `Multimedia/Videos`
- `Multimedia/Audio`
- `Instaladores`
- `Otros`

## Limitaciones y futuras ideas

- Las reglas son incorporadas en código; no hay todavía configuración externa por usuario.
- El escaneo es intencionalmente no recursivo para evitar modificar subcarpetas existentes.
- El análisis de limpieza también es no recursivo por defecto; `--recursive` inspecciona subcarpetas pero sigue siendo sólo reporte.
- No incluye una interfaz gráfica; el uso principal es por menú de terminal o comandos CLI.
- El ejecutable no está firmado digitalmente.
- Futuras mejoras posibles: reglas configurables, modo restore desde cuarentena, perfiles por carpeta y exportación del plan a archivo.
