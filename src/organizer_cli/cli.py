from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import typer

from .analyzer import analyze_cleanup
from .branding import (
    print_action_menu,
    print_brand_header,
    print_completion_banner,
    print_folder_choices,
    print_selected_folder,
    print_status,
)
from .cleanup_review import (
    REVIEW_CATEGORY_ALL,
    REVIEW_CATEGORY_DUPLICATES,
    REVIEW_CATEGORY_LARGE,
    REVIEW_CATEGORY_OLD,
    REVIEW_CATEGORY_OLD_ARCHIVES,
    REVIEW_CATEGORY_SUSPICIOUS,
    SelectionParseError,
    build_quarantine_plan,
    build_review_items,
    filter_review_items,
    parse_selection,
    selection_to_items,
)
from .date_organization import DateMode
from .models import CleanupOptions, CleanupReport, CleanupReviewItem, MoveResult
from .mover import iter_apply_plan
from .planner import build_plan
from .reporter import (
    print_apply_progress,
    print_cleanup_summary,
    print_preview,
    print_quarantine_preview,
    print_quarantine_results,
    print_review_items,
    print_rules,
    write_cleanup_report_txt,
)
from .rules import iter_rules
from .scanner import scan_root

app = typer.Typer(help="Organizador seguro de archivos sueltos: preview primero, apply sólo con confirmación.")
rules_app = typer.Typer(help="Mostrar reglas incorporadas.")
app.add_typer(rules_app, name="rules")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Punto de entrada principal: sugiere el menú sin sorprender a subcomandos."""

    if ctx.invoked_subcommand is not None:
        return

    print_brand_header("Flujo recomendado: `organizer menu`")
    typer.echo("Usá `organizer menu` para abrir el flujo guiado.")
    typer.echo("Comandos avanzados: `preview PATH`, `analyze PATH`, `review PATH`, `apply PATH --confirm`, `rules show`.")
    typer.echo("Organización por fecha opcional: `--date-mode none|year|year-month`.")


@app.command()
def preview(path: Path, date_mode: DateMode = typer.Option(DateMode.NONE, "--date-mode", help="Organización por fecha: none, year o year-month.")) -> None:
    """Muestra el plan para PATH sin crear carpetas ni mover archivos."""

    scan = scan_root(path)
    plan = build_plan(scan, date_mode=date_mode)
    print_preview(scan, plan)


@app.command()
def apply(
    path: Path,
    confirm: bool = typer.Option(False, "--confirm", help="Confirma movimientos reales."),
    date_mode: DateMode = typer.Option(DateMode.NONE, "--date-mode", help="Organización por fecha: none, year o year-month."),
) -> None:
    """Aplica el plan sólo con --confirm y muestra progreso por archivo."""

    if not confirm:
        print_status(
            "error",
            "Refusing to apply without --confirm. Run `organizer apply PATH --confirm` to move files.",
        )
        raise typer.Exit(code=1)

    scan = scan_root(path)
    plan = build_plan(scan, date_mode=date_mode)
    print_apply_progress(scan, plan, iter_apply_plan(plan))


@app.command()
def analyze(
    path: Path,
    old_days: int = typer.Option(180, "--old-days", min=1, help="Días para considerar un archivo viejo."),
    large_mb: int = typer.Option(100, "--large-mb", min=1, help="MB para considerar un archivo pesado."),
    archive_days: int = typer.Option(180, "--archive-days", min=1, help="Días para instaladores/comprimidos viejos."),
    recursive: bool = typer.Option(False, "--recursive", help="Incluye archivos dentro de subcarpetas. Por defecto no recorre carpetas."),
    output: Path | None = typer.Option(None, "--output", help="Ruta .txt o carpeta donde guardar el reporte."),
    open_report: bool = typer.Option(False, "--open-report", help="Abre el TXT generado con la app predeterminada si el sistema lo permite."),
) -> None:
    """Analiza posibles archivos viejos, pesados, duplicados o temporales sin modificar originales."""

    _analyze_path(
        path,
        options=CleanupOptions(old_days=old_days, large_mb=large_mb, archive_days=archive_days, recursive=recursive),
        output=output,
        open_report=open_report,
    )


@app.command()
def review(
    path: Path,
    old_days: int = typer.Option(180, "--old-days", min=1, help="Días para considerar un archivo viejo."),
    large_mb: int = typer.Option(100, "--large-mb", min=1, help="MB para considerar un archivo pesado."),
    archive_days: int = typer.Option(180, "--archive-days", min=1, help="Días para instaladores/comprimidos viejos."),
    recursive: bool = typer.Option(False, "--recursive", help="Incluye archivos dentro de subcarpetas. Por defecto no recorre carpetas."),
) -> None:
    """Revisa hallazgos y mueve sólo lo seleccionado a una cuarentena recuperable."""

    typer.echo("")
    print_status("info", f"Analizando para revisión segura: {path}")
    typer.echo("No hay borrado permanente: lo confirmado se mueve a _cleanup_quarantine.")
    report = analyze_cleanup(path, CleanupOptions(old_days=old_days, large_mb=large_mb, archive_days=archive_days, recursive=recursive))
    print_cleanup_summary(report)
    _review_report_loop(report)


@app.command("menu")
def menu() -> None:
    """Abre un flujo guiado apto para CMD: elegir carpeta, acción y confirmar."""

    try:
        _run_menu()
    except typer.Abort:
        print_status("warning", "Cancelado: no se movió nada.")
        raise typer.Exit(code=0) from None


def _run_menu() -> None:
    print_brand_header("Menú guiado para organizar sin memorizar flags")
    path = _choose_path()

    while True:
        typer.echo("")
        print_selected_folder(path)
        action = _choose_action()

        if action == "exit":
            print_status("info", "Listo. No se movió nada.")
            return
        if action == "change_path":
            path = _choose_path()
            continue
        if action == "rules":
            _show_rules()
            continue
        if action == "preview":
            _preview_path(path, date_mode=DateMode.NONE)
            continue
        if action == "analyze":
            options = _choose_cleanup_options()
            report, _report_path = _analyze_path(path, options=options)
            if _prompt_yes_no("¿Querés revisar hallazgos para mover seleccionados a cuarentena?", default=False):
                _review_report_loop(report)
            continue
        if action == "review":
            options = _choose_cleanup_options()
            report = analyze_cleanup(path, options)
            print_cleanup_summary(report)
            _review_report_loop(report)
            continue

        date_mode = _choose_date_mode()
        scan, plan = _preview_path(path, date_mode=date_mode)
        applied = _apply_after_preview(scan, plan)
        if not applied:
            continue

        next_step = _choose_after_completion()
        if next_step == "exit":
            print_status("success", "Listo. Organización finalizada.")
            return
        if next_step == "change_path":
            path = _choose_path()


def _choose_action() -> str:
    while True:
        typer.echo("")
        print_action_menu(
            "Elegí qué hacer con la carpeta seleccionada",
            (
                ("1", "Preview selected folder", "Dry-run: no crea carpetas ni mueve archivos"),
                ("2", "Organize selected folder", "Muestra preview y pide confirmación antes de mover"),
                ("3", "Analyze selected folder", "Reporte de viejos, pesados, duplicados y copias; no borra nada"),
                ("4", "Review findings", "Elegí hallazgos y movelos a cuarentena recuperable"),
                ("5", "Change selected folder", "Elegir otra carpeta"),
                ("6", "Show rules", "Ver categorías y patrones incorporados"),
                ("7", "Exit", "Salir sin mover nada"),
            ),
        )

        choice = typer.prompt("Opción", default="1").strip()
        actions = {
            "1": "preview",
            "preview": "preview",
            "2": "apply",
            "organize": "apply",
            "organize folder": "apply",
            "organize selected folder": "apply",
            "3": "analyze",
            "analyze": "analyze",
            "analyze selected folder": "analyze",
            "cleanup report": "analyze",
            "4": "review",
            "review": "review",
            "review findings": "review",
            "cuarentena": "review",
            "5": "change_path",
            "change": "change_path",
            "change folder": "change_path",
            "change selected folder": "change_path",
            "6": "rules",
            "rules": "rules",
            "show rules": "rules",
            "7": "exit",
            "exit": "exit",
            "salir": "exit",
        }
        action = actions.get(choice.casefold())
        if action is not None:
            return action

        print_status("error", "Opción inválida. Elegí un número del menú: 1, 2, 3, 4, 5, 6 o 7.")


def _choose_date_mode() -> DateMode:
    while True:
        typer.echo("")
        print_action_menu(
            "¿Cómo querés organizar por fecha?",
            (
                ("1", "Sin fecha (actual)", "Mantiene destinos como Documentos/PDF"),
                ("2", "Por año", "Ejemplo: Documentos/PDF/2025"),
                ("3", "Por año y mes", "Ejemplo: Documentos/PDF/2025/06-Junio"),
            ),
        )

        choice = typer.prompt("Opción", default="1").strip().casefold()
        modes = {
            "1": DateMode.NONE,
            "": DateMode.NONE,
            "none": DateMode.NONE,
            "sin fecha": DateMode.NONE,
            "2": DateMode.YEAR,
            "year": DateMode.YEAR,
            "año": DateMode.YEAR,
            "anio": DateMode.YEAR,
            "por año": DateMode.YEAR,
            "por anio": DateMode.YEAR,
            "3": DateMode.YEAR_MONTH,
            "year-month": DateMode.YEAR_MONTH,
            "año mes": DateMode.YEAR_MONTH,
            "anio mes": DateMode.YEAR_MONTH,
            "por año y mes": DateMode.YEAR_MONTH,
            "por anio y mes": DateMode.YEAR_MONTH,
        }
        mode = modes.get(choice)
        if mode is not None:
            return mode

        print_status("error", "Opción inválida. Elegí 1, 2 o 3.")


def _choose_cleanup_options() -> CleanupOptions:
    """Ask friendly cleanup-analysis options for the interactive menu."""

    defaults = CleanupOptions()
    typer.echo("")
    print_action_menu(
        "Opciones del análisis seguro",
        (
            ("old-days", f"{defaults.old_days} días", "Detecta archivos viejos"),
            ("large-mb", f"{defaults.large_mb} MB", "Detecta archivos pesados"),
            ("archive-days", f"{defaults.archive_days} días", "Detecta instaladores/comprimidos viejos"),
            ("recursive", "no", "Por defecto no revisa subcarpetas"),
        ),
    )

    if _prompt_yes_no("¿Usar umbrales por defecto?", default=True):
        return defaults

    typer.echo("Bien, ajustemos los umbrales. Ingresá números enteros mayores a cero.")
    old_days = _prompt_positive_int("Días para considerar un archivo viejo", default=defaults.old_days)
    large_mb = _prompt_positive_int("MB para considerar un archivo pesado", default=defaults.large_mb)
    archive_days = _prompt_positive_int("Días para instaladores/comprimidos viejos", default=defaults.archive_days)
    recursive = _prompt_yes_no("¿Analizar también subcarpetas?", default=defaults.recursive)
    return CleanupOptions(old_days=old_days, large_mb=large_mb, archive_days=archive_days, recursive=recursive)


def _prompt_positive_int(label: str, *, default: int) -> int:
    while True:
        raw = typer.prompt(label, default=str(default)).strip()
        try:
            value = int(raw)
        except ValueError:
            print_status("error", "Valor inválido. Escribí un número entero mayor a cero.")
            continue
        if value < 1:
            print_status("error", "Valor inválido. El número tiene que ser mayor a cero.")
            continue
        return value


def _prompt_yes_no(label: str, *, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    default_text = "y" if default else "n"
    yes_values = {"y", "yes", "s", "si", "sí"}
    no_values = {"n", "no"}

    while True:
        raw = typer.prompt(f"{label} [{suffix}]", default=default_text).strip().casefold()
        if raw in yes_values:
            return True
        if raw in no_values:
            return False
        print_status("error", "Respuesta inválida. Escribí y/sí o n/no.")


def _default_downloads() -> Path | None:
    candidates: list[Path] = []

    def add(candidate: str | Path | None) -> None:
        if not candidate:
            return
        path = Path(candidate).expanduser()
        if path not in candidates:
            candidates.append(path)

    add(Path.home() / "Downloads")
    add(os.environ.get("USERPROFILE") and Path(os.environ["USERPROFILE"]) / "Downloads")
    add(os.environ.get("DOWNLOADS"))
    add(os.environ.get("OneDrive") and Path(os.environ["OneDrive"]) / "Downloads")
    add(os.environ.get("OneDriveConsumer") and Path(os.environ["OneDriveConsumer"]) / "Downloads")

    if sys.platform == "win32":
        add(_windows_known_downloads())
        username = os.environ.get("USERNAME")
        cwd_drive = Path.cwd().drive
        if username and cwd_drive:
            add(Path(f"{cwd_drive}\\") / username / "Downloads")

    for parent in (Path.cwd(), *Path.cwd().parents):
        if parent.name.casefold() == "downloads":
            add(parent)
            break

    for downloads in candidates:
        if downloads.exists() and downloads.is_dir():
            return downloads.resolve()
    return None


def _windows_known_downloads() -> Path | None:
    if sys.platform != "win32":
        return None

    try:
        import ctypes
        from ctypes import wintypes

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wintypes.DWORD),
                ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        folder_id_downloads = GUID(
            0x374DE290,
            0x123F,
            0x4565,
            (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B),
        )
        path_pointer = wintypes.LPWSTR()
        result = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(folder_id_downloads),
            0,
            None,
            ctypes.byref(path_pointer),
        )
        if result != 0:
            return None
        try:
            return Path(path_pointer.value)
        finally:
            ctypes.windll.ole32.CoTaskMemFree(path_pointer)
    except Exception:
        return None


def _choose_path() -> Path:
    default_downloads = _default_downloads()

    while True:
        typer.echo("")
        if default_downloads is not None:
            print_folder_choices(default_downloads)
            choice = typer.prompt("Opción", default="1").strip().casefold()
            if choice in {"1", "", "downloads", "default", "d"}:
                return default_downloads
            if choice in {"3", "exit", "salir", "cancel", "cancelar", "c"}:
                print_status("warning", "Cancelado: no se movió nada.")
                raise typer.Exit(code=0)
            if choice not in {"2", "manual", "m"}:
                print_status("error", "Opción inválida. Elegí 1, 2 o 3.")
                continue
            typer.echo("Ingresá una carpeta manual o escribí `cancel` para salir.")
        else:
            print_folder_choices(None)

        raw_path = typer.prompt("Carpeta", default="").strip()
        if raw_path.casefold() in {"cancel", "cancelar", "c", "salir", "exit"}:
            print_status("warning", "Cancelado: no se movió nada.")
            raise typer.Exit(code=0)
        if not raw_path:
            print_status("error", "Ruta vacía. Probá de nuevo o escribí `cancel`.")
            continue

        candidate = Path(raw_path).expanduser().resolve()
        if not candidate.exists():
            print_status("error", f"La ruta no existe: {candidate}")
            typer.echo("Probá de nuevo o escribí `cancel`.")
            continue
        if not candidate.is_dir():
            print_status("error", f"La ruta no es una carpeta: {candidate}")
            typer.echo("Probá de nuevo o escribí `cancel`.")
            continue
        return candidate


def _preview_path(path: Path, *, date_mode: DateMode = DateMode.NONE):
    typer.echo("")
    print_status("info", f"Preview de carpeta seleccionada: {path}")
    scan = scan_root(path)
    plan = build_plan(scan, date_mode=date_mode)
    print_preview(scan, plan)
    return scan, plan


def _analyze_path(
    path: Path,
    *,
    options: CleanupOptions | None = None,
    output: Path | None = None,
    open_report: bool = False,
):
    typer.echo("")
    print_status("info", f"Analizando carpeta seleccionada: {path}")
    typer.echo("Reporte solamente: no se borra, no se mueve y no se renombra nada.")
    report = analyze_cleanup(path, options or CleanupOptions())
    report_path = write_cleanup_report_txt(report, output)
    print_cleanup_summary(report, report_path=report_path)
    if open_report:
        _open_report(report_path)
    return report, report_path


def _open_report(report_path: Path) -> None:
    try:
        startfile = getattr(os, "startfile")
        startfile(report_path)  # type: ignore[misc]
        print_status("success", f"Reporte abierto: {report_path}")
    except Exception as exc:
        print_status("warning", f"No se pudo abrir automáticamente el reporte: {exc}")


def _review_report_loop(report: CleanupReport) -> None:
    all_items = build_review_items(report)
    if not all_items:
        print_status("info", "No hay hallazgos revisables para cuarentena.")
        return

    while True:
        category = _choose_review_category(all_items)
        if category == "exit":
            print_status("info", "Revisión finalizada. No se borró nada.")
            return

        category_items = filter_review_items(all_items, category)
        if not category_items:
            print_status("warning", "No hay candidatos en esta categoría.")
        else:
            results = _review_category_once(report, category_items)
            if any(result.applied for result in results):
                report = analyze_cleanup(report.root, report.options)
                all_items = build_review_items(report)

        if not _prompt_yes_no("¿Querés revisar más hallazgos?", default=True):
            print_status("info", "Revisión finalizada. No se borró nada permanentemente.")
            return
        if not all_items:
            print_status("success", "No quedan hallazgos revisables para cuarentena.")
            return


def _choose_review_category(items: tuple[CleanupReviewItem, ...]) -> str:
    counts = {
        REVIEW_CATEGORY_DUPLICATES: len(filter_review_items(items, REVIEW_CATEGORY_DUPLICATES)),
        REVIEW_CATEGORY_SUSPICIOUS: len(filter_review_items(items, REVIEW_CATEGORY_SUSPICIOUS)),
        REVIEW_CATEGORY_OLD_ARCHIVES: len(filter_review_items(items, REVIEW_CATEGORY_OLD_ARCHIVES)),
        REVIEW_CATEGORY_OLD: len(filter_review_items(items, REVIEW_CATEGORY_OLD)),
        REVIEW_CATEGORY_LARGE: len(filter_review_items(items, REVIEW_CATEGORY_LARGE)),
        REVIEW_CATEGORY_ALL: len(filter_review_items(items, REVIEW_CATEGORY_ALL)),
    }
    while True:
        typer.echo("")
        print_action_menu(
            "¿Qué querés revisar?",
            (
                ("1", f"Duplicados extras ({counts[REVIEW_CATEGORY_DUPLICATES]})", "Conserva un representante por grupo exacto"),
                ("2", f"Nombres sospechosos ({counts[REVIEW_CATEGORY_SUSPICIOUS]})", "copy, backup, temp, final, versiones"),
                ("3", f"Instaladores/comprimidos viejos ({counts[REVIEW_CATEGORY_OLD_ARCHIVES]})", "ZIP/EXE/MSI antiguos"),
                ("4", f"Archivos viejos ({counts[REVIEW_CATEGORY_OLD]})", "Conservador: revisá antes de seleccionar"),
                ("5", f"Archivos pesados ({counts[REVIEW_CATEGORY_LARGE]})", "Advertencia para liberar espacio"),
                ("6", f"Todos los hallazgos revisables ({counts[REVIEW_CATEGORY_ALL]})", "Incluye duplicados, sospechosos, viejos y pesados"),
                ("7", "Salir de revisión", "Volver sin mover nada más"),
            ),
        )
        choice = typer.prompt("Opción", default="7").strip().casefold()
        categories = {
            "1": REVIEW_CATEGORY_DUPLICATES,
            "duplicados": REVIEW_CATEGORY_DUPLICATES,
            "duplicates": REVIEW_CATEGORY_DUPLICATES,
            "2": REVIEW_CATEGORY_SUSPICIOUS,
            "sospechosos": REVIEW_CATEGORY_SUSPICIOUS,
            "suspicious": REVIEW_CATEGORY_SUSPICIOUS,
            "3": REVIEW_CATEGORY_OLD_ARCHIVES,
            "instaladores": REVIEW_CATEGORY_OLD_ARCHIVES,
            "archives": REVIEW_CATEGORY_OLD_ARCHIVES,
            "4": REVIEW_CATEGORY_OLD,
            "viejos": REVIEW_CATEGORY_OLD,
            "old": REVIEW_CATEGORY_OLD,
            "5": REVIEW_CATEGORY_LARGE,
            "pesados": REVIEW_CATEGORY_LARGE,
            "large": REVIEW_CATEGORY_LARGE,
            "6": REVIEW_CATEGORY_ALL,
            "all": REVIEW_CATEGORY_ALL,
            "todos": REVIEW_CATEGORY_ALL,
            "7": "exit",
            "q": "exit",
            "exit": "exit",
            "salir": "exit",
        }
        category = categories.get(choice)
        if category is not None:
            return category
        print_status("error", "Opción inválida. Elegí un número del 1 al 7.")


def _review_category_once(report: CleanupReport, items: tuple[CleanupReviewItem, ...]) -> tuple[MoveResult, ...]:
    print_review_items(items, use_rich=False)
    selection = _prompt_review_selection(len(items))
    if selection.cancelled or not selection.selected_indexes:
        print_status("warning", "Sin selección: no se movió nada.")
        return ()

    selected = selection_to_items(items, selection.selected_indexes)
    plan = build_quarantine_plan(report.root, selected, datetime.now())
    print_quarantine_preview(plan, use_rich=False)
    if not typer.confirm("¿Mover estos archivos seleccionados a cuarentena?", default=False):
        print_status("warning", "Cancelado: no se movió nada.")
        return ()

    results = tuple(iter_apply_plan(plan))
    print_quarantine_results(results)
    return results


def _prompt_review_selection(max_index: int):
    while True:
        raw = typer.prompt("Selección (ej: 1,3,5 | 1-10 | all | none | q)", default="none")
        try:
            return parse_selection(raw, max_index)
        except SelectionParseError as exc:
            print_status("error", f"Selección inválida. {exc}")


def _apply_after_preview(scan, plan) -> bool:
    confirmed = typer.confirm("¿Mover estos archivos ahora?", default=False)
    if not confirmed:
        print_status("warning", "Cancelado: no se movió nada.")
        return False

    print_apply_progress(scan, plan, iter_apply_plan(plan), use_rich=False)
    print_completion_banner()
    return True


def _print_completion_banner() -> None:
    print_completion_banner()


def _choose_after_completion() -> str:
    while True:
        typer.echo("")
        print_action_menu(
            "¿Qué querés hacer ahora?",
            (
                ("1", "Continuar con esta carpeta", "Volver al menú de acciones"),
                ("2", "Cambiar carpeta", "Elegir otra ruta"),
                ("3", "Salir", "Finalizar"),
            ),
        )

        choice = typer.prompt("Opción", default="1").strip().casefold()
        actions = {
            "1": "continue",
            "continuar": "continue",
            "continue": "continue",
            "2": "change_path",
            "cambiar": "change_path",
            "change": "change_path",
            "change folder": "change_path",
            "3": "exit",
            "salir": "exit",
            "exit": "exit",
            "no": "exit",
            "n": "exit",
        }
        action = actions.get(choice)
        if action is not None:
            return action

        print_status("error", "Opción inválida. Elegí 1 para continuar, 2 para cambiar carpeta o 3 para salir.")


def _show_rules() -> None:
    print_rules(iter_rules())


@rules_app.command("show")
def rules_show() -> None:
    """Lista las categorías y extensiones/patrones del MVP."""

    _show_rules()


if __name__ == "__main__":
    app()
