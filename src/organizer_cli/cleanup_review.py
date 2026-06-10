from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from .models import CleanupReport, CleanupReviewItem, PlannedMove, SelectionResult


QUARANTINE_DIR_NAME = "_cleanup_quarantine"
REVIEW_CATEGORY_DUPLICATES = "duplicates"
REVIEW_CATEGORY_SUSPICIOUS = "suspicious"
REVIEW_CATEGORY_OLD_ARCHIVES = "old_archives"
REVIEW_CATEGORY_OLD = "old"
REVIEW_CATEGORY_LARGE = "large"
REVIEW_CATEGORY_ALL = "all"

FINDING_TO_REVIEW_CATEGORY = {
    "copy_temp_name": REVIEW_CATEGORY_SUSPICIOUS,
    "old_archive_installer": REVIEW_CATEGORY_OLD_ARCHIVES,
    "old": REVIEW_CATEGORY_OLD,
    "large": REVIEW_CATEGORY_LARGE,
}


class SelectionParseError(ValueError):
    """Raised when a review selection cannot be parsed safely."""


def parse_selection(raw: str, max_index: int) -> SelectionResult:
    """Parse `1,3,5`, `1-10`, `all`, `none`, or `q` into display indexes."""

    value = raw.strip().casefold()
    if value in {"q", "quit", "exit", "salir", "cancel", "cancelar"}:
        return SelectionResult(cancelled=True)
    if value in {"", "none", "ninguno", "nada"}:
        return SelectionResult()
    if max_index < 1:
        raise SelectionParseError("No hay candidatos para seleccionar.")
    if value in {"all", "todo", "todos", "todas"}:
        return SelectionResult(tuple(range(1, max_index + 1)))

    selected: set[int] = set()
    for token in (part.strip() for part in value.split(",")):
        if not token:
            raise SelectionParseError("Hay una coma sin número. Usá algo como 1,3,5 o 1-4.")
        if "-" in token:
            selected.update(_parse_range(token, max_index))
            continue
        selected.add(_parse_index(token, max_index))

    return SelectionResult(tuple(sorted(selected)))


def build_review_items(report: CleanupReport, *, old_limit: int = 25) -> tuple[CleanupReviewItem, ...]:
    """Build stable, selectable candidates from a cleanup report without mutating files."""

    items: list[CleanupReviewItem] = []

    for group_index, group in enumerate(report.duplicate_groups, start=1):
        files = tuple(sorted(group.files, key=lambda file: file.relative_path.as_posix().casefold()))
        if len(files) < 2:
            continue
        keep = files[0]
        for duplicate in files[1:]:
            if _is_inside_quarantine(duplicate.relative_path):
                continue
            items.append(
                CleanupReviewItem(
                    index=0,
                    source=duplicate.path,
                    relative_path=duplicate.relative_path,
                    category=REVIEW_CATEGORY_DUPLICATES,
                    label="Duplicado exacto extra",
                    reason=f"mismo contenido que {keep.relative_path.as_posix()}; se recomienda conservar ese representante",
                    duplicate_group=group_index,
                    keep_representative=keep.relative_path,
                )
            )

    old_count = 0
    for finding in sorted(report.findings, key=lambda item: (item.category, item.relative_path.as_posix().casefold())):
        if _is_inside_quarantine(finding.relative_path):
            continue
        review_category = FINDING_TO_REVIEW_CATEGORY.get(finding.category)
        if review_category is None:
            continue
        if review_category == REVIEW_CATEGORY_OLD:
            old_count += 1
            if old_count > old_limit:
                continue
        items.append(
            CleanupReviewItem(
                index=0,
                source=finding.path,
                relative_path=finding.relative_path,
                category=review_category,
                label=finding.label,
                reason=finding.reason,
            )
        )

    return tuple(
        CleanupReviewItem(
            index=index,
            source=item.source,
            relative_path=item.relative_path,
            category=item.category,
            label=item.label,
            reason=item.reason,
            duplicate_group=item.duplicate_group,
            keep_representative=item.keep_representative,
        )
        for index, item in enumerate(items, start=1)
    )


