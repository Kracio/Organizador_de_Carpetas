from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from .branding import get_console, plain_join, should_use_rich
from .models import MoveResult, PlannedMove, RunSummary, ScanResult

try:
    from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
except ImportError:  # pragma: no cover - exercised only when optional dependency is absent
    BarColumn = Progress = TaskProgressColumn = TextColumn = None  # type: ignore[assignment]


def summarize(scan: ScanResult, plan: tuple[PlannedMove, ...], results: tuple[MoveResult, ...] = ()) -> RunSummary:
    category_totals = Counter(move.category for move in plan)
    return RunSummary(
        scanned_files=len(scan.files),
        ignored_directories=scan.ignored_directories,
        planned_moves=len(plan),
        renamed_collisions=sum(1 for move in plan if move.collision_renamed),
        category_totals=dict(category_totals),
        applied_moves=sum(1 for result in results if result.applied),
        skipped_errors=sum(1 for result in results if not result.applied),
    )


def print_preview(scan: ScanResult, plan: tuple[PlannedMove, ...], *, use_rich: bool | None = None) -> RunSummary:
    summary = summarize(scan, plan)
    if use_rich is None:
        use_rich = _should_use_rich()
    if use_rich:
        console = get_console()
        console.print(Panel("No se modifica nada: dry-run seguro antes de mover.", title="PREVIEW", border_style="cyan", box=box.ROUNDED))
    else:
        typer.echo("PREVIEW - no se modifica nada")
    _print_plan(plan, use_rich=use_rich)
    _print_summary(summary, use_rich=use_rich)
    return summary


def print_apply(scan: ScanResult, plan: tuple[PlannedMove, ...], results: tuple[MoveResult, ...]) -> RunSummary:
    return print_apply_progress(scan, plan, results, use_rich=False)


def print_apply_progress(
    scan: ScanResult,
    plan: tuple[PlannedMove, ...],
    results: Iterable[MoveResult],
    *,
    use_rich: bool | None = None,
) -> RunSummary:
    """Print apply lifecycle/progress feedback while collecting streamed results."""

    total = len(plan)
    collected: list[MoveResult] = []
    if use_rich is None:
        use_rich = _should_use_rich()

    if use_rich:
        get_console().print(
            Panel(
                f"Movimientos confirmados: [bold]{total}[/] planificados",
                title="APPLY",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        typer.echo(f"APPLY - movimientos confirmados: {total} planificados")

    if use_rich and Progress is not None:
        with Progress(
            TextColumn("{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("{task.completed}/{task.total}"),
            transient=True,
        ) as progress:
            task_id = progress.add_task("Aplicando", total=total)
            for index, result in enumerate(results, start=1):
                collected.append(result)
                progress.update(task_id, advance=1, description=f"Aplicando {result.planned_move.source.name}")
                _print_move_result(result, index, total)
    else:
        for index, result in enumerate(results, start=1):
            collected.append(result)
            _print_move_result(result, index, total)

    summary = summarize(scan, plan, tuple(collected))
    _print_summary(summary, use_rich=use_rich)
    return summary


def _print_plan(plan: tuple[PlannedMove, ...], *, use_rich: bool = False) -> None:
    if not plan:
        typer.echo("No hay archivos sueltos para organizar.")
        return

    if use_rich:
        table = Table(title="Plan de movimientos", box=box.SIMPLE, show_lines=False)
        table.add_column("Archivo", style="bold")
        table.add_column("Destino", style="magenta")
        table.add_column("Categoría", style="blue")
        table.add_column("Nota", style="yellow")
        for move in plan:
            table.add_row(
                move.source.name,
                str(move.destination.relative_to(move.source.parent)),
                move.category,
                "renombrado por colisión" if move.collision_renamed else "",
            )
        get_console().print(table)
        return

    for move in plan:
        suffix = " (renombrado por colisión)" if move.collision_renamed else ""
        typer.echo(f"- {move.source.name} -> {move.destination.relative_to(move.source.parent)} [{move.category}]{suffix}")


def _print_move_result(result: MoveResult, index: int, total: int) -> None:
    marker = "OK" if result.applied else "SKIP"
    suffix = " (renombrado por colisión)" if result.planned_move.collision_renamed else ""
    typer.echo(
        f"[{marker}] {index}/{total} {result.planned_move.source.name} -> "
        f"{result.planned_move.destination}{suffix}"
    )
    if result.error:
        typer.echo(f"      reason: {result.error}")


def _should_use_rich() -> bool:
    if Progress is None:
        return False
    try:
        import sys

        return sys.stdout.isatty()
    except Exception:
        return False


def _print_summary(summary: RunSummary, *, use_rich: bool = False) -> None:
    if use_rich:
        table = Table(title="Resumen", box=box.SIMPLE)
        table.add_column("Métrica", style="dim")
        table.add_column("Total", justify="right", style="bold")
        table.add_row("Archivos escaneados", str(summary.scanned_files))
        table.add_row("Carpetas ignoradas", str(summary.ignored_directories))
        table.add_row("Movimientos planificados", str(summary.planned_moves))
        table.add_row("Movimientos aplicados", str(summary.applied_moves))
        table.add_row("Renombres por colisión", str(summary.renamed_collisions))
        table.add_row("Saltados con error", str(summary.skipped_errors))
        get_console().print(table)

        categories = Table(title="Totales por categoría", box=box.SIMPLE)
        categories.add_column("Categoría", style="blue")
        categories.add_column("Total", justify="right", style="bold")
        if summary.category_totals:
            for category, total in sorted(summary.category_totals.items()):
                categories.add_row(category, str(total))
        else:
            categories.add_row("(sin archivos)", "0")
        get_console().print(categories)
        return

    typer.echo("")
    typer.echo("Resumen")
    typer.echo(f"- Archivos escaneados: {summary.scanned_files}")
    typer.echo(f"- Carpetas ignoradas: {summary.ignored_directories}")
    typer.echo(f"- Movimientos planificados: {summary.planned_moves}")
    typer.echo(f"- Movimientos aplicados: {summary.applied_moves}")
    typer.echo(f"- Renombres por colisión: {summary.renamed_collisions}")
    typer.echo(f"- Saltados con error: {summary.skipped_errors}")
    typer.echo("- Totales por categoría:")
    if not summary.category_totals:
        typer.echo("  - (sin archivos)")
    for category, total in sorted(summary.category_totals.items()):
        typer.echo(f"  - {category}: {total}")


def print_rules(rules, *, use_rich: bool | None = None) -> None:  # noqa: ANN001
    if use_rich is None:
        use_rich = _should_use_rich()

    if use_rich:
        table = Table(title="Reglas incorporadas", box=box.SIMPLE)
        table.add_column("Destino", style="blue", no_wrap=True)
        table.add_column("Extensiones", style="magenta")
        table.add_column("Patrones", style="yellow")
        table.add_column("Descripción", style="dim")
        for rule in rules:
            table.add_row(
                rule.label,
                plain_join(rule.extensions, empty="(fallback)"),
                plain_join(rule.patterns),
                rule.description,
            )
        get_console().print(table)
        return

    typer.echo("Reglas incorporadas")
    for rule in rules:
        extensions = plain_join(rule.extensions, empty="(fallback)")
        patterns = plain_join(rule.patterns)
        typer.echo(f"- {rule.label}: {extensions} | patrones: {patterns}")
