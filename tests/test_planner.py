from organizer_cli.models import FileEntry, ScanResult
from organizer_cli.planner import build_plan
from organizer_cli.scanner import scan_root


def test_plan_renames_existing_destination_collision(tmp_path) -> None:
    (tmp_path / "photo.jpg").write_text("source")
    destination = tmp_path / "Fotos" / "General"
    destination.mkdir(parents=True)
    (destination / "photo.jpg").write_text("existing")

    plan = build_plan(scan_root(tmp_path))

    assert plan[0].destination == destination / "photo (1).jpg"
    assert plan[0].collision_renamed is True


def test_plan_renames_same_run_case_insensitive_conflicts(tmp_path) -> None:
    plan = build_plan(
        ScanResult(
            root=tmp_path,
            files=(
                FileEntry(tmp_path / "photo.jpg", "photo.jpg", ".jpg"),
                FileEntry(tmp_path / "other" / "PHOTO.JPG", "PHOTO.JPG", ".jpg"),
            ),
        )
    )
    destinations = [move.destination.name for move in plan]

    assert destinations == ["photo.jpg", "PHOTO (1).JPG"]
    assert len({name.casefold() for name in destinations}) == 2
