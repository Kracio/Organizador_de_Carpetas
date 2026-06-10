import os
from datetime import datetime

from organizer_cli.analyzer import analyze_cleanup
from organizer_cli.models import CleanupOptions


NOW = datetime(2026, 6, 10, 12, 0, 0)


def _set_mtime(path, year: int, month: int, day: int = 1) -> None:
    timestamp = datetime(year, month, day, 12, 0, 0).timestamp()
    os.utime(path, (timestamp, timestamp))


def _categories(report):
    return {(finding.category, finding.relative_path.as_posix()) for finding in report.findings}


def test_old_file_threshold_is_deterministic(tmp_path) -> None:
    old_file = tmp_path / "old.pdf"
    fresh_file = tmp_path / "fresh.pdf"
    old_file.write_text("old")
    fresh_file.write_text("fresh")
    _set_mtime(old_file, 2025, 1)
    _set_mtime(fresh_file, 2026, 6)

    report = analyze_cleanup(tmp_path, CleanupOptions(old_days=180, now=NOW))

    assert ("old", "old.pdf") in _categories(report)
    assert ("old", "fresh.pdf") not in _categories(report)


def test_large_file_threshold_uses_size_bytes(tmp_path) -> None:
    large = tmp_path / "large.bin"
    small = tmp_path / "small.bin"
    large.write_bytes(b"x" * (1024 * 1024 + 1))
    small.write_bytes(b"x" * 10)

    report = analyze_cleanup(tmp_path, CleanupOptions(large_mb=1, now=NOW))

    categories = _categories(report)

    assert ("large", "large.bin") in categories
    assert ("large", "small.bin") not in categories


def test_archive_and_installer_age_heuristic(tmp_path) -> None:
    installer = tmp_path / "setup.exe"
    archive = tmp_path / "files.zip"
    fresh_archive = tmp_path / "fresh.zip"
    installer.write_text("exe")
    archive.write_text("zip")
    fresh_archive.write_text("zip")
    _set_mtime(installer, 2024, 1)
    _set_mtime(archive, 2024, 1)
    _set_mtime(fresh_archive, 2026, 6)

    report = analyze_cleanup(tmp_path, CleanupOptions(archive_days=180, now=NOW))
    categories = _categories(report)

    assert ("old_archive_installer", "setup.exe") in categories
    assert ("old_archive_installer", "files.zip") in categories
    assert ("old_archive_installer", "fresh.zip") not in categories


def test_copy_version_like_names_are_reported(tmp_path) -> None:
    names = ["report copy.pdf", "factura copia.docx", "notes (1).txt", "backup-final2.zip", "download.tmp"]
    for name in names:
        (tmp_path / name).write_text("x")

    report = analyze_cleanup(tmp_path, CleanupOptions(now=NOW))
    suspicious = {finding.relative_path.as_posix() for finding in report.findings if finding.category == "copy_temp_name"}

    assert set(names) <= suspicious


def test_exact_duplicates_use_hash_not_name_or_size_only(tmp_path) -> None:
    (tmp_path / "a.txt").write_bytes(b"same")
    (tmp_path / "b.txt").write_bytes(b"same")
    (tmp_path / "c.txt").write_bytes(b"diff")
    (tmp_path / "d.txt").write_bytes(b"DIFF")

    report = analyze_cleanup(tmp_path, CleanupOptions(now=NOW))

    groups = [tuple(file.relative_path.as_posix() for file in group.files) for group in report.duplicate_groups]

    assert groups == [("a.txt", "b.txt")]


def test_non_recursive_default_ignores_nested_files(tmp_path) -> None:
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested = nested_dir / "old copy.pdf"
    nested.write_text("old")
    _set_mtime(nested, 2020, 1)

    report = analyze_cleanup(tmp_path, CleanupOptions(now=NOW))

    assert report.files == ()
    assert report.ignored_directories == 1
    assert report.findings == ()


def test_recursive_flag_includes_nested_files(tmp_path) -> None:
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested = nested_dir / "old copy.pdf"
    nested.write_text("old")
    _set_mtime(nested, 2020, 1)

    report = analyze_cleanup(tmp_path, CleanupOptions(recursive=True, now=NOW))
    categories = _categories(report)

    assert report.ignored_directories == 0
    assert ("old", "nested/old copy.pdf") in categories
    assert ("copy_temp_name", "nested/old copy.pdf") in categories
