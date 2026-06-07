from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Literal, TextIO

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


BRAND_NAME = "Organizador de Carpetas"
BRAND_TAGLINE = "Preview primero. Confirmación explícita. Cero sorpresas."

STYLE_BRAND = "bold cyan"
STYLE_MUTED = "dim"
STYLE_PATH = "magenta"
STYLE_SUCCESS = "bold green"
STYLE_WARNING = "bold yellow"
STYLE_ERROR = "bold red"
STYLE_INFO = "cyan"
STYLE_COUNT = "bold white"
STYLE_CATEGORY = "bold blue"

StatusKind = Literal["success", "warning", "error", "info"]


def should_use_rich(force_plain: bool = False) -> bool:
    """Return True only for real terminals, keeping captured tests plain and stable."""

    if force_plain:
        return False
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def get_console(*, force_plain: bool = False, record: bool = False, file: TextIO | None = None) -> Console:
    """Create the project console with a safe no-color seam for tests/non-TTY use."""

    return Console(
        file=file,
        record=record,
        no_color=force_plain or not should_use_rich(force_plain),
        force_terminal=False if force_plain else None,
        highlight=False,
        soft_wrap=True,
    )


def print_brand_header(subtitle: str | None = None, *, force_plain: bool = False) -> None:
    if not should_use_rich(force_plain):
        typer.echo(BRAND_NAME)
        typer.echo(BRAND_TAGLINE)
        if subtitle:
            typer.echo(subtitle)
        return

    console = get_console(force_plain=force_plain)
    body = Text(BRAND_TAGLINE, style=STYLE_MUTED)
    if subtitle:
        body.append("\n")
        body.append(subtitle, style=STYLE_INFO)
    console.print(Panel(body, title=f"[bold cyan]{BRAND_NAME}[/]", border_style="cyan", box=box.ROUNDED))


def print_status(kind: StatusKind, message: str, *, force_plain: bool = False) -> None:
    labels = {
        "success": "OK",
        "warning": "ATENCIÓN",
        "error": "ERROR",
        "info": "INFO",
    }
    styles = {
        "success": STYLE_SUCCESS,
        "warning": STYLE_WARNING,
        "error": STYLE_ERROR,
        "info": STYLE_INFO,
    }

    if not should_use_rich(force_plain):
        typer.echo(f"{labels[kind]}: {message}")
        return

    get_console(force_plain=force_plain).print(f"[{styles[kind]}]{labels[kind]}[/] {message}")


def print_selected_folder(path: Path, *, force_plain: bool = False) -> None:
    if not should_use_rich(force_plain):
        typer.echo(f"Carpeta seleccionada: {path}")
        return

    get_console(force_plain=force_plain).print(
        Panel(f"[dim]Carpeta seleccionada[/]\n[{STYLE_PATH}]{path}[/]", border_style="magenta", box=box.SIMPLE)
    )


def print_action_menu(title: str, actions: Sequence[tuple[str, str, str]], *, force_plain: bool = False) -> None:
    if not should_use_rich(force_plain):
        typer.echo(title)
        for number, label, _description in actions:
            typer.echo(f"{number}) {label}")
        return

    table = Table(box=box.SIMPLE, show_header=False, pad_edge=False)
    table.add_column("#", style=STYLE_COUNT, no_wrap=True)
    table.add_column("Acción", style="bold")
    table.add_column("Detalle", style=STYLE_MUTED)
    for number, label, description in actions:
        table.add_row(number, label, description)
    get_console(force_plain=force_plain).print(Panel(table, title=title, border_style="cyan", box=box.ROUNDED))


def print_folder_choices(default_downloads: Path | None, *, force_plain: bool = False) -> None:
    if default_downloads is None:
        print_status("warning", "No encontré una carpeta Downloads válida.", force_plain=force_plain)
        typer.echo("Ingresá una carpeta manual o `cancel` para salir.")
        return

    actions = (
        ("1", f"Usar Downloads detectada: {default_downloads}", "Recomendado para Windows/CMD"),
        ("2", "Ingresar carpeta manual", "Pegá una ruta propia"),
        ("3", "Exit", "Salir sin mover nada"),
    )
    print_action_menu("Primero elegí la carpeta a organizar", actions, force_plain=force_plain)


def print_completion_banner(*, force_plain: bool = False) -> None:
    if not should_use_rich(force_plain):
        typer.echo("")
        typer.echo("Organización completa")
        typer.echo("Realizado")
        return

    get_console(force_plain=force_plain).print(
        Panel(
            Text("Realizado", style=STYLE_SUCCESS),
            title="Organización completa",
            border_style="green",
            box=box.ROUNDED,
        )
    )


def plain_join(values: Iterable[str], *, empty: str = "-") -> str:
    items = tuple(values)
    return ", ".join(items) if items else empty
