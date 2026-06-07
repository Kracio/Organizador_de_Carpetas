from __future__ import annotations

import sys

from organizer_cli.cli import app


def main() -> None:
    """Entry point used by PyInstaller to open the guided menu by default."""

    sys.argv = [sys.argv[0], "menu"]
    app()


if __name__ == "__main__":
    main()
