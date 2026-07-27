"""Import-protecting launcher for the SSMD CLI.

This module is the installed console entry point.  It imports ``ssmd.cli``
lazily so that import failures surface as a compact diagnostic rather than a
Python traceback.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    """Launch the SSMD CLI, converting import failures to a fatal exit."""
    try:
        from ssmd.cli import cli_main

        if not callable(cli_main):
            raise ImportError("ssmd.cli.cli_main is not callable")
    except Exception as exc:
        debug = "--debug" in (argv or sys.argv[1:])
        print(f"ssmd: fatal: could not load the CLI: {exc}", file=sys.stderr)
        if debug:
            import traceback

            traceback.print_exc(file=sys.stderr)
        raise SystemExit(3) from exc

    cli_main(argv)


if __name__ == "__main__":
    main()
