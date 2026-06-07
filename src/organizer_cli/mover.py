from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

from .models import MoveResult, PlannedMove


def iter_apply_plan(plan: tuple[PlannedMove, ...] | list[PlannedMove]) -> Iterator[MoveResult]:
    """Yield one result per planned move, best-effort and never overwriting."""

    for move in plan:
        try:
            if move.destination.exists():
                raise FileExistsError(f"Destination already exists: {move.destination}")
            move.destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(move.source), str(move.destination))
            yield MoveResult(planned_move=move, applied=True)
        except (PermissionError, FileNotFoundError, FileExistsError, OSError) as error:
            yield MoveResult(planned_move=move, applied=False, error=str(error))


def apply_plan(plan: tuple[PlannedMove, ...] | list[PlannedMove]) -> tuple[MoveResult, ...]:
    """Apply planned moves best-effort, never overwriting and continuing on errors."""

    return tuple(iter_apply_plan(plan))


def destination_exists(path: Path) -> bool:
    return path.exists()
