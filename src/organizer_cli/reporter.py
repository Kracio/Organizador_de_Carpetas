from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import typer
from rich import box
from rich.panel import Panel
from rich.table import Table

from .branding import get_console, plain_join, should_use_rich
from .models import CleanupReport, CleanupReviewItem, MoveResult, PlannedMove, RunSummary, ScanResult

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


def print_cleanup_summary(report: CleanupReport, *, report_path: Path | None = None, use_rich: bool | None = None) -> None:
    """Print a cleanup report summary without implying any file mutation."""

    if use_rich is None:
        use_rich = _should_use_rich()

    totals = report.category_totals
    distribution = _cleanup_file_distribution(report)
    if use_rich:
        get_console().print(
            Panel(
                "Reporte solamente: NO SE BORRÓ NADA, no se movió nada y no se renombró nada.",
                title="CLEANUP REPORT",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )
        dashboard = Table(title="Dashboard rápido", box=box.SIMPLE_HEAVY)
        dashboard.add_column("Archivos", style="cyan")
        dashboard.add_column("Viejos", justify="right", style="bold yellow")
        dashboard.add_column("Pesados", justify="right", style="bold magenta")
        dashboard.add_column("ZIP/inst.", justify="right", style="bold blue")
        dashboard.add_column("Sospechosos", justify="right", style="bold red")
        dashboard.add_column("Duplicados", justify="right", style="bold green")
        dashboard.add_row(
            str(len(report.files)),
            str(totals.get("old", 0)),
            str(totals.get("large", 0)),
            str(totals.get("old_archive_installer", 0)),
            str(totals.get("copy_temp_name", 0)),
            str(totals.get("exact_duplicates", 0)),
        )
        get_console().print(dashboard)

        context = Table(title="Contexto del análisis", box=box.SIMPLE)
        context.add_column("Métrica", style="dim")
        context.add_column("Total", justify="right", style="bold")
        context.add_row("Carpetas ignoradas", str(report.ignored_directories))
        context.add_row("Modo recursivo", "sí" if report.options.recursive else "no")
        context.add_row("Archivos saltados", str(len(report.skipped_files)))
        get_console().print(context)

        categories = Table(title="Distribución por tipo", box=box.SIMPLE)
        categories.add_column("Grupo", style="blue")
        categories.add_column("Total", justify="right", style="bold")
        for key, label in _cleanup_distribution_labels():
            categories.add_row(label, str(distribution.get(key, 0)))
        get_console().print(categories)

        findings = Table(title="Hallazgos por categoría", box=box.SIMPLE)
        findings.add_column("Categoría", style="blue")
        findings.add_column("Total", justify="right", style="bold")
        for key, label in _cleanup_category_labels():
            findings.add_row(label, str(totals.get(key, 0)))
        get_console().print(findings)
        if report_path is not None:
            get_console().print(f"[green]Reporte TXT:[/] {report_path}")
        return

    typer.echo("CLEANUP REPORT - NO SE BORRÓ NADA")
    typer.echo("Reporte solamente: no se movió nada y no se renombró nada.")
    typer.echo("")
    typer.echo("Dashboard rápido")
    _print_plain_dashboard(report)
    typer.echo("")
    typer.echo("Contexto del análisis")
    typer.echo(f"- Archivos analizados: {len(report.files)}")
    typer.echo(f"- Carpetas ignoradas: {report.ignored_directories}")
    typer.echo(f"- Modo recursivo: {'sí' if report.options.recursive else 'no'}")
    typer.echo(f"- Archivos saltados: {len(report.skipped_files)}")
    typer.echo("- Distribución por tipo:")
    for key, label in _cleanup_distribution_labels():
        typer.echo(f"  - {label}: {distribution.get(key, 0)}")
    typer.echo("- Hallazgos por categoría:")
    for key, label in _cleanup_category_labels():
        typer.echo(f"  - {label}: {totals.get(key, 0)}")
    if report_path is not None:
        typer.echo(f"Reporte TXT: {report_path}")


def render_cleanup_report_txt(report: CleanupReport) -> str:
    """Render a deterministic TXT cleanup report."""

    totals = report.category_totals
    distribution = _cleanup_file_distribution(report)
    lines: list[str] = [
        "Organizador de Carpetas - Cleanup Report",
        "NO SE BORRÓ NADA. NO SE MOVIÓ NADA. NO SE RENOMBRÓ NADA.",
        "",
        f"Carpeta analizada: {report.root}",
        f"Generado: {report.generated_at:%Y-%m-%d %H:%M:%S}",
        f"Modo recursivo: {'sí' if report.options.recursive else 'no'}",
        f"Umbral archivos viejos: {report.options.old_days} días",
        f"Umbral archivos pesados: {report.options.large_mb} MB",
        f"Umbral instaladores/comprimidos viejos: {report.options.archive_days} días",
        "",
        "Resumen",
        f"- Archivos analizados: {len(report.files)}",
        f"- Carpetas ignoradas: {report.ignored_directories}",
        f"- Archivos saltados: {len(report.skipped_files)}",
        "- Distribución por tipo:",
    ]
    for key, label in _cleanup_distribution_labels():
        lines.append(f"  - {label}: {distribution.get(key, 0)}")

    lines.extend([
        "- Hallazgos por categoría:",
    ])
    for key, label in _cleanup_category_labels():
        lines.append(f"  - {label}: {totals.get(key, 0)}")

    lines.extend(["", "Detalle de hallazgos"])
    if report.findings:
        for finding in sorted(report.findings, key=lambda item: (item.category, item.relative_path.as_posix().lower())):
            lines.append(f"- [{finding.label}] {finding.relative_path.as_posix()} — {finding.reason}")
    else:
        lines.append("- Sin hallazgos por umbrales o nombres sospechosos.")

    lines.extend(["", "Duplicados exactos"])
    if report.duplicate_groups:
        for index, group in enumerate(report.duplicate_groups, start=1):
            lines.append(f"- Grupo {index}: {len(group.files)} archivos, {group.size_bytes} bytes, sha256={group.sha256}")
            for file in group.files:
                lines.append(f"  - {file.relative_path.as_posix()}")
    else:
        lines.append("- No se detectaron duplicados exactos.")

    lines.extend(["", "Archivos saltados"])
    if report.skipped_files:
        for skipped in report.skipped_files:
            lines.append(f"- {skipped.relative_path.as_posix()}: {skipped.reason}")
    else:
        lines.append("- Ninguno.")

    lines.extend(["", "Recordatorio: este reporte es informativo. Revisá manualmente antes de borrar cualquier archivo.", ""])
    return "\n".join(lines)


def write_cleanup_report_txt(report: CleanupReport, output: Path | None = None) -> Path:
    """Write the TXT report; output may be a .txt path or a destination directory."""

    if output is None:
        destination = report.root / _default_cleanup_report_name(report)
    else:
        output = output.expanduser()
        if output.suffix.lower() == ".txt":
            destination = output
        else:
            destination = output / _default_cleanup_report_name(report)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_cleanup_report_txt(report), encoding="utf-8")
    return destination.resolve()


