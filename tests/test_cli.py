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
    assert "apply" in result.output


def test_no_args_prints_menu_hint() -> None:
    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "organizer menu" in result.output
    assert "preview PATH" in result.output


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

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n9\ntexto\n5\n")

    assert result.exit_code == 0
    assert result.output.count("Opción inválida") == 2
    assert "Elegí un número del menú" in result.output
    assert "Listo. No se movió nada." in result.output


def test_menu_preview_manual_path_does_not_mutate(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    (tmp_path / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n1\n5\n")

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

    result = runner.invoke(app, ["menu"], input="\n1\n5\n")

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

    result = runner.invoke(app, ["menu"], input="1\n4\n5\n")

    assert result.exit_code == 0
    assert "Reglas incorporadas" in result.output
    assert "Fotos/WhatsApp" in result.output
    assert "Documentos/PDF" in result.output


def test_menu_apply_cancel_after_preview_does_not_mutate(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "_default_downloads", lambda: None)
    (tmp_path / "report.pdf").write_text("pdf")

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n2\n1\nn\n5\n")

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

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n2\n1\ny\n1\n5\n")

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

    result = runner.invoke(app, ["menu"], input=f"{first}\n3\n{second}\n1\n5\n")

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

    result = runner.invoke(app, ["menu"], input=f"{tmp_path}\n1\n5\n")

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
