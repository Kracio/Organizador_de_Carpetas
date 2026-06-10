import os
from datetime import datetime
from pathlib import Path

import pytest

from organizer_cli.analyzer import analyze_cleanup
from organizer_cli.cleanup_review import (
    REVIEW_CATEGORY_ALL,
    REVIEW_CATEGORY_DUPLICATES,
    REVIEW_CATEGORY_SUSPICIOUS,
    SelectionParseError,
    build_quarantine_plan,
    build_review_items,
    filter_review_items,
    parse_selection,
)
from organizer_cli.models import CleanupOptions


NOW = datetime(2026, 6, 10, 12, 0, 0)


def _set_mtime(path: Path, year: int, month: int, day: int = 1) -> None:
    timestamp = datetime(year, month, day, 12, 0, 0).timestamp()
    os.utime(path, (timestamp, timestamp))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,3,5", (1, 3, 5)),
        ("1-3", (1, 2, 3)),
        ("1,3-5,5", (1, 3, 4, 5)),
        ("all", (1, 2, 3, 4, 5)),
    ],
)
def test_parse_selection_numbers_ranges_all_and_dedupes(raw: str, expected: tuple[int, ...]) -> None:
    assert parse_selection(raw, 5).selected_indexes == expected


@pytest.mark.parametrize("raw", ["none", "", "q", "cancel", "salir"])
def test_parse_selection_none_and_cancel(raw: str) -> None:
    result = parse_selection(raw, 5)

    if raw in {"q", "cancel", "salir"}:
        assert result.cancelled is True
    else:
        assert result.selected_indexes == ()
        assert result.cancelled is False


@pytest.mark.parametrize("raw", ["0", "4", "bad", "1-", "3-1"])
def test_parse_selection_invalid_retries_via_exception(raw: str) -> None:
    with pytest.raises(SelectionParseError):
        parse_selection(raw, 3)


def test_duplicate_review_candidates_select_only_non_representatives(tmp_path) -> None:
    (tmp_path / "a.txt").write_bytes(b"same")
    (tmp_path / "b.txt").write_bytes(b"same")
    (tmp_path / "c.txt").write_bytes(b"same")

    report = analyze_cleanup(tmp_path, CleanupOptions(now=NOW))
    duplicate_items = filter_review_items(build_review_items(report), REVIEW_CATEGORY_DUPLICATES)

    assert [item.relative_path.as_posix() for item in duplicate_items] == ["b.txt", "c.txt"]
    assert all(item.keep_representative == Path("a.txt") for item in duplicate_items)


def test_filter_all_reviewable_findings_dedupes_same_source(tmp_path) -> None:
    suspicious_old = tmp_path / "backup.zip"
    suspicious_old.write_text("zip")
    _set_mtime(suspicious_old, 2020, 1)

    report = analyze_cleanup(tmp_path, CleanupOptions(now=NOW))
    all_items = filter_review_items(build_review_items(report), REVIEW_CATEGORY_ALL)

    assert [item.relative_path.as_posix() for item in all_items] == ["backup.zip"]
    assert all_items[0].index == 1


def test_suspicious_review_category_is_reindexed(tmp_path) -> None:
    old_file = tmp_path / "ancient.pdf"
    suspicious = tmp_path / "report copy.pdf"
    old_file.write_text("old")
    suspicious.write_text("copy")
    _set_mtime(old_file, 2020, 1)

    report = analyze_cleanup(tmp_path, CleanupOptions(now=NOW))
    suspicious_items = filter_review_items(build_review_items(report), REVIEW_CATEGORY_SUSPICIOUS)

    assert [item.index for item in suspicious_items] == [1]
    assert suspicious_items[0].relative_path == Path("report copy.pdf")


def test_quarantine_plan_preserves_relative_paths_and_avoids_collisions(tmp_path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    source = nested / "report copy.pdf"
    source.write_text("copy")
    existing = tmp_path / "_cleanup_quarantine" / "2026-06-10_120000" / "nested"
    existing.mkdir(parents=True)
    (existing / "report copy.pdf").write_text("existing")

    report = analyze_cleanup(tmp_path, CleanupOptions(recursive=True, now=NOW))
    item = filter_review_items(build_review_items(report), REVIEW_CATEGORY_SUSPICIOUS)[0]
    plan = build_quarantine_plan(tmp_path, (item,), NOW)

    assert len(plan) == 1
    assert plan[0].destination == existing / "report copy (1).pdf"
    assert plan[0].collision_renamed is True
    assert source.exists()
