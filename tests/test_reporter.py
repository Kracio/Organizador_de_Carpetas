from organizer_cli.models import FileEntry, MoveResult, PlannedMove, ScanResult
from organizer_cli.reporter import print_apply_progress, print_preview, print_rules
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
