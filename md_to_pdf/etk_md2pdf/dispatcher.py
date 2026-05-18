"""
etk_md2pdf.dispatcher — entry point for the `md2pdf` console script.

Parses --engine, then delegates all remaining argv to the selected engine.

Engines
-------
  typst       (default)  engines/typst/convert.py
  weasyprint              engines/weasyprint/convert.py

Usage
-----
  md2pdf article.md                           # typst, intelligence style
  md2pdf article.md --engine weasyprint       # WeasyPrint
  md2pdf article.md --style intelligence --compile
  md2pdf article.md --engine weasyprint --css magazine --custom my.css
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# engines/ is a sibling of this package directory
_ENGINES_DIR = Path(__file__).resolve().parent.parent / "engines"

_ENGINE_SCRIPTS: dict[str, Path] = {
    "typst":      _ENGINES_DIR / "typst"      / "convert.py",
    "weasyprint": _ENGINES_DIR / "weasyprint"  / "convert.py",
}


def main() -> None:
    # Minimal pre-parse: extract --engine only, forward everything else.
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument(
        "--engine", "-e",
        choices=list(_ENGINE_SCRIPTS),
        default="typst",
        metavar="ENGINE",
    )
    known, rest = pre.parse_known_args()
    engine = known.engine

    script = _ENGINE_SCRIPTS[engine]
    if not script.exists():
        print(
            f"md2pdf: engine script not found at {script}\n"
            f"  Reinstall with: pip install -e .",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd = [sys.executable, str(script)] + rest
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