def print_review_items(items: tuple[CleanupReviewItem, ...], *, title: str = "Candidatos para cuarentena", use_rich: bool | None = None) -> None:
    """Print numbered review candidates in a CMD-friendly format."""

    if use_rich is None:
        use_rich = _should_use_rich()

    if not items:
        typer.echo("No hay candidatos para revisar en esta categoría.")
        return

    if use_rich:
        table = Table(title=title, box=box.SIMPLE)
        table.add_column("#", justify="right", style="bold cyan")
        table.add_column("Archivo", style="bold")
        table.add_column("Categoría", style="blue")
        table.add_column("Motivo", style="yellow")
        for item in items:
            table.add_row(str(item.index), item.relative_path.as_posix(), item.label, item.reason)
        get_console().print(table)
        return

    typer.echo(title)
    for item in items:
        suffix = ""
        if item.keep_representative is not None:
            suffix = f" | conservar: {item.keep_representative.as_posix()}"
        typer.echo(f"{item.index}. {item.relative_path.as_posix()} [{item.label}] - {item.reason}{suffix}")


def print_quarantine_preview(plan: tuple[PlannedMove, ...], *, use_rich: bool | None = None) -> None:
    """Show quarantine moves before confirmation; does not mutate files."""

    if use_rich is None:
        use_rich = _should_use_rich()

    if not plan:
        typer.echo("No hay movimientos de cuarentena para previsualizar.")
        return

    if use_rich:
        get_console().print(
            Panel(
                "Vista previa solamente: todavía NO se movió nada. Confirmá explícitamente para mandar a cuarentena.",
                title="QUARANTINE PREVIEW",
                border_style="yellow",
                box=box.ROUNDED,
            )
        )
    else:
        typer.echo("QUARANTINE PREVIEW - todavía no se movió nada")

    for move in plan:
        suffix = " (renombrado por colisión)" if move.collision_renamed else ""
        typer.echo(f"- {move.source} -> {move.destination}{suffix}")


