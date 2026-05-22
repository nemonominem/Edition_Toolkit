#!/usr/bin/env python3
"""
md_harden — Markdown normalization and hardening tool.

Two-pass workflow
-----------------
Pass 1 — Generate a review document:
    python md_harden.py article.md --review
    → writes article_review.md

    Open article_review.md in VSCode Preview.  Each change is a numbered
    "Suggestion" block with the original text and the proposed replacement.
    Delete suggestions you don't want applied.  Edit the "After" block to
    adjust a suggestion.  Leave the ones you approve untouched.

Pass 2 — Apply the approved suggestions:
    python md_harden.py article.md --apply article_review.md
    → reads back the (edited) review file, applies surviving suggestions,
      writes article_hardened.md

Direct mode (no review step):
    python md_harden.py article.md
    python md_harden.py article.md --dry-run   # diff to stdout only

Transforms (in order):
  1. bold-headings   **Bold** paragraph followed by blank line → #### heading
                     (if followed immediately by text: skipped — it's a definition
                      term or emphasis lead-in, not a heading)
  2. strip-sections  Bare ## Notes / ## References headings removed
  3. pullquotes      Pull-quote lines normalised: one space after pipe,
                     consistent Source: capitalisation
  4. consistency     Advisory: et al. → *et al.*, mixed apostrophe styles, etc.
                     These appear in the review as suggestions to inspect; they
                     are never applied blindly.

Single-column div injection is NOT done automatically — images are fine in
two-column layout by default. Use <div class="single-column"> explicitly in
source for wide graphics that need full width.

Environment variables:
  ANTHROPIC_API_KEY   required for --claude
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import textwrap
from pathlib import Path

# ── Style config loader ───────────────────────────────────────────────────────
#
# Style JSON files live in md_to_pdf/styles/<name>.json, one level above this
# script's own package.  They are the single authoritative source for per-style
# hardening conventions (confidence values, pull-quote attribution style, etc.).
#
# md_harden reads the "hardening" object; md2pdf engines read the "design"
# object. All cross-tool conventions live in the JSON — not hardcoded here.

_STYLES_DIR = Path(__file__).resolve().parent.parent / "md_to_pdf" / "styles"

# Fallback hardening config — used when no --style is passed, or the file
# cannot be found.  Values must match the defaults in the JSON files.
_DEFAULT_HARDENING: dict = {
    "pull_quote_attribution":      {"style": "source:", "confidence": 90},
    "pull_quote_spacing":          {"confidence": 99},
    "pull_quote_missing_source":   {"confidence": 30},
    "bold_headings":               {"confidence": 90},
    "strip_bare_sections":         {"confidence": 95},
    "et_al_italics":               {"confidence": 40},
    "apostrophe_consistency":      {"confidence": 35},
    "pull_quote_style_consistency": {"confidence": 30},
}


def _load_style_config(style: str | None) -> dict:
    """Load the hardening sub-object from md_to_pdf/styles/<style>.json.

    Returns the hardening dict (merged over _DEFAULT_HARDENING) on success,
    or _DEFAULT_HARDENING unchanged if style is None or the file is absent.
    """
    if not style:
        return _DEFAULT_HARDENING

    path = _STYLES_DIR / f"{style}.json"
    if not path.exists():
        print(
            f"md_harden: style config not found: {path}\n"
            f"  Using built-in defaults. Create {path} to customise.",
            file=sys.stderr,
        )
        return _DEFAULT_HARDENING

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"md_harden: could not parse {path}: {exc}", file=sys.stderr)
        return _DEFAULT_HARDENING

    hardening = data.get("hardening", {})
    # Merge: start from defaults, overlay with whatever the file specifies
    merged = dict(_DEFAULT_HARDENING)
    for key, val in hardening.items():
        if key.startswith("_"):
            continue  # skip _comment keys
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = {**merged[key], **val}
        else:
            merged[key] = val
    return merged


# Module-level config — set by main() after CLI parsing, used by all transforms.
# Initialised to defaults so the module is importable without a CLI call.
_HCFG: dict = _DEFAULT_HARDENING


def _hconf(key: str) -> dict:
    """Return the hardening config sub-dict for a given rule key."""
    return _HCFG.get(key, {})


def _hconfidence(key: str) -> int:
    """Return the confidence value for a rule from the loaded style config."""
    return int(_hconf(key).get("confidence", 50))


# ── Suggestion block format ───────────────────────────────────────────────────
#
# ## Suggestion 3 — bold-headings
#
# **Before:**
# ```
# **The WHO players**
# ```
#
# **After:**
# ```
# #### The WHO players
# ```
#
# ---
#
# To reject: delete the entire block (## Suggestion … through ---).
# To adjust: edit the After block.
# Advisory blocks (type starting with "advisory-") are never applied
# automatically even if left in the file — they are for human action only.

_REVIEW_SEP = "\n---\n"
_SUGGESTION_HEADER_RE = re.compile(r'^## Suggestion \d+ — ([^\n]+)\n', re.MULTILINE)
_CONFIDENCE_RE = re.compile(r'\*\*Confidence:\*\* (\d+)%')
_TREATMENT_RE  = re.compile(r'\*\*Treatment:\*\* (Apply|Review)')
_CODE_FENCE_RE = re.compile(r'```[^\n]*\n(.*?)```', re.DOTALL)

APPLY_THRESHOLD = 50  # apply if confidence >= this value


def _treatment(confidence: int) -> str:
    return "Apply" if confidence >= APPLY_THRESHOLD else "Review"


def _make_review_block(
    n: int,
    label: str,
    before: str,
    after: str,
    confidence: int,
    note: str = "",
) -> str:
    before_s = before.rstrip('\n')
    after_s  = after.rstrip('\n')
    treatment = _treatment(confidence)
    note_line = f"\n**Note:** {note}\n" if note else ""
    return (
        f"## Suggestion {n} — {label}\n\n"
        f"**Confidence:** {confidence}%  \n"
        f"**Treatment:** {treatment}\n"
        f"{note_line}\n"
        f"**Before:**\n```\n{before_s}\n```\n\n"
        f"**After:**\n```\n{after_s}\n```\n"
    )


def _parse_review_file(review_text: str) -> list[tuple[str, str]]:
    """
    Parse review doc → (before, after) pairs for surviving blocks
    whose Treatment is Apply (confidence >= threshold).
    Blocks the user deleted are gone; blocks they changed Treatment on are respected.
    """
    blocks = re.split(r'\n---\n', review_text)
    suggestions: list[tuple[str, str]] = []
    for block in blocks:
        if not _SUGGESTION_HEADER_RE.search(block):
            continue
        # Respect Treatment field — skip if Review
        t_match = _TREATMENT_RE.search(block)
        if t_match and t_match.group(1) == "Review":
            continue
        # Also skip if confidence is present but below threshold (user didn't edit)
        c_match = _CONFIDENCE_RE.search(block)
        if c_match and int(c_match.group(1)) < APPLY_THRESHOLD:
            continue
        fences = _CODE_FENCE_RE.findall(block)
        if len(fences) < 2:
            continue
        before = fences[0]
        after  = fences[1]
        if before != after:
            suggestions.append((before, after))
    return suggestions


# ── Transform 1: Bold-only paragraphs → H4 ───────────────────────────────────
#
# Heuristic: a bold-only line is a heading candidate ONLY if the line
# immediately following it is blank (or it is the last line of the file).
# If the next line has content, it is a definition term or emphasis lead-in.
# If the inner text exceeds 80 chars, it is body emphasis, not a heading.
#
# Confidence: from style config "bold_headings.confidence" (default 90%).

_BOLD_ONLY_RE = re.compile(r'^\*\*([^*\n]+?)\*\*[.:]?\s*$')
_BOLD_HEADING_MAX_LEN = 80


def _transform_bold_headings(text: str) -> list[tuple[str, str, str, int, str]]:
    confidence = _hconfidence("bold_headings")
    lines = text.splitlines(keepends=True)
    hunks = []
    for i, line in enumerate(lines):
        stripped = line.rstrip('\n').rstrip()
        m = _BOLD_ONLY_RE.match(stripped)
        if not m:
            continue
        inner = m.group(1).strip()
        if len(inner) > _BOLD_HEADING_MAX_LEN:
            continue
        next_line = lines[i + 1].rstrip('\n') if i + 1 < len(lines) else ''
        if next_line.strip():
            continue
        before = stripped
        after  = f'#### {inner}'
        hunks.append(('bold-headings', before, after, confidence, ''))
    return hunks


# ── Transform 2: Bare section headings stripped ───────────────────────────────
# Confidence: from style config "strip_bare_sections.confidence" (default 95%).
# These headings exist only as section markers for footnote blocks; once
# footnotes are extracted by md2pdf they become empty shells.

_BARE_SECTION_RE = re.compile(
    r'(\n#{1,3}[ \t]+(?:Notes?|References?|Footnotes?)[ \t]*\n(?:[ \t]*\n)*)',
    re.IGNORECASE,
)


def _transform_strip_bare_sections(text: str) -> list[tuple[str, str, str, int, str]]:
    confidence = _hconfidence("strip_bare_sections")
    hunks = []
    for m in _BARE_SECTION_RE.finditer(text):
        before = m.group(1)
        after  = '\n'
        hunks.append(('strip-sections', before, after, confidence, ''))
    return hunks


# ── Transform 3: Pull-quote normalisation ────────────────────────────────────
#
# 3a. Missing space after pipe  (|"text" → | "text")
#     Confidence: style config "pull_quote_spacing.confidence"       (default 99%)
# 3b. Wrong attribution capitalisation — normalise to style convention
#     Confidence: style config "pull_quote_attribution.confidence"   (default 90%)
#     Style:      style config "pull_quote_attribution.style"        (default "source:")
# 3c. Advisory: pull-quote line missing source attribution
#     Confidence: style config "pull_quote_missing_source.confidence" (default 30%)

# Pull-quote blocks: two consecutive | lines where the second is the source
_PULLQUOTE_SOURCE_RE = re.compile(r'^\| (?:source:|Source:)', re.IGNORECASE)


def _transform_pullquotes(text: str) -> list[tuple[str, str, str, int, str]]:
    # Read conventions from loaded style config
    canonical_source  = _hconf("pull_quote_attribution").get("style", "source:")
    wrong_source      = "Source:" if canonical_source == "source:" else "source:"
    conf_spacing      = _hconfidence("pull_quote_spacing")
    conf_cap          = _hconfidence("pull_quote_attribution")
    conf_missing      = _hconfidence("pull_quote_missing_source")

    # Content lines are those that are NOT attribution lines
    content_re = re.compile(
        r'^\| (?!' + re.escape(canonical_source) + r')(?!' + re.escape(wrong_source) + r')',
        re.IGNORECASE,
    )

    hunks = []
    lines = text.splitlines(keepends=True)

    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip('\n')

        # 3a — missing space after pipe (skip table separator/row lines)
        if re.match(r'^\|(?![ \t]|$|.*\|[ \t]*$)', line):
            content = line[1:]
            before  = line
            after   = f'| {content}'
            if before != after:
                hunks.append(('pullquotes-spacing', before, after, conf_spacing, ''))

        # 3b — wrong attribution capitalisation (e.g. "Source:" when style is "source:")
        elif line.startswith(f'| {wrong_source}'):
            content = line[len(f'| {wrong_source}'):]
            before  = line
            after   = f'| {canonical_source}{content}'
            hunks.append(('pullquotes-capitalisation', before, after, conf_cap, ''))

        # 3c — pull-quote content line with no following source line
        elif content_re.match(line) and not re.match(r'^\|.*\|', line):
            next_line = lines[i + 1].rstrip('\n') if i + 1 < len(lines) else ''
            if not _PULLQUOTE_SOURCE_RE.match(next_line):
                hunks.append((
                    'pullquotes-missing-source', line, line, conf_missing,
                    f'Pull-quote has no following `| {canonical_source}` attribution line.',
                ))

    return hunks


# ── Transform 4: Consistency suggestions ─────────────────────────────────────
#
# These use Before/After like all other suggestions.
# Confidence values are below 50% → Treatment: Review by default.
# The author can raise confidence (or change Treatment to Apply) in the file.

def _advisory_et_al(text: str) -> list[tuple[str, str, str, int, str]]:
    """
    et al. not in italics — one consolidated suggestion showing the first
    occurrence as Before/After, with a note that it applies throughout.
    Confidence from style config "et_al_italics.confidence" (default 40%).
    """
    confidence = _hconfidence("et_al_italics")
    pat = re.compile(r'(?<!\*)\bet al\.(?!\*)')
    lines = text.splitlines()
    for line in lines:
        if line.startswith('[^'):
            continue  # skip footnote definitions
        m = pat.search(line)
        if m:
            before = 'et al.'
            after  = '*et al.*'
            count  = len(pat.findall(text))
            note   = (
                f'{count} occurrence(s) of `et al.` found. '
                'This suggestion replaces all of them. '
                'Exception: leave plain in footnote definitions if your citation style requires it.'
            )
            return [('consistency-et-al', before, after, confidence, note)]
    return []


def _advisory_mixed_apostrophes(text: str) -> list[tuple[str, str, str, int, str]]:
    """
    Mixed straight/curly apostrophes.
    Confidence from style config "apostrophe_consistency.confidence" (default 35%).
    """
    confidence = _hconfidence("apostrophe_consistency")
    # U+2019 RIGHT SINGLE QUOTATION MARK — written as escape to survive editors
    CURLY_APOS = "\u2019"
    has_straight = bool(re.search(r"(?<=[a-zA-Z])'(?=[a-zA-Z])", text))
    has_curly    = bool(CURLY_APOS in text)
    if not (has_straight and has_curly):
        return []
    m = re.search(r"(?<=[a-zA-Z])'(?=[a-zA-Z])", text)
    start = max(0, m.start() - 20)
    excerpt_before = text[start:m.start() + 20].splitlines()[0]
    excerpt_after  = excerpt_before.replace("'", CURLY_APOS)
    note = (
        "Document mixes straight (\') and curly (\u2019) apostrophes. "
        "Before/After shows one example. Apply globally in your editor "
        "(Edit \u2192 Find & Replace, enable regex: "
        "s/(?<=[a-zA-Z])\'(?=[a-zA-Z])/\u2019/g)."
    )
    return [("consistency-apostrophe", excerpt_before, excerpt_after, confidence, note)]

def _advisory_pull_quote_style(text: str) -> list[tuple[str, str, str, int, str]]:
    """
    Pull-quotes without opening quote mark.
    Confidence from style config "pull_quote_style_consistency.confidence" (default 30%).
    Unquoted pull-quotes are often intentional (paraphrase, narrative summary).
    """
    confidence = _hconfidence("pull_quote_style_consistency")
    # quote chars: straight " ' and curly “ ” ‘ ’
    _OPEN_QUOTES = '"\'“”‘’'
    lines = text.splitlines()
    no_quote_lines = []
    for line in lines:
        if re.match(r"^\| [Ss]ource:", line):
            continue
        if re.match(r"^\| ", line) and len(line) > 2 and line[2] in _OPEN_QUOTES:
            continue
        if re.match(r"^\|[ \t]", line) and not re.match(r"^\|.*\|", line):
            no_quote_lines.append(line.strip())
    if not no_quote_lines:
        return []
    example = no_quote_lines[0]
    after = example[:2] + '"' + example[2:] + '"'
    note = (
        f"{len(no_quote_lines)} pull-quote line(s) open without a quotation mark. "
        "Before/After shows the first example. Verify each is intentional or a direct quote."
    )
    return [("consistency-pullquote-style", example, after, confidence, note)]

ADVISORY_FNS = [
    _advisory_et_al,
    _advisory_mixed_apostrophes,
    _advisory_pull_quote_style,
]


# ── Hunk collection & application ────────────────────────────────────────────

TRANSFORM_FNS: list[tuple[str, callable]] = [
    ('bold-headings',  _transform_bold_headings),
    ('strip-sections', _transform_strip_bare_sections),
    ('pullquotes',     _transform_pullquotes),
]


def collect_hunks(
    text: str,
    skip: list[str] | None = None,
    include_advisory: bool = True,
) -> list[tuple[str, str, str, int, str]]:
    """
    Run all transforms and advisory checks.
    Returns list of (label, before, after, confidence, note).
    """
    skip = skip or []
    all_hunks: list[tuple[str, str, str, int, str]] = []

    for name, fn in TRANSFORM_FNS:
        if name not in skip:
            all_hunks.extend(fn(text))

    if include_advisory:
        for fn in ADVISORY_FNS:
            all_hunks.extend(fn(text))

    # Deduplicate on 'before'
    seen: set[str] = set()
    deduped = []
    for item in all_hunks:
        before = item[1]
        if before not in seen:
            seen.add(before)
            deduped.append(item)

    return deduped


def apply_hunks(text: str, hunks: list[tuple[str, str]]) -> str:
    """Apply (before, after) substitutions in order."""
    for before, after in hunks:
        text = text.replace(before, after)
    return text


# ── Review document ───────────────────────────────────────────────────────────

_SECTION_HEADER = """\
## {title}

