from datetime import datetime
from pathlib import Path

from organizer_cli.models import AnalyzedFile, CleanupFinding, CleanupOptions, CleanupReport, CleanupReviewItem, DuplicateGroup, FileEntry, MoveResult, PlannedMove, ScanResult
from organizer_cli.reporter import print_apply_progress, print_cleanup_summary, print_preview, print_quarantine_preview, print_quarantine_results, print_review_items, print_rules, render_cleanup_report_txt, write_cleanup_report_txt
import organizer_cli.reporter as reporter
from organizer_cli.rules import iter_rules


def test_print_apply_progress_handles_empty_plan(capsys, tmp_path) -> None:
    scan = ScanResult(root=tmp_path, files=())

    summary = print_apply_progress(scan, (), (), use_rich=False)

    output = capsys.readouterr().out
    assert "APPLY - movimientos confirmados: 0 planificados" in output
    assert "Resumen" in output
    assert summary.planned_moves == 0
    assert summary.applied_moves == 0


def test_print_apply_progress_reports_success(capsys, tmp_path) -> None:
    source = tmp_path / "report.pdf"
    destination = tmp_path / "Documentos" / "PDF" / "report.pdf"
    move = PlannedMove(source, destination, "Documentos/PDF")
    scan = ScanResult(root=tmp_path, files=(FileEntry(source, source.name, source.suffix),))

    summary = print_apply_progress(scan, (move,), (MoveResult(move, applied=True),), use_rich=False)

    output = capsys.readouterr().out
    assert "[OK] 1/1 report.pdf" in output
    assert "Resumen" in output
    assert summary.applied_moves == 1


def test_print_apply_progress_reports_collision_rename(capsys, tmp_path) -> None:
    source = tmp_path / "photo.jpg"
    destination = tmp_path / "Fotos" / "General" / "photo (1).jpg"
    move = PlannedMove(source, destination, "Fotos/General", collision_renamed=True)
    scan = ScanResult(root=tmp_path, files=(FileEntry(source, source.name, source.suffix),))

    print_apply_progress(scan, (move,), (MoveResult(move, applied=True),), use_rich=False)

    output = capsys.readouterr().out
    assert "[OK] 1/1 photo.jpg" in output
    assert "renombrado por colisión" in output


def test_print_apply_progress_reports_error_reason(capsys, tmp_path) -> None:
    source = tmp_path / "blocked.pdf"
    destination = tmp_path / "Documentos" / "PDF" / "blocked.pdf"
    move = PlannedMove(source, destination, "Documentos/PDF")
    scan = ScanResult(root=tmp_path, files=(FileEntry(source, source.name, source.suffix),))

    summary = print_apply_progress(
        scan,
        (move,),
        (MoveResult(move, applied=False, error="permission denied"),),
        use_rich=False,
    )

    output = capsys.readouterr().out
    assert "[SKIP] 1/1 blocked.pdf" in output
    assert "reason: permission denied" in output
    assert summary.skipped_errors == 1


