import os
from datetime import datetime

from organizer_cli.date_organization import DateMode
from organizer_cli.models import FileEntry, ScanResult
from organizer_cli.planner import build_plan
from organizer_cli.scanner import scan_root


def _set_mtime(path, year: int, month: int, day: int = 15) -> None:
    timestamp = datetime(year, month, day, 12, 0, 0).timestamp()
    os.utime(path, (timestamp, timestamp))


def test_plan_default_date_mode_keeps_existing_destination_shape(tmp_path) -> None:
    (tmp_path / "report.pdf").write_text("pdf")

    plan = build_plan(scan_root(tmp_path))

    assert plan[0].destination == tmp_path / "Documentos" / "PDF" / "report.pdf"


def test_plan_year_date_mode_uses_file_mtime(tmp_path) -> None:
    report = tmp_path / "report.pdf"
    report.write_text("pdf")
    _set_mtime(report, 2025, 6)

    plan = build_plan(scan_root(tmp_path), date_mode=DateMode.YEAR)

    assert plan[0].destination == tmp_path / "Documentos" / "PDF" / "2025" / "report.pdf"


def test_plan_year_month_date_mode_uses_spanish_month_folder(tmp_path) -> None:
    report = tmp_path / "report.pdf"
    report.write_text("pdf")
    _set_mtime(report, 2025, 6)

    plan = build_plan(scan_root(tmp_path), date_mode=DateMode.YEAR_MONTH)

    assert plan[0].destination == tmp_path / "Documentos" / "PDF" / "2025" / "06-Junio" / "report.pdf"


def test_plan_year_month_preserves_non_document_base_parts(tmp_path) -> None:
    movie = tmp_path / "movie.mp4"
    movie.write_text("video")
    _set_mtime(movie, 2025, 6)

    plan = build_plan(scan_root(tmp_path), date_mode=DateMode.YEAR_MONTH)

    assert plan[0].destination == tmp_path / "Multimedia" / "Videos" / "2025" / "06-Junio" / "movie.mp4"


def test_plan_renames_existing_destination_collision(tmp_path) -> None:
    (tmp_path / "photo.jpg").write_text("source")
    destination = tmp_path / "Fotos" / "General"
    destination.mkdir(parents=True)
    (destination / "photo.jpg").write_text("existing")

    plan = build_plan(scan_root(tmp_path))

    assert plan[0].destination == destination / "photo (1).jpg"
    assert plan[0].collision_renamed is True


def test_plan_renames_existing_destination_collision_inside_date_folder(tmp_path) -> None:
    report = tmp_path / "report.pdf"
    report.write_text("source")
    _set_mtime(report, 2025, 6)
    destination = tmp_path / "Documentos" / "PDF" / "2025"
    destination.mkdir(parents=True)
    (destination / "report.pdf").write_text("existing")

    plan = build_plan(scan_root(tmp_path), date_mode=DateMode.YEAR)

    assert plan[0].destination == destination / "report (1).pdf"
    assert plan[0].collision_renamed is True


def test_plan_renames_same_run_case_insensitive_conflicts(tmp_path) -> None:
    plan = build_plan(
        ScanResult(
            root=tmp_path,
            files=(
                FileEntry(tmp_path / "photo.jpg", "photo.jpg", ".jpg"),
                FileEntry(tmp_path / "other" / "PHOTO.JPG", "PHOTO.JPG", ".jpg"),
            ),
        )
    )
    destinations = [move.destination.name for move in plan]

    assert destinations == ["photo.jpg", "PHOTO (1).JPG"]
    assert len({name.casefold() for name in destinations}) == 2