*Treatment: **{treatment}** — confidence ≥ {threshold}% | {desc}*

"""

def build_review_document(src_path: Path, hunks: list[tuple[str, str, str, int, str]]) -> str:
    """
    Organise suggestions into 4 sections:
      1. Deterministic — Apply    (mechanical rules, confidence ≥ 50%)
      2. Deterministic — Review   (mechanical rules, confidence < 50%)
      3. Claude — Apply           (Claude-flagged, confidence ≥ 50%)
      4. Claude — Review          (Claude-flagged, confidence < 50%)

    Claude hunks are identified by label starting with 'claude-'.
    """
    header = [
        f"# md_harden review — `{src_path.name}`\n",
        "Each suggestion has a **Confidence** score and a **Treatment**.\n"
        "- **Apply**: will be applied on `--apply` unless you delete the block or change Treatment to `Review`.\n"
        "- **Review**: will be skipped unless you change Treatment to `Apply`.\n"
        "- To adjust a suggestion: edit the `After` block.\n"
        "- To reject a suggestion: delete the entire block (from `## Suggestion` to `---`).\n\n"
        f"When done:\n"
        f"```\npython md_harden/md_harden.py {src_path.name} --apply {src_path.stem}_review.md\n```\n",
    ]

    if not hunks:
        return '\n'.join(header) + "\n*No changes suggested — document is already clean.*\n"

    # Partition into 4 buckets
    det_apply:    list[tuple] = []
    det_review:   list[tuple] = []
    claude_apply: list[tuple] = []
    claude_review_: list[tuple] = []

    for item in hunks:
        label, before, after, confidence, note = item
        is_claude = label.startswith('claude-')
        is_apply  = confidence >= APPLY_THRESHOLD
        if is_claude:
            (claude_apply if is_apply else claude_review_).append(item)
        else:
            (det_apply if is_apply else det_review).append(item)

    sections = [
        ("1. Deterministic — Apply",
         "Apply",
         "mechanical rules with high confidence; safe to apply automatically",
         det_apply),
        ("2. Deterministic — Review",
         "Review",
         "lower-confidence rules; verify each before applying",
         det_review),
        ("3. Claude — Apply",
         "Apply",
         "Claude-flagged issues with confidence ≥ 50%",
         claude_apply),
        ("4. Claude — Review",
         "Review",
         "Claude-flagged issues needing human judgement",
         claude_review_),
    ]

    out = '\n'.join(header)
    n = 0
    for title, treatment, desc, bucket in sections:
        if not bucket:
            continue
        out += f"\n---\n\n# {title}\n\n"
        out += f"*{desc}*\n\n"
        for item in bucket:
            label, before, after, confidence, note = item
            n += 1
            out += _make_review_block(n, label, before, after, confidence, note)
            out += _REVIEW_SEP

    return out


# ── Claude API semantic review ────────────────────────────────────────────────

_CLAUDE_SYSTEM = textwrap.dedent("""\
    You are a Markdown copy-editor for long-form analytical articles.
    You will receive a Markdown document and must return ONLY a JSON object
    with a single key "issues", containing a list of objects, each with:
      - "line":       approximate line number (int)
      - "type":       short category string (e.g. "italics", "quotes",
                      "formatting", "pull-quote", "footnote", "capitalisation")
      - "before":     verbatim excerpt from the document that has the problem (≤120 chars)
      - "after":      corrected version of that same excerpt (≤120 chars)
      - "note":       concise description of the problem
      - "confidence": integer 0–100 — how confident you are this is a real problem
                      (90+ = clear mechanical error; 60–89 = likely issue; <60 = borderline)

    Focus on:
    - Inconsistent use of italics for paper/journal titles (e.g. *Lancet* vs Lancet)
    - Inconsistent formatting of the same paper name (italic vs backtick vs plain)
    - Mixed quote styles (straight " vs curly ")
    - et al. not in italics when used as part of an in-text citation
    - Pull-quote attribution style: the convention is lowercase `source:` (not `Source:`).
      Flag `Source:` occurrences as needing correction to `source:`. Do NOT flag `source:` as wrong.
    - Orphaned footnote references ([^key] with no definition, or vice versa)
    - Inconsistent capitalisation of recurring proper nouns

    CRITICAL JSON RULES — the response will be parsed by json.loads():
    - All string values must use double quotes.
    - Single quotes MUST NOT be backslash-escaped. Write ' not \'.
    - Double quotes inside a string value must be escaped as \\".
    - Newlines inside string values must be escaped as \\n.
    - Keep "before" and "after" to a single line each (no raw newlines).
    - Avoid including Markdown pipe (|) or quote characters in "before"/"after";
      use the plain text content of the line instead.
    - Return {"issues": []} if the document is clean.
    - Do NOT add any text outside the JSON object.
    - Limit output to the 30 most important issues. Do not pad with minor ones.
      It is better to return 20 complete, well-formed issues than 40 truncated ones.
