#!/usr/bin/env python3
"""
md_to_pdf.py — Legacy shim.

Delegates to etk_md2pdf.convert.  Kept for backwards compatibility so that
  python md_to_pdf.py article.md
continues to work without installing the package.

If the package is installed, prefer the 'md2pdf' CLI command instead.
"""
import sys
from pathlib import Path

# Allow running as a script from this directory without installing
sys.path.insert(0, str(Path(__file__).parent))

from etk_md2pdf.convert import main

if __name__ == '__main__':
    main()
