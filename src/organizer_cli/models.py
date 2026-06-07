from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FileEntry:
    """A direct file found in the target root."""

    path: Path
    name: str
    suffix: str


@dataclass(frozen=True)
class ScanResult:
    """Non-recursive scan output."""

    root: Path
    files: tuple[FileEntry, ...]
    ignored_directories: int = 0


@dataclass(frozen=True)
class CategoryRule:
    """Built-in routing rule visible through `rules show`."""

    key: str
    label: str
    destination_parts: tuple[str, ...]
    extensions: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class ClassificationResult:
    """The deterministic category selected for a file."""

    category: str
    label: str
    destination_parts: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class PlannedMove:
    """A safe move planned before any mutation happens."""

    source: Path
    destination: Path
    category: str
    collision_renamed: bool = False


@dataclass(frozen=True)
class MoveResult:
    """Result of applying one planned move."""

    planned_move: PlannedMove
    applied: bool
    error: str | None = None


@dataclass(frozen=True)
class RunSummary:
    """Summary numbers for preview and apply reports."""

    scanned_files: int
    ignored_directories: int
    planned_moves: int
    renamed_collisions: int
    category_totals: dict[str, int] = field(default_factory=dict)
    applied_moves: int = 0
    skipped_errors: int = 0