""")


def _sanitise_claude_json(raw: str) -> str:
    """
    Fix all invalid JSON escape sequences Claude emits, reporting every
    problem found before returning the sanitised string.

    JSON only allows these backslash escapes: \\\\ \\" \\/ \\b \\f \\n \\r \\t \\uXXXX
    Everything else (e.g. \\' \\. \\s \\* ) is illegal and must be unescaped.
    """
    # Valid JSON escape characters after a backslash (the char that follows \)
    _VALID = {'"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'}
    problems: list[str] = []
    out: list[str] = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == '\\' and i + 1 < len(raw):
            nxt = raw[i + 1]
            if nxt in _VALID:
                out.append(ch)       # keep valid escape as-is
                out.append(nxt)
                i += 2
            else:
                # Invalid escape — record it and drop the backslash
                context = raw[max(0, i - 40):i + 40].replace('\n', '\\n')
                problems.append(f"  char {i}: invalid escape \\{nxt!r} — context: {context!r}")
                out.append(nxt)      # keep the character, drop the backslash
                i += 2
        else:
            out.append(ch)
            i += 1

    if problems:
        print(f"  Claude review: {len(problems)} invalid escape(s) fixed:", flush=True)
        for p in problems:
            print(p, flush=True)

    return ''.join(out)


def _parse_claude_json(raw: str) -> list[dict]:
    """
    Parse the JSON response from Claude.  Falls back to extracting individual
    issue objects if the outer document is malformed (e.g. unescaped quotes
    in a before/after field broke the overall parse).

    Also writes the raw response to /tmp/md_harden_claude_raw.json for
    debugging if parsing fails.
    """
    # Try clean parse first
    try:
        return json.loads(raw).get("issues", [])
    except json.JSONDecodeError as first_err:
        pass

    # Save raw for debugging
    debug_path = Path("/tmp/md_harden_claude_raw.json")
    try:
        debug_path.write_text(raw, encoding="utf-8")
        print(f"  Claude review: JSON parse failed — raw response saved to {debug_path}",
              file=sys.stderr, flush=True)
    except Exception:
        pass

    # Fallback: extract individual {...} objects and parse each separately
    issues: list[dict] = []
    # Find all top-level objects inside the "issues" array
    obj_re = re.compile(r'\{[^{}]+\}', re.DOTALL)
    for m in obj_re.finditer(raw):
        snippet = m.group(0)
        try:
            obj = json.loads(snippet)
            if "before" in obj:
                issues.append(obj)
        except json.JSONDecodeError:
            # Try fixing common unescaped newlines inside strings
            fixed = re.sub(r'(?<!\\)\n', r'\\n', snippet)
            try:
                obj = json.loads(fixed)
                if "before" in obj:
                    issues.append(obj)
            except json.JSONDecodeError:
                continue  # skip this issue, move on

    if issues:
        print(f"  Claude review: recovered {len(issues)} issue(s) via fallback parser.",
              flush=True)
    else:
        print("  Claude review: could not recover any issues. "
              f"Inspect {debug_path} for the raw response.", file=sys.stderr)
    return issues


# Target chunk size in characters. ~60K chars ≈ ~15K tokens input, leaving
# ample headroom in a 200K token context window and keeping output well under
# 8K tokens even for issue-dense sections.
_CHUNK_TARGET_CHARS = 60_000
_CHUNK_MAX_ISSUES   = 30   # per chunk; matches the prompt instruction


def _chunk_markdown(text: str, target: int = _CHUNK_TARGET_CHARS) -> list[str]:
    """
    Split Markdown at H1/H2 heading boundaries into chunks of roughly
    `target` characters each.  A heading that would push a chunk over the
    limit starts a new chunk instead.  Frontmatter (--- block) stays with
    the first chunk.
    """
    heading_re = re.compile(r'^#{1,2} ', re.MULTILINE)
    # Find all heading positions
    splits = [m.start() for m in heading_re.finditer(text)]
    if not splits:
        # No headings — split on blank lines near target boundaries
        return _chunk_on_blank_lines(text, target)

    chunks: list[str] = []
    current_start = 0
    current_len   = 0

    for split in splits:
        segment_len = split - current_start
        if current_len + segment_len > target and current_len > 0:
            chunks.append(text[current_start:split])
            current_start = split
            current_len   = 0
        current_len += segment_len

    # Last chunk
    chunks.append(text[current_start:])
    return [c for c in chunks if c.strip()]


def _chunk_on_blank_lines(text: str, target: int) -> list[str]:
    """Fallback: split on blank lines near target boundaries."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + target, len(text))
        if end < len(text):
            # Walk back to nearest blank line
            blank = text.rfind('\n\n', start, end)
            if blank > start:
                end = blank + 2
        chunks.append(text[start:end])
        start = end
    return chunks


_CHUNK_OUTPUT_TRUNCATED = object()  # sentinel returned when max_tokens hit


def _claude_review_chunk(
    client: object,
    chunk: str,
    chunk_n: int,
    total: int,
    line_offset: int,
) -> "list[dict] | object":
    """Send one chunk to Claude and return raw issue dicts.

    Returns the module-level sentinel _CHUNK_OUTPUT_TRUNCATED when the
    response was cut off by the output token limit, so the caller can
    re-split the chunk and retry.
    """
    n_chars = len(chunk)
    n_lines = chunk.count('\n')
    print(
        f"  Claude review: chunk {chunk_n}/{total} — "
        f"{n_lines} lines ({n_chars:,} chars, starting at line ~{line_offset})...",
        flush=True,
    )
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=_CLAUDE_SYSTEM,
            messages=[{"role": "user", "content": chunk}],
        )
        stop_reason = response.stop_reason
        n_out = response.usage.output_tokens
        print(f"  Claude review: chunk {chunk_n}/{total} received "
              f"({n_out} tokens, stop={stop_reason})", flush=True)
        if stop_reason == "max_tokens":
            print(f"  Claude review: chunk {chunk_n} output truncated — "
                  f"will re-split and retry.", file=sys.stderr, flush=True)
            return _CHUNK_OUTPUT_TRUNCATED
        raw = response.content[0].text.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        raw = _sanitise_claude_json(raw)

        # Adjust line numbers by offset
        issues = _parse_claude_json(raw)
        for iss in issues:
            if "line" in iss and isinstance(iss["line"], int):
                iss["line"] += line_offset
        return issues
    except Exception as exc:  # noqa: BLE001
        print(f"  Claude review: chunk {chunk_n} failed — {exc}", file=sys.stderr)
        return []


