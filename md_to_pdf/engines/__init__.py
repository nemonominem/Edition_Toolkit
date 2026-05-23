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


# ── Typst variable names that are safe to override ───────────────────────────
#
# These correspond to the #let variables defined at the top of each .typ style
# file.  Only variables listed here are emitted as overrides — anything else
# in a sidecar typst_overrides block is silently ignored (safety guard).
#
# Value types:
#   "pt"  → numeric, emitted as  #let body-size = 10pt
#   "em"  → numeric, emitted as  #let body-spacing = 1.4em
#   "str" → string,  emitted as  #let page-paper = "a4"
#
_TYPST_OVERRIDE_VARS: dict[str, str] = {
    # Typography
    "body_size":     "pt",   # body text size               e.g. "10pt" or 10
    "body_leading":  "em",   # inter-line gap                e.g. "0.65em" or 0.65
    "body_spacing":  "em",   # inter-paragraph gap           e.g. "1.4em" or 1.4
    "list_spacing":  "em",   # gap between list items        e.g. "0.9em" or 0.9
    # Headings — size and vertical spacing
    "h1_size":       "pt",
    "h1_above":      "em",
    "h1_below":      "em",
    "h2_size":       "pt",
    "h2_above":      "em",
    "h2_below":      "em",
    "h3_size":       "pt",
    "h3_above":      "em",
    "h3_below":      "em",
    "h4_size":       "pt",
    "h4_above":      "em",
    "h4_below":      "em",
    # Running header / footer
    "header_size":   "pt",
    "footer_size":   "pt",
    # Page geometry
    "page_paper":    "str",  # "a4" | "us-letter" | "a5" etc.
}

# Canonical Typst variable name uses hyphens; sidecar keys use underscores.
# This dict maps sidecar key → typst variable name.
_TYPST_VAR_NAME: dict[str, str] = {
    k: k.replace("_", "-") for k in _TYPST_OVERRIDE_VARS
}


def _normalise_typst_value(key: str, raw) -> str | None:
    """
    Convert a sidecar value to its Typst literal form.

    raw may be a number (int/float) or a string like "10pt" / "0.65em" / "a4".
    Returns the Typst literal string, or None if the value cannot be parsed.
    """
    vtype = _TYPST_OVERRIDE_VARS.get(key)
    if vtype is None:
        return None

    if vtype == "str":
        return f'"{raw}"'

    # Numeric types: strip unit if already present, then re-attach.
    unit = vtype  # "pt" or "em"
    if isinstance(raw, (int, float)):
        return f"{raw}{unit}"
    if isinstance(raw, str):
        s = raw.strip()
        # Accept "10pt", "10 pt", "0.65em", "0.65 em", or bare "10"
        m = re.match(r'^([0-9]+(?:\.[0-9]*)?)[ \t]*(?:pt|em)?$', s)
        if m:
            return f"{m.group(1)}{unit}"
    return None


def load_typst_overrides(md_path: Path) -> dict[str, str]:
    """
    Load the typst_overrides block from <md_path.stem>.json.

    Returns a dict mapping Typst variable name (hyphen form, e.g. "body-size")
    to its Typst literal value string (e.g. "10pt").
    Unknown keys and malformed values are silently skipped.
    Empty dict if no sidecar or no typst_overrides block.
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

    block = data.get("typst_overrides")
    if not isinstance(block, dict):
        return {}

    result: dict[str, str] = {}
    for raw_key, raw_val in block.items():
        key = raw_key.lower().replace("-", "_")
        typst_val = _normalise_typst_value(key, raw_val)
        if typst_val is not None:
            result[_TYPST_VAR_NAME[key]] = typst_val
        else:
            import sys
            print(
                f"  [sidecar] Warning: typst_overrides.{raw_key} = {raw_val!r} "
                f"— unrecognised key or malformed value, skipped.",
                file=sys.stderr,
            )
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
