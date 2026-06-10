from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path


class DateMode(str, Enum):
    NONE = "none"
    YEAR = "year"
    YEAR_MONTH = "year-month"


MONTH_LABELS: tuple[str, ...] = (
    "01-Enero",
    "02-Febrero",
    "03-Marzo",
    "04-Abril",
    "05-Mayo",
    "06-Junio",
    "07-Julio",
    "08-Agosto",
    "09-Septiembre",
    "10-Octubre",
    "11-Noviembre",
    "12-Diciembre",
)


def date_destination_parts(path: Path, mode: DateMode = DateMode.NONE) -> tuple[str, ...]:
    """Return optional date-based destination folders derived from file mtime."""

    if mode == DateMode.NONE:
        return ()

    modified_at = datetime.fromtimestamp(path.stat().st_mtime)
    year = str(modified_at.year)
    if mode == DateMode.YEAR:
        return (year,)
    if mode == DateMode.YEAR_MONTH:
        return (year, MONTH_LABELS[modified_at.month - 1])

    raise ValueError(f"Unsupported date mode: {mode}")
