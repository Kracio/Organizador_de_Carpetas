from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from .models import AnalyzedFile, CleanupFinding, CleanupOptions, CleanupReport, DuplicateGroup, SkippedFile
from .rules import RULES

ARCHIVE_INSTALLER_EXTENSIONS = frozenset(
    extension
    for rule in RULES
    if rule.key in {"archives", "installers"}
    for extension in rule.extensions
)

COPY_TEMP_NAME_RE = re.compile(
    r"(^|[\s._\-])(copy|copia|backup|bak|temp|tmp|download|descarga|old|final\d*|v\d+)([\s._\-]|$)|\(\d+\)",
    re.IGNORECASE,
)


def analyze_cleanup(root: Path, options: CleanupOptions | None = None) -> CleanupReport:
    """Analyze clutter candidates without deleting, moving, or renaming files."""

    options = options or CleanupOptions()
    target = root.expanduser().resolve()
    if not target.exists():
        raise FileNotFoundError(f"Target path does not exist: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Target path is not a directory: {target}")

    generated_at = options.now or datetime.now()
    files, ignored_directories, skipped_files = _collect_files(target, options.recursive)
    findings = _build_findings(files, options, generated_at)
    duplicate_groups, duplicate_skipped = _find_exact_duplicates(files, target)

    return CleanupReport(
        root=target,
        options=options,
        generated_at=generated_at,
        files=tuple(files),
        ignored_directories=ignored_directories,
        findings=tuple(findings),
        duplicate_groups=tuple(duplicate_groups),
        skipped_files=tuple((*skipped_files, *duplicate_skipped)),
    )


def _collect_files(root: Path, recursive: bool) -> tuple[list[AnalyzedFile], int, list[SkippedFile]]:
    files: list[AnalyzedFile] = []
    skipped: list[SkippedFile] = []
    ignored_directories = 0

    if recursive:
        candidates = sorted((path for path in root.rglob("*") if path.is_file()), key=lambda path: path.relative_to(root).as_posix().lower())
    else:
        candidates = []
        for child in sorted(root.iterdir(), key=lambda path: path.name.lower()):
            if child.is_file():
                candidates.append(child)
            elif child.is_dir():
                ignored_directories += 1

    for path in candidates:
        try:
            stat = path.stat()
        except OSError as exc:
            skipped.append(_skipped(root, path, f"metadata unavailable: {exc}"))
            continue

        files.append(
            AnalyzedFile(
                path=path,
                relative_path=path.relative_to(root),
                name=path.name,
                suffix=path.suffix.lower(),
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime),
            )
        )

    return files, ignored_directories, skipped


def _build_findings(files: list[AnalyzedFile], options: CleanupOptions, now: datetime) -> list[CleanupFinding]:
    findings: list[CleanupFinding] = []
    old_cutoff = now - timedelta(days=options.old_days)
    archive_cutoff = now - timedelta(days=options.archive_days)
    large_threshold = options.large_mb * 1024 * 1024

    for file in files:
        if file.modified_at <= old_cutoff:
            findings.append(_finding("old", "Archivo viejo", file, f"modificado hace más de {options.old_days} días"))
        if file.size_bytes >= large_threshold:
            findings.append(_finding("large", "Archivo pesado", file, f"pesa {_format_size(file.size_bytes)}; umbral {_format_size(large_threshold)}"))
        if file.suffix in ARCHIVE_INSTALLER_EXTENSIONS and file.modified_at <= archive_cutoff:
            findings.append(
                _finding(
                    "old_archive_installer",
                    "Instalador/comprimido viejo",
                    file,
                    f"extensión {file.suffix} y más de {options.archive_days} días",
                )
            )
        if COPY_TEMP_NAME_RE.search(file.path.stem):
            findings.append(_finding("copy_temp_name", "Nombre sospechoso", file, "parece copia, backup, temp, descarga, versión o final"))

    return findings


def _find_exact_duplicates(files: list[AnalyzedFile], root: Path) -> tuple[list[DuplicateGroup], list[SkippedFile]]:
    by_size: dict[int, list[AnalyzedFile]] = defaultdict(list)
    for file in files:
        by_size[file.size_bytes].append(file)

    duplicate_groups: list[DuplicateGroup] = []
    skipped: list[SkippedFile] = []
    for size, same_size_files in sorted(by_size.items()):
        if len(same_size_files) < 2:
            continue

        by_hash: dict[str, list[AnalyzedFile]] = defaultdict(list)
        for file in same_size_files:
            try:
                by_hash[_sha256(file.path)].append(file)
            except OSError as exc:
                skipped.append(_skipped(root, file.path, f"hash unavailable: {exc}"))

        for digest, hashed_files in sorted(by_hash.items()):
            if len(hashed_files) >= 2:
                duplicate_groups.append(DuplicateGroup(sha256=digest, size_bytes=size, files=tuple(hashed_files)))

    return duplicate_groups, skipped


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finding(category: str, label: str, file: AnalyzedFile, reason: str) -> CleanupFinding:
    return CleanupFinding(category=category, label=label, path=file.path, relative_path=file.relative_path, reason=reason)


def _skipped(root: Path, path: Path, reason: str) -> SkippedFile:
    try:
        relative_path = path.relative_to(root)
    except ValueError:
        relative_path = Path(path.name)
    return SkippedFile(path=path, relative_path=relative_path, reason=reason)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"
