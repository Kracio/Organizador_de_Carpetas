from io import StringIO

from organizer_cli.branding import get_console, print_brand_header, print_status


def test_brand_header_plain_contains_semantic_branding(capsys) -> None:
    print_brand_header("Menú guiado", force_plain=True)

    output = capsys.readouterr().out
    assert "Organizador de Carpetas" in output
    assert "Preview primero" in output
    assert "Menú guiado" in output


def test_status_plain_contains_kind_and_message(capsys) -> None:
    print_status("error", "Opción inválida", force_plain=True)

    output = capsys.readouterr().out
    assert "ERROR" in output
    assert "Opción inválida" in output


def test_console_factory_supports_recorded_no_color_output() -> None:
    stream = StringIO()
    console = get_console(force_plain=True, record=True, file=stream)

    console.print("Organizador de Carpetas")

    assert "Organizador de Carpetas" in stream.getvalue()
