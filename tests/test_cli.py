import os
from datetime import datetime

from typer.testing import CliRunner

import organizer_cli.cli as cli
from organizer_cli.cli import app


runner = CliRunner()


def _set_mtime(path, year: int, month: int, day: int = 15) -> None:
    timestamp = datetime(year, month, day, 12, 0, 0).timestamp()
    os.utime(path, (timestamp, timestamp))


def test_help_text() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "preview" in result.output
    assert "analyze" in result.output
    assert "review" in result.output
    assert "apply" in result.output


def test_no_args_prints_menu_hint() -> None:
    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "organizer menu" in result.output
    assert "preview PATH" in result.output
    assert "analyze PATH" in result.output
    assert "review PATH" in result.output


def test_apply_refuses_without_confirm(tmp_path) -> None:
    (tmp_path / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["apply", str(tmp_path)])

    assert result.exit_code == 1
    assert "--confirm" in result.output
    assert (tmp_path / "report.pdf").exists()
    assert not (tmp_path / "Documentos").exists()


def test_menu_exit_does_not_scan_or_mutate(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: tmp_path)
    (tmp_path / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["menu"], input="3\n")

    assert result.exit_code == 0
    assert "no se movió nada" in result.output
    assert (tmp_path / "report.pdf").exists()
    assert not (tmp_path / "Documentos").exists()