def test_print_apply_progress_plain_mode_does_not_use_rich(monkeypatch, capsys, tmp_path) -> None:
    source = tmp_path / "report.pdf"
    destination = tmp_path / "Documentos" / "PDF" / "report.pdf"
    move = PlannedMove(source, destination, "Documentos/PDF")
    scan = ScanResult(root=tmp_path, files=(FileEntry(source, source.name, source.suffix),))

    def fail_if_used(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("Rich Progress should not be used in plain mode")

    monkeypatch.setattr(reporter, "Progress", fail_if_used)

    print_apply_progress(scan, (move,), (MoveResult(move, applied=True),), use_rich=False)

    output = capsys.readouterr().out
    assert "APPLY - movimientos confirmados: 1 planificados" in output
    assert "[OK] 1/1 report.pdf" in output
    assert "Resumen" in output


def test_print_preview_plain_keeps_safety_copy(capsys, tmp_path) -> None:
    source = tmp_path / "report.pdf"
    destination = tmp_path / "Documentos" / "PDF" / "report.pdf"
    move = PlannedMove(source, destination, "Documentos/PDF")
    scan = ScanResult(root=tmp_path, files=(FileEntry(source, source.name, source.suffix),))

    summary = print_preview(scan, (move,), use_rich=False)

    output = capsys.readouterr().out
    assert "PREVIEW - no se modifica nada" in output
    assert "report.pdf" in output
    assert "Documentos/PDF" in output
    assert "Movimientos planificados: 1" in output
    assert summary.planned_moves == 1


def test_print_rules_plain_outputs_destinations_and_patterns(capsys) -> None:
    print_rules(iter_rules(), use_rich=False)

    output = capsys.readouterr().out
    assert "Reglas incorporadas" in output
    assert "Fotos/WhatsApp" in output
    assert "Documentos/PDF" in output
    assert "patrones:" in output


def test_print_cleanup_summary_plain_includes_totals_and_report_path(capsys, tmp_path) -> None:
    analyzed = AnalyzedFile(tmp_path / "old.pdf", Path("old.pdf"), "old.pdf", ".pdf", 3, datetime(2020, 1, 1))
    report = CleanupReport(
        root=tmp_path,
        options=CleanupOptions(now=datetime(2026, 6, 10, 12, 0, 0)),
        generated_at=datetime(2026, 6, 10, 12, 0, 0),
        files=(analyzed,),
        ignored_directories=1,
        findings=(CleanupFinding("old", "Archivo viejo", analyzed.path, analyzed.relative_path, "test"),),
        duplicate_groups=(),
    )
    report_path = tmp_path / "cleanup-report.txt"

    print_cleanup_summary(report, report_path=report_path, use_rich=False)

    output = capsys.readouterr().out
    assert "CLEANUP REPORT - NO SE BORRÓ NADA" in output
    assert "Reporte solamente: no se movió nada y no se renombró nada." in output
    assert "Dashboard rápido" in output
    assert "Archivos analizados: 1" in output
    assert "Distribución por tipo" in output
    assert "Documentos: 1" in output
    assert "Carpetas ignoradas: 1" in output
    assert "Archivos viejos: 1" in output
    assert f"Reporte TXT: {report_path}" in output


def test_print_review_items_plain_shows_numbered_candidates(capsys, tmp_path) -> None:
    item = CleanupReviewItem(
        index=1,
        source=tmp_path / "report copy.pdf",
        relative_path=Path("report copy.pdf"),
        category="suspicious",
        label="Nombre sospechoso",
        reason="parece copia",
    )

    print_review_items((item,), use_rich=False)

    output = capsys.readouterr().out
    assert "Candidatos para cuarentena" in output
    assert "1. report copy.pdf" in output
    assert "parece copia" in output


def test_print_quarantine_preview_and_results_plain(capsys, tmp_path) -> None:
    source = tmp_path / "report copy.pdf"
    destination = tmp_path / "_cleanup_quarantine" / "2026-06-10_120000" / "report copy.pdf"
    move = PlannedMove(source, destination, "quarantine/suspicious")

    print_quarantine_preview((move,), use_rich=False)
    print_quarantine_results((MoveResult(move, applied=True),))

    output = capsys.readouterr().out
    assert "QUARANTINE PREVIEW - todavía no se movió nada" in output
    assert "QUARANTINE APPLY - movimientos confirmados" in output
    assert "Movidos a cuarentena: 1" in output


def test_print_cleanup_summary_plain_dashboard_includes_key_findings(capsys, tmp_path) -> None:
    old = AnalyzedFile(tmp_path / "old.pdf", Path("old.pdf"), "old.pdf", ".pdf", 3, datetime(2020, 1, 1))
    large = AnalyzedFile(tmp_path / "movie.mp4", Path("movie.mp4"), "movie.mp4", ".mp4", 150_000_000, datetime(2026, 1, 1))
    archive = AnalyzedFile(tmp_path / "setup.zip", Path("setup.zip"), "setup.zip", ".zip", 4, datetime(2020, 1, 1))
    report = CleanupReport(
        root=tmp_path,
        options=CleanupOptions(now=datetime(2026, 6, 10, 12, 0, 0)),
        generated_at=datetime(2026, 6, 10, 12, 0, 0),
        files=(old, large, archive),
        ignored_directories=0,
        findings=(
            CleanupFinding("old", "Archivo viejo", old.path, old.relative_path, "test"),
            CleanupFinding("large", "Archivo pesado", large.path, large.relative_path, "test"),
            CleanupFinding("old_archive_installer", "Instalador/comprimido viejo", archive.path, archive.relative_path, "test"),
            CleanupFinding("copy_temp_name", "Nombre sospechoso", old.path, old.relative_path, "test"),
        ),
        duplicate_groups=(DuplicateGroup("abc123", 4, (old, archive)),),
    )

    print_cleanup_summary(report, use_rich=False)

    output = capsys.readouterr().out
    assert "Dashboard rápido" in output
    assert "Archivos analizados" in output
    assert "Archivos pesados" in output
    assert "ZIP/instaladores viejos" in output
    assert "Nombres sospechosos" in output
    assert "Grupos duplicados" in output
    assert "Media: 1" in output
    assert "Comprimidos: 1" in output


def test_render_cleanup_report_txt_has_safety_sections_and_duplicates(tmp_path) -> None:
    first = AnalyzedFile(tmp_path / "a.txt", Path("a.txt"), "a.txt", ".txt", 4, datetime(2026, 1, 1))
    second = AnalyzedFile(tmp_path / "b.txt", Path("b.txt"), "b.txt", ".txt", 4, datetime(2026, 1, 1))
    report = CleanupReport(
        root=tmp_path,
        options=CleanupOptions(old_days=90, large_mb=5, archive_days=30, recursive=True, now=datetime(2026, 6, 10, 12, 0, 0)),
        generated_at=datetime(2026, 6, 10, 12, 0, 0),
        files=(first, second),
        ignored_directories=0,
        findings=(CleanupFinding("copy_temp_name", "Nombre sospechoso", first.path, first.relative_path, "test"),),
        duplicate_groups=(DuplicateGroup("abc123", 4, (first, second)),),
    )

    text = render_cleanup_report_txt(report)

    assert "NO SE BORRÓ NADA" in text
    assert "Modo recursivo: sí" in text
    assert "Umbral archivos viejos: 90 días" in text
    assert "Distribución por tipo" in text
    assert "Documentos: 2" in text
    assert "[Nombre sospechoso]" in text
    assert "sha256=abc123" in text
    assert "a.txt" in text
    assert "b.txt" in text


def test_write_cleanup_report_txt_supports_directory_and_file_output(tmp_path) -> None:
    report = CleanupReport(
        root=tmp_path,
        options=CleanupOptions(now=datetime(2026, 6, 10, 12, 0, 0)),
        generated_at=datetime(2026, 6, 10, 12, 0, 0),
        files=(),
        ignored_directories=0,
        findings=(),
        duplicate_groups=(),
    )

    default_path = write_cleanup_report_txt(report)
    explicit_file = write_cleanup_report_txt(report, tmp_path / "reports" / "custom.txt")

    assert default_path.name == "cleanup-report-20260610-120000.txt"
    assert default_path.exists()
    assert explicit_file.name == "custom.txt"
    assert explicit_file.exists()
