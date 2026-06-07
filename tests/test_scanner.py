from organizer_cli.scanner import scan_root


def test_scan_root_includes_direct_files_and_ignores_directories(tmp_path) -> None:
    (tmp_path / "file.pdf").write_text("pdf")
    nested = tmp_path / "existing-folder"
    nested.mkdir()
    (nested / "nested.pdf").write_text("nested")

    result = scan_root(tmp_path)

    assert [entry.name for entry in result.files] == ["file.pdf"]
    assert result.ignored_directories == 1
    assert nested.exists()


def test_scan_root_does_not_create_destination_folders(tmp_path) -> None:
    (tmp_path / "photo.jpg").write_text("photo")

    scan_root(tmp_path)

    assert not (tmp_path / "Fotos").exists()
