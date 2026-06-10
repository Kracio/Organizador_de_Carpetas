from __future__ import annotations

from pathlib import Path

from .date_organization import DateMode, date_destination_parts
from .models import PlannedMove, ScanResult
from .rules import classify


def build_plan(scan: ScanResult, *, date_mode: DateMode = DateMode.NONE) -> tuple[PlannedMove, ...]:
    """Build a complete collision-safe move plan without mutating the filesystem."""

    reserved_by_dir: dict[Path, set[str]] = {}
    planned: list[PlannedMove] = []

    for entry in scan.files:
        classification = classify(entry)
        destination_parts = (*classification.destination_parts, *date_destination_parts(entry.path, date_mode))
        destination_dir = scan.root.joinpath(*destination_parts)
        reserved = reserved_by_dir.setdefault(destination_dir, _existing_names_casefold(destination_dir))
        destination, renamed = _unique_destination(destination_dir, entry.name, reserved)
        reserved.add(destination.name.casefold())
        planned.append(
            PlannedMove(
                source=entry.path,
                destination=destination,
                category=classification.label,
                collision_renamed=renamed,
            )
        )

    return tuple(planned)


def _existing_names_casefold(directory: Path) -> set[str]:
    if not directory.exists():
        return set()
    return {child.name.casefold() for child in directory.iterdir()}


def _unique_destination(destination_dir: Path, filename: str, reserved: set[str]) -> tuple[Path, bool]:
    candidate = destination_dir / filename
    if candidate.name.casefold() not in reserved:
        return candidate, False

    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        renamed = destination_dir / f"{stem} ({index}){suffix}"
        if renamed.name.casefold() not in reserved:
            return renamed, True
        index += 1
