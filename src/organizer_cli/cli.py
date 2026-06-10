from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from .branding import (
    print_action_menu,
    print_brand_header,
    print_completion_banner,
    print_folder_choices,
    print_selected_folder,
    print_status,
)
from .date_organization import DateMode
from .mover import iter_apply_plan
from .planner import build_plan
from .reporter import print_apply_progress, print_preview, print_rules
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
    typer.echo("Comandos avanzados: `preview PATH`, `apply PATH --confirm`, `rules show`.")
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
                ("3", "Change selected folder", "Elegir otra carpeta"),
                ("4", "Show rules", "Ver categorías y patrones incorporados"),
                ("5", "Exit", "Salir sin mover nada"),
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
            "3": "change_path",
            "change": "change_path",
            "change folder": "change_path",
            "change selected folder": "change_path",
            "4": "rules",
            "rules": "rules",
            "show rules": "rules",
            "5": "exit",
            "exit": "exit",
            "salir": "exit",
        }
        action = actions.get(choice.casefold())
        if action is not None:
            return action

        print_status("error", "Opción inválida. Elegí un número del menú: 1, 2, 3, 4 o 5.")


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
