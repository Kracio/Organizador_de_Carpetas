from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
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


@dataclass(frozen=True)
class CleanupOptions:
    """Configuration for the report-only cleanup analyzer."""

    old_days: int = 180
    large_mb: int = 100
    archive_days: int = 180
    recursive: bool = False
    now: datetime | None = None


@dataclass(frozen=True)
class AnalyzedFile:
    """File metadata captured without mutating the original file."""

    path: Path
    relative_path: Path
    name: str
    suffix: str
    size_bytes: int
    modified_at: datetime


@dataclass(frozen=True)
class CleanupFinding:
    """One report-only recommendation for a potentially cluttered file."""

    category: str
    label: str
    path: Path
    relative_path: Path
    reason: str


@dataclass(frozen=True)
class DuplicateGroup:
    """Exact duplicate files with matching size and SHA-256 hash."""

    sha256: str
    size_bytes: int
    files: tuple[AnalyzedFile, ...]


@dataclass(frozen=True)
class SkippedFile:
    """File that could not be analyzed completely."""

    path: Path
    relative_path: Path
    reason: str


@dataclass(frozen=True)
class CleanupReport:
    """Structured cleanup report produced without moving or deleting files."""

    root: Path
    options: CleanupOptions
    generated_at: datetime
    files: tuple[AnalyzedFile, ...]
    ignored_directories: int
    findings: tuple[CleanupFinding, ...]
    duplicate_groups: tuple[DuplicateGroup, ...]
    skipped_files: tuple[SkippedFile, ...] = ()

    @property
    def category_totals(self) -> dict[str, int]:
        totals: dict[str, int] = {
            "old": 0,
            "large": 0,
            "old_archive_installer": 0,
            "copy_temp_name": 0,
            "exact_duplicates": len(self.duplicate_groups),
        }
        for finding in self.findings:
            totals[finding.category] = totals.get(finding.category, 0) + 1
        return totals


@dataclass(frozen=True)
class CleanupReviewItem:
    """Selectable cleanup candidate for the explicit quarantine review flow."""

    index: int
    source: Path
    relative_path: Path
    category: str
    label: str
    reason: str
    duplicate_group: int | None = None
    keep_representative: Path | None = None


@dataclass(frozen=True)
class SelectionResult:
    """Parsed interactive selection for review candidates."""

    selected_indexes: tuple[int, ...] = ()
    cancelled: bool = False
