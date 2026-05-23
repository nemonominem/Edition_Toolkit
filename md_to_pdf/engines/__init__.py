"""
engines — shared utilities for md_to_pdf engine modules.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


# ── Default document metadata ────────────────────────────────────────────────

METADATA_DEFAULTS: dict[str, str] = {
    "author":   "Author Name",
    "title":    "Article Title",
    "pub-name": "DRASTIC",
    "doc-type": "OSINT RESEARCH PRODUCT",
}

# Location of the shared style JSON files
_STYLES_JSON_DIR = Path(__file__).resolve().parent.parent / "styles"


def load_style_defaults(style: str) -> dict[str, str]:
    """
    Read branding_defaults from md_to_pdf/styles/<style>.json.

    Returns a partial metadata dict (only the keys present in branding_defaults).
    Falls back to empty dict if the file is missing or has no branding_defaults.
    """
    path = _STYLES_JSON_DIR / f"{style}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    bd = data.get("design", {}).get("branding_defaults", {})
    mapping = {
        "pub_name":  "pub-name",
        "doc_type":  "doc-type",
        "author":    "author",
        "title":     "title",
    }
    result: dict[str, str] = {}
    for json_key, meta_key in mapping.items():
        if json_key in bd:
            result[meta_key] = bd[json_key]
    return result


def load_sidecar(md_path: Path) -> dict[str, str]:
    """
    Load a per-article JSON sidecar at <md_path.stem>.json in the same directory.

    Recognised keys (same aliases as frontmatter): author, title, pub_name /
    pub-name / pubname, doc_type / doc-type / doctype.

    Returns a partial metadata dict (only keys present in sidecar).
    Empty dict if no sidecar exists or is malformed.
    """
    sidecar_path = md_path.with_suffix(".json")
    if not sidecar_path.exists():
        return {}
    try:
        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    result: dict[str, str] = {}
    _KEY_SIDECAR: dict[str, str] = {
        "author":   "author",
        "title":    "title",
        "pub-name": "pub-name",
        "pub_name": "pub-name",
        "pubname":  "pub-name",
        "doc-type": "doc-type",
        "doc_type": "doc-type",
        "doctype":  "doc-type",
    }
    for raw_key, val in data.items():
        canonical = _KEY_SIDECAR.get(raw_key.lower())
        if canonical and isinstance(val, str):
            result[canonical] = val
    return result


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


def parse_frontmatter(
    md_text: str,
    sidecar: dict[str, str] | None = None,
) -> tuple[dict[str, str], str]:
    """
    Parse YAML frontmatter from *md_text*.

    Precedence (lowest → highest):
      METADATA_DEFAULTS → style branding_defaults → sidecar JSON → YAML frontmatter

    Callers should merge style defaults and sidecar before calling:
        sidecar = {**load_style_defaults(style), **load_sidecar(md_path)}
        meta, body = parse_frontmatter(md_text, sidecar=sidecar)

    Returns (metadata, body) where:
      - metadata  is a dict of recognised keys (canonical hyphen form).
      - body      is md_text with the frontmatter block stripped.

    Only simple scalar values are supported (no lists/dicts).  Lines of the
    form ``key: value`` (with optional surrounding quotes) are extracted via
    regex so that a full YAML library is not required.
    """
    meta = dict(METADATA_DEFAULTS)
    if sidecar:
        meta.update(sidecar)
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


def read_frontmatter(
    md_path: Path,
    style: str | None = None,
    extra_sidecar: dict[str, str] | None = None,
) -> tuple[dict[str, str], str]:
    """
    Convenience wrapper: read file, load sidecar, parse frontmatter.

    Precedence: METADATA_DEFAULTS → style branding_defaults → sidecar JSON
                → extra_sidecar (explicit --meta overrides) → YAML frontmatter.
    """
    text = md_path.read_text(encoding="utf-8")
    sidecar: dict[str, str] = {}
    if style:
        sidecar.update(load_style_defaults(style))
    sidecar.update(load_sidecar(md_path))
    if extra_sidecar:
        sidecar.update(extra_sidecar)
    return parse_frontmatter(text, sidecar=sidecar)
