from __future__ import annotations

import re
from pathlib import Path

from .models import CategoryRule, ClassificationResult, FileEntry


PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".heic")

RULES: tuple[CategoryRule, ...] = (
    CategoryRule(
        key="photos_whatsapp",
        label="Fotos/WhatsApp",
        destination_parts=("Fotos", "WhatsApp"),
        extensions=PHOTO_EXTENSIONS,
        patterns=("whatsapp", "img-*-wa*"),
        description="Fotos de WhatsApp por nombre o patrón IMG-...-WA.",
    ),
    CategoryRule(
        key="photos_screenshots",
        label="Fotos/Capturas",
        destination_parts=("Fotos", "Capturas"),
        extensions=PHOTO_EXTENSIONS,
        patterns=("screenshot", "screen shot", "captura"),
        description="Capturas de pantalla por patrones habituales.",
    ),
    CategoryRule(
        key="photos_general",
        label="Fotos/General",
        destination_parts=("Fotos", "General"),
        extensions=PHOTO_EXTENSIONS,
        description="Imágenes y fotos generales.",
    ),
    CategoryRule("documents_pdf", "Documentos/PDF", ("Documentos", "PDF"), (".pdf",), description="Documentos PDF."),
    CategoryRule("documents_word", "Documentos/Word", ("Documentos", "Word"), (".doc", ".docx", ".odt"), description="Documentos Word/OpenDocument."),
    CategoryRule("documents_powerpoint", "Documentos/PowerPoint", ("Documentos", "PowerPoint"), (".ppt", ".pptx", ".odp"), description="Presentaciones."),
    CategoryRule("documents_excel_csv", "Documentos/Excel-CSV", ("Documentos", "Excel-CSV"), (".xls", ".xlsx", ".csv", ".ods"), description="Planillas y CSV."),
    CategoryRule("archives", "Comprimidos", ("Comprimidos",), (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"), description="Archivos comprimidos."),
    CategoryRule("videos", "Multimedia/Videos", ("Multimedia", "Videos"), (".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm"), description="Videos."),
    CategoryRule("audio", "Multimedia/Audio", ("Multimedia", "Audio"), (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"), description="Audio y música."),
    CategoryRule("installers", "Instaladores", ("Instaladores",), (".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk"), description="Instaladores."),
)

OTHER_RULE = CategoryRule("other", "Otros", ("Otros",), description="Todo lo que no coincide con reglas anteriores.")

WHATSAPP_PHOTO_RE = re.compile(r"^img-\d{8}-wa\d+", re.IGNORECASE)


def classify(entry: FileEntry) -> ClassificationResult:
    """Classify one scanned file with built-in deterministic rules."""

    name_lower = entry.name.lower()
    suffix = entry.suffix.lower()

    if suffix in PHOTO_EXTENSIONS and ("whatsapp" in name_lower or WHATSAPP_PHOTO_RE.search(Path(entry.name).stem)):
        return _result(RULES[0], "filename pattern")

    if suffix in PHOTO_EXTENSIONS and any(pattern in name_lower for pattern in ("screenshot", "screen shot", "captura")):
        return _result(RULES[1], "filename pattern")

    for rule in RULES[2:]:
        if suffix in rule.extensions:
            return _result(rule, "extension")

    return _result(OTHER_RULE, "fallback")


def iter_rules() -> tuple[CategoryRule, ...]:
    """Return the current built-in rules; seam for future config-backed rules."""

    return (*RULES, OTHER_RULE)


def _result(rule: CategoryRule, reason: str) -> ClassificationResult:
    return ClassificationResult(
        category=rule.key,
        label=rule.label,
        destination_parts=rule.destination_parts,
        reason=reason,
    )
