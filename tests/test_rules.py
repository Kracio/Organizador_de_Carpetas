from pathlib import Path

from organizer_cli.models import FileEntry
from organizer_cli.rules import classify


def entry(name: str) -> FileEntry:
    path = Path(name)
    return FileEntry(path=path, name=name, suffix=path.suffix.lower())


def test_classifies_document_and_media_extensions() -> None:
    assert classify(entry("report.pdf")).label == "Documentos/PDF"
    assert classify(entry("slides.pptx")).label == "Documentos/PowerPoint"
    assert classify(entry("table.csv")).label == "Documentos/Excel-CSV"
    assert classify(entry("song.mp3")).label == "Multimedia/Audio"


def test_classifies_whatsapp_and_screenshots_before_general_photos() -> None:
    assert classify(entry("IMG-20240601-WA0001.jpg")).label == "Fotos/WhatsApp"
    assert classify(entry("vacaciones-whatsapp.png")).label == "Fotos/WhatsApp"
    assert classify(entry("Screenshot 2024-06-01.png")).label == "Fotos/Capturas"
    assert classify(entry("playa.jpg")).label == "Fotos/General"


def test_unknown_extension_goes_to_otros() -> None:
    assert classify(entry("notes.unknown")).label == "Otros"