def filter_review_items(items: Iterable[CleanupReviewItem], category: str) -> tuple[CleanupReviewItem, ...]:
    """Return candidates for one menu category, or all reviewable candidates with duplicate sources removed."""

    if category == REVIEW_CATEGORY_ALL:
        return _reindex(_dedupe_by_source(items))
    return _reindex(item for item in items if item.category == category)


def build_quarantine_plan(root: Path, selected: Iterable[CleanupReviewItem], generated_at: datetime) -> tuple[PlannedMove, ...]:
    """Plan collision-safe moves into `_cleanup_quarantine/YYYY-MM-DD_HHMMSS/`."""

    target_root = root.expanduser().resolve()
    quarantine_root = target_root / QUARANTINE_DIR_NAME / generated_at.strftime("%Y-%m-%d_%H%M%S")
    used_destinations: set[Path] = set()
    plan: list[PlannedMove] = []

    for item in _dedupe_by_source(selected):
        relative_path = _safe_relative_path(item.relative_path)
        destination = _collision_safe_destination(quarantine_root / relative_path, used_destinations)
        used_destinations.add(destination)
        plan.append(
            PlannedMove(
                source=item.source,
                destination=destination,
                category=f"quarantine/{item.category}",
                collision_renamed=destination.name != relative_path.name,
            )
        )

    return tuple(plan)


def selection_to_items(items: tuple[CleanupReviewItem, ...], selected_indexes: Iterable[int]) -> tuple[CleanupReviewItem, ...]:
    """Convert display indexes back to candidates in display order."""

    by_index = {item.index: item for item in items}
    return tuple(by_index[index] for index in selected_indexes if index in by_index)


def _parse_range(token: str, max_index: int) -> range:
    parts = token.split("-")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise SelectionParseError(f"Rango inválido: {token}")
    start = _parse_index(parts[0].strip(), max_index)
    end = _parse_index(parts[1].strip(), max_index)
    if start > end:
        raise SelectionParseError(f"Rango inválido: {token}. El inicio debe ser menor o igual al final.")
    return range(start, end + 1)


def _parse_index(token: str, max_index: int) -> int:
    try:
        value = int(token)
    except ValueError as exc:
        raise SelectionParseError(f"Selección inválida: {token}") from exc
    if value < 1 or value > max_index:
        raise SelectionParseError(f"Selección fuera de rango: {value}. Usá números entre 1 y {max_index}.")
    return value


def _dedupe_by_source(items: Iterable[CleanupReviewItem]) -> tuple[CleanupReviewItem, ...]:
    seen: set[Path] = set()
    deduped: list[CleanupReviewItem] = []
    for item in items:
        key = item.source.resolve() if item.source.exists() else item.source.absolute()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return tuple(deduped)


def _reindex(items: Iterable[CleanupReviewItem]) -> tuple[CleanupReviewItem, ...]:
    return tuple(
        CleanupReviewItem(
            index=index,
            source=item.source,
            relative_path=item.relative_path,
            category=item.category,
            label=item.label,
            reason=item.reason,
            duplicate_group=item.duplicate_group,
            keep_representative=item.keep_representative,
        )
        for index, item in enumerate(items, start=1)
    )


def _collision_safe_destination(destination: Path, used_destinations: set[Path]) -> Path:
    candidate = destination
    counter = 1
    while candidate.exists() or candidate in used_destinations:
        candidate = destination.with_name(f"{destination.stem} ({counter}){destination.suffix}")
        counter += 1
    return candidate


def _safe_relative_path(relative_path: Path) -> Path:
    parts = tuple(part for part in relative_path.parts if part not in {"", "."})
    if not parts or relative_path.is_absolute() or ".." in parts:
        return Path(relative_path.name)
    return Path(*parts)


def _is_inside_quarantine(relative_path: Path) -> bool:
    return bool(relative_path.parts) and relative_path.parts[0] == QUARANTINE_DIR_NAME
