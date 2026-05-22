"""
engines — shared utilities for md_to_pdf engine modules.
"""

from __future__ import annotations

import re
from pathlib import Path


# ── Default document metadata ────────────────────────────────────────────────

METADATA_DEFAULTS: dict[str, str] = {
    "author":   "Author Name",
    "title":    "Article Title",
    "pub-name": "DRASTIC",
    "doc-type": "OSINT RESEARCH PRODUCT",
}


# ── YAML frontmatter parser ──────────────────────────────────────────────────

_FM_RE = re.compile(r'^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n', re.DOTALL)

# Keys recognised in frontmatter, mapped to canonical metadata key.
# Allows both hyphen and underscore variants.
_KEY_ALIASES: dict[str, str] = {
    "author":    "author",
    "title":     "title",
    "pub-name":  "pub-name",
    "pub_name":  "pub-name",
    "pubname":   "pub-name",
    "doc-type":  "doc-type",
    "doc_type":  "doc-type",
    "doctype":   "doc-type",
}


def parse_frontmatter(md_text: str) -> tuple[dict[str, str], str]:
    """
    Parse YAML frontmatter from *md_text*.

    Returns (metadata, body) where:
      - metadata  is a dict of recognised keys (canonical hyphen form) merged
                  over METADATA_DEFAULTS.  Unknown keys are ignored.
      - body      is md_text with the frontmatter block stripped.

    Only simple scalar values are supported (no lists/dicts).  Lines of the
    form ``key: value`` (with optional surrounding quotes) are extracted via
    regex so that a full YAML library is not required.
    """
    meta = dict(METADATA_DEFAULTS)
    m = _FM_RE.match(md_text)
    if m:
        for line in m.group(1).splitlines():
            kv = re.match(r'^([\w-]+)\s*:\s*(.+)$', line.strip())
            if not kv:
                continue
            raw_key = kv.group(1).lower()
            canonical = _KEY_ALIASES.get(raw_key)
            if canonical:
                meta[canonical] = kv.group(2).strip().strip('"\'')
        md_text = md_text[m.end():]

    # Strip bare "Notes" / "References" / "Footnotes" headings that become
    # empty shells once footnote definitions are extracted by the engine.
    md_text = re.sub(
        r'\n#{1,3}[ \t]+(?:Notes?|References?|Footnotes?)[ \t]*\n(?:[ \t]*\n)*',
        '\n',
        md_text,
        flags=re.IGNORECASE,
    )

    return meta, md_text


def read_frontmatter(md_path: Path) -> tuple[dict[str, str], str]:
    """Convenience wrapper: read file, parse frontmatter, return (meta, body)."""
    text = md_path.read_text(encoding="utf-8")
    return parse_frontmatter(text)
