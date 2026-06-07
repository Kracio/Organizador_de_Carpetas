from organizer_cli.models import PlannedMove
from organizer_cli.mover import apply_plan, iter_apply_plan


def test_apply_plan_creates_destination_lazily_and_moves_file(tmp_path) -> None:
    source = tmp_path / "report.pdf"
    source.write_text("content")
    destination = tmp_path / "Documentos" / "PDF" / "report.pdf"

    results = apply_plan((PlannedMove(source, destination, "Documentos/PDF"),))

    assert results[0].applied is True
    assert destination.read_text() == "content"
    assert not source.exists()


def test_apply_plan_skips_existing_destination_and_continues(tmp_path) -> None:
    first = tmp_path / "one.pdf"
    second = tmp_path / "two.pdf"
    first.write_text("one")
    second.write_text("two")
    conflict = tmp_path / "Documentos" / "PDF" / "one.pdf"
    conflict.parent.mkdir(parents=True)
    conflict.write_text("existing")
    second_destination = tmp_path / "Documentos" / "PDF" / "two.pdf"

    results = apply_plan(
        (
            PlannedMove(first, conflict, "Documentos/PDF"),
            PlannedMove(second, second_destination, "Documentos/PDF"),
        )
    )

    assert results[0].applied is False
    assert results[0].error
    assert results[1].applied is True
    assert first.exists()
    assert second_destination.exists()


def test_iter_apply_plan_streams_successes_in_plan_order(tmp_path) -> None:
    first = tmp_path / "one.pdf"
    second = tmp_path / "two.pdf"
    first.write_text("one")
    second.write_text("two")
    first_destination = tmp_path / "Documentos" / "PDF" / "one.pdf"
    second_destination = tmp_path / "Documentos" / "PDF" / "two.pdf"

    results = list(
        iter_apply_plan(
            (
                PlannedMove(first, first_destination, "Documentos/PDF"),
                PlannedMove(second, second_destination, "Documentos/PDF"),
            )
        )
    )

    assert [result.planned_move.source.name for result in results] == ["one.pdf", "two.pdf"]
    assert [result.applied for result in results] == [True, True]
    assert first_destination.exists()
    assert second_destination.exists()


def test_iter_apply_plan_skips_conflict_and_continues_streaming(tmp_path) -> None:
    first = tmp_path / "one.pdf"
    second = tmp_path / "two.pdf"
    first.write_text("one")
    second.write_text("two")
    conflict = tmp_path / "Documentos" / "PDF" / "one.pdf"
    conflict.parent.mkdir(parents=True)
    conflict.write_text("existing")
    second_destination = tmp_path / "Documentos" / "PDF" / "two.pdf"

    results = list(
        iter_apply_plan(
            (
                PlannedMove(first, conflict, "Documentos/PDF"),
                PlannedMove(second, second_destination, "Documentos/PDF"),
            )
        )
    )

    assert len(results) == 2
    assert results[0].applied is False
    assert "Destination already exists" in (results[0].error or "")
    assert results[1].applied is True
    assert first.exists()
    assert conflict.read_text() == "existing"
    assert second_destination.exists()


def test_apply_plan_wrapper_matches_iter_apply_plan(tmp_path) -> None:
    streamed_source = tmp_path / "streamed.pdf"
    wrapped_source = tmp_path / "wrapped.pdf"
    streamed_source.write_text("streamed")
    wrapped_source.write_text("wrapped")

    streamed_results = tuple(
        iter_apply_plan((PlannedMove(streamed_source, tmp_path / "A" / "streamed.pdf", "Documentos/PDF"),))
    )
    wrapped_results = apply_plan((PlannedMove(wrapped_source, tmp_path / "B" / "wrapped.pdf", "Documentos/PDF"),))

    assert isinstance(wrapped_results, tuple)
    assert [result.applied for result in wrapped_results] == [result.applied for result in streamed_results]
