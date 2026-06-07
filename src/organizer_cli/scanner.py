from __future__ import annotations

from pathlib import Path

from .models import FileEntry, ScanResult


def scan_root(root: Path) -> ScanResult:
    """Scan only direct children of *root*, returning files and counting folders.

    This function does not create, move, delete, or traverse anything. Nested files are
    intentionally invisible to the MVP pipeline because existing folders must remain
    untouched.
    """

    target = root.expanduser().resolve()
    if not target.exists():
        raise FileNotFoundError(f"Target path does not exist: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Target path is not a directory: {target}")

    files: list[FileEntry] = []
    ignored_directories = 0

    for child in sorted(target.iterdir(), key=lambda path: path.name.lower()):
        if child.is_file():
            files.append(FileEntry(path=child, name=child.name, suffix=child.suffix.lower()))
        elif child.is_dir():
            ignored_directories += 1

    return ScanResult(root=target, files=tuple(files), ignored_directories=ignored_directories)