def _claude_review(text: str) -> list[tuple[str, str, str, int, str]]:
    """
    Call Claude API and return hunks in standard (label, before, after, confidence, note) form.
    Label is prefixed 'claude-' so build_review_document puts them in the Claude sections.
    Automatically chunks large documents to stay within output token limits.
    """
    try:
        import anthropic
    except ImportError:
        print(
            "md_harden: --claude requires the anthropic package.\n"
            "  conda install -c conda-forge anthropic",
            file=sys.stderr,
        )
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "md_harden: ANTHROPIC_API_KEY not set. Skipping Claude review.",
            file=sys.stderr,
        )
        return []

    client = anthropic.Anthropic(api_key=api_key)

    chunks = _chunk_markdown(text)
    total  = len(chunks)
    n_chars = len(text)
    print(
        f"  Claude review: {n_chars:,} chars → {total} chunk(s) "
        f"(target {_CHUNK_TARGET_CHARS:,} chars/chunk)",
        flush=True,
    )

    # Queue of (chunk_text, line_offset_at_chunk_start).
    # Truncated chunks are re-split at half size and re-queued.
    # chunk_n/total are cosmetic labels only; recomputed when queue grows.
    queue: list[tuple[str, int]] = [(c, 0) for c in chunks]
    # Compute cumulative line offsets
    line_offset = 0
    queue_with_offsets: list[tuple[str, int]] = []
    for c in chunks:
        queue_with_offsets.append((c, line_offset))
        line_offset += c.count('\n')
    queue = queue_with_offsets

    all_issues: list[dict] = []
    processed = 0
    while queue:
        chunk, chunk_line_offset = queue.pop(0)
        processed += 1
        total_display = processed + len(queue)
        result = _claude_review_chunk(
            client, chunk, processed, total_display, chunk_line_offset
        )
        if result is _CHUNK_OUTPUT_TRUNCATED:
            # Re-split this chunk at half its current size and push to front
            half = len(chunk) // 2
            sub_chunks = _chunk_on_blank_lines(chunk, half)
            if len(sub_chunks) < 2:
                # Can't split further — accept truncated parse by re-sending
                # with explicit truncation warning and collecting what we can
                print(f"  Claude review: chunk cannot be split further "
                      f"({len(chunk):,} chars). Collecting partial results.",
                      file=sys.stderr, flush=True)
                # Re-call but treat any stop as acceptable
                try:
                    response = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=8192,
                        system=_CLAUDE_SYSTEM,
                        messages=[{"role": "user", "content": chunk}],
                    )
                    raw = response.content[0].text.strip()
                    raw = re.sub(r'^```(?:json)?\s*', '', raw)
                    raw = re.sub(r'\s*```$', '', raw)
                    raw = _sanitise_claude_json(raw)
                    partial = _parse_claude_json(raw)
                    for iss in partial:
                        if "line" in iss and isinstance(iss["line"], int):
                            iss["line"] += chunk_line_offset
                    all_issues.extend(partial)
                except Exception as exc:
                    print(f"  Claude review: partial collect failed — {exc}",
                          file=sys.stderr)
            else:
                # Re-queue sub-chunks at the front (preserve order)
                sub_offset = chunk_line_offset
                sub_queue: list[tuple[str, int]] = []
                for sc in sub_chunks:
                    sub_queue.append((sc, sub_offset))
                    sub_offset += sc.count('\n')
                queue = sub_queue + queue
                processed -= 1  # this chunk didn't count
        else:
            all_issues.extend(result)

    hunks: list[tuple[str, str, str, int, str]] = []
    seen_before: set[str] = set()
    for iss in all_issues:
        before     = iss.get("before", "").strip()
        after      = iss.get("after", "").strip()
        note       = iss.get("note", "")
        confidence = int(iss.get("confidence", 50))
        tag        = iss.get("type", "issue")
        label      = f"claude-{tag}"
        if not before or before == after:
            continue
        if before in seen_before:
            continue
        seen_before.add(before)
        hunks.append((label, before, after, confidence, note))
    return hunks


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Harden a Markdown file for use with md2pdf.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Workflow:
              1. python md_harden.py article.md --review
                 → writes article_review.md (open in VSCode Preview)
              2. Delete/edit suggestions; advisory blocks are informational only
              3. python md_harden.py article.md --apply article_review.md
                 → writes article_hardened.md

            Direct mode (apply all transforms immediately):
              python md_harden.py article.md
              python md_harden.py article.md --dry-run
        """),
    )
    parser.add_argument("input", metavar="FILE.md", help="Input Markdown file")
    parser.add_argument(
        "--review", action="store_true",
        help="Generate a review document (<stem>_review.md)",
    )
    parser.add_argument(
        "--apply", metavar="REVIEW.md",
        help="Apply surviving suggestions from a review document",
    )
    parser.add_argument(
        "--output", "-o", metavar="OUT.md",
        help="Output path (overrides default naming)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="(Direct mode) Print unified diff but do not write any file",
    )
    parser.add_argument(
        "--skip", metavar="TRANSFORM", action="append", default=[],
        help="Skip a named transform: bold-headings, strip-sections, pullquotes",
    )
    parser.add_argument(
        "--no-advisory", action="store_true",
        help="Suppress advisory consistency checks in the review document",
    )
    parser.add_argument(
        "--claude", action="store_true",
        help="Add Claude API semantic review section (requires ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--style", metavar="STYLE",
        help=(
            "Style name to load conventions from "
            "(e.g. intelligence, academic, magazine, thinktank). "
            "Reads md_to_pdf/styles/<STYLE>.json for hardening rules."
        ),
    )
    args = parser.parse_args()

    # Load style config — must happen before any transform runs
    global _HCFG
    _HCFG = _load_style_config(args.style)

    src = Path(args.input).resolve()
    if not src.exists():
        print(f"md_harden: file not found: {src}", file=sys.stderr)
        sys.exit(1)

    original = src.read_text(encoding="utf-8")

    # ── --review mode ────────────────────────────────────────────────────────
    if args.review:
        hunks = collect_hunks(
            original,
            skip=args.skip,
            include_advisory=not args.no_advisory,
        )
        if args.claude:
            hunks += _claude_review(original)

        review_text = build_review_document(src, hunks)
        out_path = (
            Path(args.output) if args.output
            else src.with_name(f"{src.stem}_review.md")
        )
        out_path.write_text(review_text, encoding="utf-8")

        n_det_apply  = sum(1 for l, _, _, c, _ in hunks if not l.startswith('claude-') and c >= APPLY_THRESHOLD)
        n_det_review = sum(1 for l, _, _, c, _ in hunks if not l.startswith('claude-') and c < APPLY_THRESHOLD)
        n_cl_apply   = sum(1 for l, _, _, c, _ in hunks if l.startswith('claude-') and c >= APPLY_THRESHOLD)
        n_cl_review  = sum(1 for l, _, _, c, _ in hunks if l.startswith('claude-') and c < APPLY_THRESHOLD)
        print(f"→  {out_path}")
        print(f"   Deterministic — Apply: {n_det_apply}  Review: {n_det_review}")
        if args.claude:
            print(f"   Claude        — Apply: {n_cl_apply}  Review: {n_cl_review}")
        print(f"   Run: python md_harden/md_harden.py {src.name} --apply {out_path.name}")
        return

    # ── --apply mode ─────────────────────────────────────────────────────────
    if args.apply:
        review_path = Path(args.apply).resolve()
        if not review_path.exists():
            print(f"md_harden: review file not found: {review_path}", file=sys.stderr)
            sys.exit(1)

        review_text = review_path.read_text(encoding="utf-8")
        suggestions = _parse_review_file(review_text)
        hardened    = apply_hunks(original, suggestions)

        out_path = (
            Path(args.output) if args.output
            else src.with_name(f"{src.stem}_hardened.md")
        )
        out_path.write_text(hardened, encoding="utf-8")

        diff = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            hardened.splitlines(keepends=True),
            fromfile=str(src),
            tofile=str(out_path),
            lineterm="",
        ))
        if diff:
            print("".join(diff))
        else:
            print("md_harden: no changes applied (all suggestions were removed).")
        print(f"\n→  Written: {out_path}  ({len(suggestions)} suggestion(s) applied)")
        return

    # ── Direct mode ───────────────────────────────────────────────────────────
    hunks = collect_hunks(original, skip=args.skip, include_advisory=False)
    hardened = apply_hunks(original, [(b, a) for l, b, a, c, n in hunks if c >= APPLY_THRESHOLD])

    diff = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        hardened.splitlines(keepends=True),
        fromfile=str(src),
        tofile=args.output or f"{src.stem}_hardened.md",
        lineterm="",
    ))
    if diff:
        print("".join(diff))
    else:
        print("md_harden: no changes — document is already clean.")

    if not args.dry_run:
        out_path = (
            Path(args.output) if args.output
            else src.with_name(f"{src.stem}_hardened.md")
        )
        out_path.write_text(hardened, encoding="utf-8")
        print(f"\n→  Written: {out_path}")


if __name__ == "__main__":
    main()