def test_menu_invalid_choice_reprompts_until_valid_exit(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n9\ntexto\n7\n")

    assert result.exit_code == 0
    assert result.output.count("Opción inválida") == 2
    assert "Elegí un número del menú" in result.output
    assert "Listo. No se movió nada." in result.output


def test_menu_preview_manual_path_does_not_mutate(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    (tmp_path / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n1\n7\n")

    assert result.exit_code == 0
    assert "Carpeta seleccionada" in result.output
    assert "PREVIEW - no se modifica nada" in result.output
    assert "APPLY - movimientos confirmados" not in result.output
    assert (tmp_path / "report.pdf").exists()
    assert not (tmp_path / "Documentos").exists()


def test_menu_preview_can_use_downloads_default(monkeypatch, tmp_path) -> None:
    home = tmp_path / "home"
    downloads = home / "Downloads"
    downloads.mkdir(parents=True)
    (downloads / "slides.pptx").write_text("ppt")
    monkeypatch.setattr(cli.Path, "home", lambda: home)

    result = runner.invoke(app, ["menu"], input="\n1\n7\n")

    assert result.exit_code == 0
    assert str(downloads) in result.output
    assert "Documentos" in result.output
    assert (downloads / "slides.pptx").exists()
    assert not (downloads / "Documentos").exists()


def test_menu_invalid_manual_path_can_cancel(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    missing = tmp_path / "missing"

    result = runner.invoke(app, ["menu"], input=f"{missing}\ncancel\n")

    assert result.exit_code == 0
    assert "La ruta no existe" in result.output
    assert "Cancelado: no se movió nada" in result.output


def test_menu_rules_show_outputs_destinations(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: tmp_path)

    result = runner.invoke(app, ["menu"], input="1\n6\n7\n")

    assert result.exit_code == 0
    assert "Reglas incorporadas" in result.output
    assert "Fotos/WhatsApp" in result.output
    assert "Documentos/PDF" in result.output


def test_menu_apply_cancel_after_preview_does_not_mutate(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    (tmp_path / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n2\n1\nn\n7\n")

    assert result.exit_code == 0
    assert "PREVIEW - no se modifica nada" in result.output
    assert "Cancelado: no se movió nada" in result.output
    assert (tmp_path / "report.pdf").exists()
    assert not (tmp_path / "Documentos").exists()


def test_menu_apply_confirm_shows_completion_and_can_exit(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    (tmp_path / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n2\n1\ny\n3\n")

    assert result.exit_code == 0
    assert result.output.index("PREVIEW - no se modifica nada") < result.output.index("APPLY - movimientos confirmados")
    assert "[OK] 1/1 report.pdf" in result.output
    assert "Organización completa" in result.output
    assert "Realizado" in result.output
    assert "¿Qué querés hacer ahora?" in result.output
    assert "Listo. Organización finalizada." in result.output
    assert not (tmp_path / "report.pdf").exists()
    assert (tmp_path / "Documentos" / "PDF" / "report.pdf").exists()


def test_menu_apply_confirm_can_continue_to_same_folder_menu(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    (tmp_path / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n2\n1\ny\n1\n7\n")

    assert result.exit_code == 0
    assert "Organización completa" in result.output
    assert "Carpeta seleccionada" in result.output
    assert result.output.rindex("Carpeta seleccionada") > result.output.index("Organización completa")
    assert not (tmp_path / "report.pdf").exists()
    assert (tmp_path / "Documentos" / "PDF" / "report.pdf").exists()


def test_menu_apply_completion_invalid_choice_reprompts(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    (tmp_path / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n2\n1\ny\nbad\n3\n")

    assert result.exit_code == 0
    assert "Organización completa" in result.output
    assert "Opción inválida. Elegí 1 para continuar" in result.output
    assert "Listo. Organización finalizada." in result.output


def test_menu_preview_returns_to_actions_and_can_organize_same_folder(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    (tmp_path / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n1\n2\n1\ny\n3\n")

    assert result.exit_code == 0
    assert result.output.count("PREVIEW - no se modifica nada") == 2
    assert result.output.index("PREVIEW - no se modifica nada") < result.output.index("APPLY - movimientos confirmados")
    assert not (tmp_path / "report.pdf").exists()
    assert (tmp_path / "Documentos" / "PDF" / "report.pdf").exists()


def test_menu_can_change_selected_folder(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (second / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{first}\n5\n{second}\n1\n7\n")

    assert result.exit_code == 0
    assert str(second) in result.output
    assert "Documentos/PDF" in result.output
    assert (second / "report.pdf").exists()
    assert not (second / "Documentos").exists()


def test_apply_confirm_shows_progress_and_summary(tmp_path) -> None:
    (tmp_path / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["apply", str(tmp_path), "--confirm"])

    assert result.exit_code == 0
    assert "APPLY - movimientos confirmados: 1 planificados" in result.output
    assert "[OK] 1/1 report.pdf" in result.output
    assert "Resumen" in result.output
    assert "Movimientos aplicados: 1" in result.output
    assert not (tmp_path / "report.pdf").exists()
    assert (tmp_path / "Documentos" / "PDF" / "report.pdf").exists()


def test_analyze_exports_report_and_does_not_mutate(tmp_path) -> None:
    file_path = tmp_path / "old-copy.pdf"
    file_path.write_text("pdf")
    _set_mtime(file_path, 2020, 1)
    folder = tmp_path / "existing"
    folder.mkdir()
    (folder / "nested.pdf").write_text("nested")

    result = runner.invoke(app, ["analyze", str(tmp_path), "--old-days", "180", "--large-mb", "1"])

    reports = list(tmp_path.glob("cleanup-report-*.txt"))
    assert result.exit_code == 0
    assert "CLEANUP REPORT - NO SE BORRÓ NADA" in result.output
    assert "Archivos viejos" in result.output
    assert "Reporte TXT:" in result.output
    assert len(reports) == 1
    assert file_path.exists()
    assert folder.exists()
    assert not (tmp_path / "Documentos").exists()
    assert "old-copy.pdf" in reports[0].read_text(encoding="utf-8")


def test_review_command_cancel_does_not_mutate_or_create_quarantine(tmp_path) -> None:
    suspicious = tmp_path / "report copy.pdf"
    suspicious.write_text("copy")

    result = runner.invoke(app, ["review", str(tmp_path)], input="2\nq\nn\n")

    assert result.exit_code == 0
    assert "No hay borrado permanente" in result.output
    assert "Sin selección: no se movió nada" in result.output
    assert suspicious.exists()
    assert not (tmp_path / "_cleanup_quarantine").exists()


def test_review_command_confirm_moves_selected_to_quarantine_only(tmp_path) -> None:
    suspicious = tmp_path / "report copy.pdf"
    normal = tmp_path / "normal.pdf"
    suspicious.write_text("copy")
    normal.write_text("normal")

    result = runner.invoke(app, ["review", str(tmp_path)], input="2\n1\ny\nn\n")

    quarantined = list((tmp_path / "_cleanup_quarantine").glob("*/*.pdf"))
    assert result.exit_code == 0
    assert "QUARANTINE PREVIEW" in result.output
    assert "QUARANTINE APPLY" in result.output
    assert not suspicious.exists()
    assert normal.exists()
    assert len(quarantined) == 1
    assert quarantined[0].name == "report copy.pdf"


def test_review_command_selection_denied_confirmation_does_not_quarantine(tmp_path) -> None:
    suspicious = tmp_path / "report copy.pdf"
    normal = tmp_path / "normal.pdf"
    suspicious.write_text("copy")
    normal.write_text("normal")

    result = runner.invoke(app, ["review", str(tmp_path)], input="2\n1\nn\nn\n")

    assert result.exit_code == 0
    assert "QUARANTINE PREVIEW" in result.output
    assert "Cancelado: no se movió nada" in result.output
    assert "QUARANTINE APPLY" not in result.output
    assert suspicious.exists()
    assert normal.exists()
    assert not (tmp_path / "_cleanup_quarantine").exists()


def test_review_invalid_selection_reprompts_then_cancels(tmp_path) -> None:
    suspicious = tmp_path / "report copy.pdf"
    suspicious.write_text("copy")

    result = runner.invoke(app, ["review", str(tmp_path)], input="2\n0\nbad\nnone\nn\n")

    assert result.exit_code == 0
    assert "Selección fuera de rango" in result.output
    assert "Selección inválida: bad" in result.output
    assert suspicious.exists()
    assert not (tmp_path / "_cleanup_quarantine").exists()


def test_review_continue_loop_allows_multiple_categories(tmp_path) -> None:
    suspicious = tmp_path / "report copy.pdf"
    duplicate_extra = tmp_path / "b.txt"
    suspicious.write_text("copy")
    (tmp_path / "a.txt").write_text("same")
    duplicate_extra.write_text("same")

    result = runner.invoke(app, ["review", str(tmp_path)], input="2\n1\ny\ny\n1\n1\ny\nn\n")

    quarantined = {path.name for path in (tmp_path / "_cleanup_quarantine").glob("*/*")}
    assert result.exit_code == 0
    assert result.output.count("¿Querés revisar más hallazgos?") == 2
    assert not suspicious.exists()
    assert not duplicate_extra.exists()
    assert (tmp_path / "a.txt").exists()
    assert {"report copy.pdf", "b.txt"} <= quarantined


def test_review_quarantine_failure_keeps_failed_source_and_continues(monkeypatch, tmp_path) -> None:
    blocked = tmp_path / "blocked copy.pdf"
    ok = tmp_path / "ok copy.pdf"
    blocked.write_text("blocked")
    ok.write_text("ok")

    import organizer_cli.mover as mover

    original_move = mover.shutil.move

    def move_with_one_failure(source: str, destination: str) -> str:
        if source.endswith("blocked copy.pdf"):
            raise PermissionError("blocked for test")
        return original_move(source, destination)

    monkeypatch.setattr(mover.shutil, "move", move_with_one_failure)

    result = runner.invoke(app, ["review", str(tmp_path)], input="2\nall\ny\nn\n")

    assert result.exit_code == 0
    assert "[SKIP] 1/2 blocked copy.pdf" in result.output
    assert "reason: blocked for test" in result.output
    assert "[OK] 2/2 ok copy.pdf" in result.output
    assert blocked.exists()
    assert not ok.exists()
    assert len(list((tmp_path / "_cleanup_quarantine").glob("*/ok copy.pdf"))) == 1


def test_menu_analyze_review_confirm_moves_only_selected(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    suspicious = tmp_path / "report copy.pdf"
    normal = tmp_path / "normal.pdf"
    suspicious.write_text("copy")
    normal.write_text("normal")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n3\ny\ny\n2\n1\ny\nn\n7\n")

    assert result.exit_code == 0
    assert "¿Querés revisar hallazgos" in result.output
    assert not suspicious.exists()
    assert normal.exists()
    assert not (tmp_path / "Documentos").exists()
    assert len(list((tmp_path / "_cleanup_quarantine").glob("*/*.pdf"))) == 1


def test_analyze_output_can_be_explicit_file(tmp_path) -> None:
    (tmp_path / "backup.txt").write_text("x")
    output = tmp_path / "custom-report.txt"

    result = runner.invoke(app, ["analyze", str(tmp_path), "--output", str(output)])

    assert result.exit_code == 0
    assert str(output.resolve()) in result.output
    assert output.exists()


def test_menu_analyze_returns_to_actions_without_mutation(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    report = tmp_path / "backup.pdf"
    report.write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n3\ny\nn\n7\n")

    assert result.exit_code == 0
    assert "Analyze selected folder" in result.output
    assert "¿Usar umbrales por defecto? [Y/n]" in result.output
    assert "CLEANUP REPORT - NO SE BORRÓ NADA" in result.output
    assert report.exists()
    assert not (tmp_path / "Documentos").exists()
    assert len(list(tmp_path.glob("cleanup-report-*.txt"))) == 1


def test_menu_analyze_custom_thresholds_are_used(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    report = tmp_path / "backup.pdf"
    report.write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n3\nn\n30\n5\n45\ny\nn\n7\n")

    reports = list(tmp_path.glob("cleanup-report-*.txt"))
    assert result.exit_code == 0
    assert "Días para considerar un archivo viejo" in result.output
    assert "MB para considerar un archivo pesado" in result.output
    assert "¿Analizar también subcarpetas? [y/N]" in result.output
    assert len(reports) == 1
    report_text = reports[0].read_text(encoding="utf-8")
    assert "Modo recursivo: sí" in report_text
    assert "Umbral archivos viejos: 30 días" in report_text
    assert "Umbral archivos pesados: 5 MB" in report_text
    assert "Umbral instaladores/comprimidos viejos: 45 días" in report_text
    assert report.exists()
    assert not (tmp_path / "Documentos").exists()


def test_menu_analyze_invalid_threshold_reprompts(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    (tmp_path / "backup.pdf").write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n3\nn\nabc\n0\n10\n1\n20\nn\nn\n7\n")

    reports = list(tmp_path.glob("cleanup-report-*.txt"))
    assert result.exit_code == 0
    assert result.output.count("Valor inválido") == 2
    assert len(reports) == 1
    report_text = reports[0].read_text(encoding="utf-8")
    assert "Umbral archivos viejos: 10 días" in report_text
    assert "Umbral archivos pesados: 1 MB" in report_text
    assert "Umbral instaladores/comprimidos viejos: 20 días" in report_text


def test_preview_date_mode_year_month_shows_date_path_and_does_not_mutate(tmp_path) -> None:
    report = tmp_path / "report.pdf"
    report.write_text("pdf")
    _set_mtime(report, 2025, 6)

    result = runner.invoke(app, ["preview", str(tmp_path), "--date-mode", "year-month"])

    assert result.exit_code == 0
    assert "Documentos/PDF/2025/06-Junio/report.pdf" in result.output
    assert report.exists()
    assert not (tmp_path / "Documentos").exists()


def test_apply_date_mode_year_month_without_confirm_refuses_and_does_not_mutate(tmp_path) -> None:
    report = tmp_path / "report.pdf"
    report.write_text("pdf")
    _set_mtime(report, 2025, 6)

    result = runner.invoke(app, ["apply", str(tmp_path), "--date-mode", "year-month"])

    assert result.exit_code == 1
    assert "--confirm" in result.output
    assert report.exists()
    assert not (tmp_path / "Documentos").exists()


def test_apply_confirm_date_mode_year_moves_to_year_destination(tmp_path) -> None:
    report = tmp_path / "report.pdf"
    report.write_text("pdf")
    _set_mtime(report, 2025, 6)

    result = runner.invoke(app, ["apply", str(tmp_path), "--confirm", "--date-mode", "year"])

    assert result.exit_code == 0
    assert not report.exists()
    assert (tmp_path / "Documentos" / "PDF" / "2025" / "report.pdf").exists()


def test_menu_preview_uses_no_date_mode_and_does_not_prompt_or_mutate(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    report = tmp_path / "report.pdf"
    report.write_text("pdf")
    _set_mtime(report, 2025, 6)

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n1\n7\n")

    assert result.exit_code == 0
    assert "¿Cómo querés organizar por fecha?" not in result.output
    assert "Documentos/PDF/report.pdf" in result.output
    assert "Documentos/PDF/2025" not in result.output
    assert "APPLY - movimientos confirmados" not in result.output
    assert report.exists()
    assert not (tmp_path / "Documentos").exists()


def test_menu_organize_uses_previewed_date_mode_for_apply(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    report = tmp_path / "report.pdf"
    report.write_text("pdf")
    _set_mtime(report, 2025, 6)

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n2\n2\ny\n3\n")

    destination = tmp_path / "Documentos" / "PDF" / "2025" / "report.pdf"

    assert result.exit_code == 0
    assert "¿Cómo querés organizar por fecha?" in result.output
    assert "Documentos/PDF/2025/report.pdf" in result.output
    assert result.output.index("Documentos/PDF/2025/report.pdf") < result.output.index("APPLY - movimientos confirmados")
    assert not report.exists()
    assert destination.exists()


def test_apply_confirm_reports_error_and_continues(monkeypatch, tmp_path) -> None:
    blocked = tmp_path / "blocked.pdf"
    ok = tmp_path / "ok.pdf"
    blocked.write_text("blocked")
    ok.write_text("ok")

    import organizer_cli.mover as mover

    original_move = mover.shutil.move

    def move_with_one_failure(source: str, destination: str) -> str:
        if source.endswith("blocked.pdf"):
            raise PermissionError("blocked for test")
        return original_move(source, destination)

    monkeypatch.setattr(mover.shutil, "move", move_with_one_failure)

    result = runner.invoke(app, ["apply", str(tmp_path), "--confirm"])

    assert result.exit_code == 0
    assert "[SKIP] 1/2 blocked.pdf" in result.output
    assert "reason: blocked for test" in result.output
    assert "[OK] 2/2 ok.pdf" in result.output
    assert blocked.exists()
    assert (tmp_path / "Documentos" / "PDF" / "ok.pdf").exists()


def test_apply_confirm_reports_collision_rename(tmp_path) -> None:
    (tmp_path / "photo.jpg").write_text("source")
    destination = tmp_path / "Fotos" / "General"
    destination.mkdir(parents=True)
    (destination / "photo.jpg").write_text("existing")

    result = runner.invoke(app, ["apply", str(tmp_path), "--confirm"])

    assert result.exit_code == 0
    assert "[OK] 1/1 photo.jpg" in result.output
    assert "renombrado por colisión" in result.output
    assert (destination / "photo.jpg").read_text() == "existing"
    assert (destination / "photo (1).jpg").read_text() == "source"


def test_preview_does_not_mutate(tmp_path) -> None:
    (tmp_path / "report.pdf").write_text("pdf")
    folder = tmp_path / "existing"
    folder.mkdir()
    (folder / "nested.pdf").write_text("nested")

    result = runner.invoke(app, ["preview", str(tmp_path)])

    assert result.exit_code == 0
    assert "PREVIEW" in result.output
    assert "APPLY - movimientos confirmados" not in result.output
    assert "Documentos" in result.output
    assert (tmp_path / "report.pdf").exists()
    assert not (tmp_path / "Documentos").exists()


def test_rules_show_outputs_destinations() -> None:
    result = runner.invoke(app, ["rules", "show"])

    assert result.exit_code == 0
    assert "Fotos/WhatsApp" in result.output
    assert "Documentos/PDF" in result.output
    assert "Otros" in result.output