def print_quarantine_results(results: tuple[MoveResult, ...]) -> None:
    """Show quarantine action results after confirmed moves."""

    typer.echo("QUARANTINE APPLY - movimientos confirmados")
    for index, result in enumerate(results, start=1):
        _print_move_result(result, index, len(results))
    applied = sum(1 for result in results if result.applied)
    skipped = len(results) - applied
    typer.echo("")
    typer.echo("Resumen cuarentena")
    typer.echo(f"- Movidos a cuarentena: {applied}")
    typer.echo(f"- Saltados con error: {skipped}")


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
                move.destination.relative_to(move.source.parent).as_posix(),
                move.category,
                "renombrado por colisión" if move.collision_renamed else "",
            )
        get_console().print(table)
        return

    for move in plan:
        suffix = " (renombrado por colisión)" if move.collision_renamed else ""
        relative_destination = move.destination.relative_to(move.source.parent).as_posix()
        typer.echo(f"- {move.source.name} -> {relative_destination} [{move.category}]{suffix}")


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


def _default_cleanup_report_name(report: CleanupReport) -> str:
    return f"cleanup-report-{report.generated_at:%Y%m%d-%H%M%S}.txt"


def _cleanup_category_labels() -> tuple[tuple[str, str], ...]:
    return (
        ("old", "Archivos viejos"),
        ("large", "Archivos pesados"),
        ("old_archive_installer", "Instaladores/comprimidos viejos"),
        ("copy_temp_name", "Copias/temp/nombres sospechosos"),
        ("exact_duplicates", "Grupos duplicados exactos"),
    )


def _cleanup_distribution_labels() -> tuple[tuple[str, str], ...]:
    return (
        ("documents", "Documentos"),
        ("images", "Imágenes"),
        ("media", "Media"),
        ("archives", "Comprimidos"),
        ("installers", "Instaladores"),
        ("others", "Otros"),
    )


def _cleanup_file_distribution(report: CleanupReport) -> dict[str, int]:
    totals = {key: 0 for key, _label in _cleanup_distribution_labels()}
    for file in report.files:
        totals[_cleanup_distribution_key(file.suffix)] += 1
    return totals


def _cleanup_distribution_key(suffix: str) -> str:
    suffix = suffix.lower()
    if suffix in {".pdf", ".doc", ".docx", ".odt", ".ppt", ".pptx", ".odp", ".xls", ".xlsx", ".csv", ".ods", ".txt", ".rtf"}:
        return "documents"
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".heic", ".svg"}:
        return "images"
    if suffix in {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm", ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}:
        return "media"
    if suffix in {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"}:
        return "archives"
    if suffix in {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk"}:
        return "installers"
    return "others"


def _print_plain_dashboard(report: CleanupReport) -> None:
    totals = report.category_totals
    rows = (
        ("Archivos analizados", len(report.files)),
        ("Archivos viejos", totals.get("old", 0)),
        ("Archivos pesados", totals.get("large", 0)),
        ("ZIP/instaladores viejos", totals.get("old_archive_installer", 0)),
        ("Nombres sospechosos", totals.get("copy_temp_name", 0)),
        ("Grupos duplicados", totals.get("exact_duplicates", 0)),
    )
    width = max(len(label) for label, _value in rows)
    typer.echo("+" + "-" * (width + 2) + "+-------+")
    for label, value in rows:
        typer.echo(f"| {label.ljust(width)} | {str(value).rjust(5)} |")
    typer.echo("+" + "-" * (width + 2) + "+-------+")


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
