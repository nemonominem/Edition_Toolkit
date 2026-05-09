#!/usr/bin/env python3
"""
md_to_pdf.py — Convert Markdown to PDF via WeasyPrint.

See README.md in this folder for full setup and usage instructions.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# style.css lives next to this script
SCRIPT_DIR = Path(__file__).parent
DEFAULT_CSS_PATH = SCRIPT_DIR / 'style.css'


# ---------------------------------------------------------------------------
# Mermaid rendering
# ---------------------------------------------------------------------------

def find_mmdc() -> str | None:
    """Return path to mmdc CLI if available, else None."""
    found = shutil.which('mmdc')
    if found:
        return found
    for candidate in [
        os.path.expanduser('~/.npm/bin/mmdc'),
        os.path.expanduser('~/.npm-global/bin/mmdc'),
        '/usr/local/bin/mmdc',
        '/opt/homebrew/bin/mmdc',
    ]:
        if os.path.isfile(candidate):
            return candidate
    return None


def render_mermaid_blocks(text: str, out_dir: Path) -> str:
    """
    Replace ```mermaid...``` fenced blocks with either:
    - An <img> tag pointing at a rendered PNG (when mmdc is available), or
    - A styled <div class="mermaid-placeholder"> notice.
    PNG files are written into out_dir (typically the document's images/ folder).
    """
    mmdc = find_mmdc()
    counter = [0]

    def replace_block(m: re.Match) -> str:
        diagram_src = m.group(1).strip()
        counter[0] += 1
        idx = counter[0]

        if not mmdc:
            return (
                f'<div class="mermaid-placeholder">'
                f'[Diagram {idx} — install mmdc to render: '
                f'npm install -g @mermaid-js/mermaid-cli]'
                f'</div>'
            )

        with tempfile.NamedTemporaryFile(suffix='.mmd', mode='w',
                                         delete=False, encoding='utf-8') as f:
            f.write(diagram_src)
            mmd_path = f.name

        png_name = f'_mermaid_{idx}.png'
        png_path = out_dir / png_name

        try:
            result = subprocess.run(
                [mmdc, '-i', mmd_path, '-o', str(png_path),
                 '-b', 'white', '--width', '1200'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0 or not png_path.exists():
                print(f"  [mermaid] Warning: diagram {idx} failed: {result.stderr[:200]}",
                      file=sys.stderr)
                return (
                    f'<div class="mermaid-placeholder">'
                    f'[Diagram {idx} rendering failed]'
                    f'</div>'
                )
            print(f"  [mermaid] Rendered diagram {idx} → {png_name}")
            return (
                f'<img src="{png_path}" alt="Network diagram {idx}" '
                f'style="max-width:100%;display:block;margin:1em auto;">'
            )
        except Exception as e:
            print(f"  [mermaid] Exception on diagram {idx}: {e}", file=sys.stderr)
            return (
                f'<div class="mermaid-placeholder">'
                f'[Diagram {idx} — rendering error]'
                f'</div>'
            )
        finally:
            os.unlink(mmd_path)

    return re.sub(r'```mermaid\n(.*?)```', replace_block, text, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# GFM callout conversion  (> [!NOTE], > [!WARNING], etc.)
# ---------------------------------------------------------------------------

def md_inline(src: str) -> str:
    """
    Convert a Markdown fragment to HTML.
    Footnote references ([^key]) are temporarily removed before conversion
    and reattached afterwards as raw tokens, so the outer document-level
    footnote pass can resolve them with correct numbering.
    """
    import markdown

    # Extract footnote refs and replace with placeholders
    refs = []
    def stash_ref(m):
        refs.append(m.group(0))
        return f'\x00FNREF{len(refs)-1}\x00'

    src_stashed = re.sub(r'\[\^[^\]]+\](?!:)', stash_ref, src)

    html = markdown.markdown(
        src_stashed,
        extensions=['tables', 'fenced_code', 'attr_list', 'def_list', 'abbr', 'smarty'],
    )

    # Restore footnote refs
    for i, ref in enumerate(refs):
        html = html.replace(f'\x00FNREF{i}\x00', ref)

    return html


def convert_gfm_callouts(text: str) -> str:
    """
    Convert GitHub-Flavoured Markdown callout blocks to styled HTML divs.

        > [!NOTE]
        > Body text here.

    becomes:

        <div class="callout callout-note">
        <p class="callout-label">Note</p>
        <p>Body text here.</p>
        </div>

    Supported types: NOTE, TIP, IMPORTANT, WARNING, CAUTION.
    """
    LABELS = {
        'NOTE':      'Note',
        'TIP':       'Tip',
        'IMPORTANT': 'Important',
        'WARNING':   'Warning',
        'CAUTION':   'Caution',
    }

    def replace_callout(m: re.Match) -> str:
        kind = m.group(1).upper()
        label = LABELS.get(kind, kind.capitalize())
        css_class = kind.lower()
        # Strip leading "> " or ">" from every body line
        body_lines = []
        for line in m.group(2).splitlines():
            if line.startswith('> '):
                body_lines.append(line[2:])
            elif line == '>':
                body_lines.append('')       # blank line → paragraph break
            else:
                body_lines.append(line)
        body_md = '\n'.join(body_lines).strip()
        body_html = md_inline(body_md)
        return (
            f'<div class="callout callout-{css_class}">\n'
            f'<p class="callout-label">{label}</p>\n'
            f'{body_html}\n'
            f'</div>'
        )

    # Match the marker line + every subsequent line that starts with ">" (including blank ">")
    return re.sub(
        r'> \[!(' + '|'.join(LABELS) + r')\]\n((?:>[ \t]?.*\n?)*)',
        replace_callout,
        text,
        flags=re.IGNORECASE,
    )


# ---------------------------------------------------------------------------
# Pull-quote conversion
# ---------------------------------------------------------------------------

def convert_pullquotes(text: str) -> str:
    """
    Convert the document's pipe-prefixed pull-quote convention to proper HTML
    blockquotes so python-markdown's table parser never touches them.

    Convention in the source:
        | "Quote text."[^fn]
        | source: Attribution line.

    Rendered as:
        <blockquote>
          <p>"Quote text."<sup>...</sup></p>
          <cite>Attribution line.</cite>
        </blockquote>

    Rules:
    - A pull-quote block is one or more consecutive lines starting with "| ".
    - The LAST such line, if it starts with "| source:", becomes a <cite>.
    - All preceding lines become the blockquote body.
    - Footnote markers ([^key]) are preserved as-is for the footnote extension.
    """
    def replace_block(m: re.Match) -> str:
        raw = m.group(0)
        lines = [l[2:] for l in raw.splitlines()]  # strip leading "| "

        # Split off the source attribution line if present
        if lines and lines[-1].lower().startswith('source:'):
            body_lines = lines[:-1]
            source = lines[-1][len('source:'):].strip()
        else:
            body_lines = lines
            source = ''

        body = ' '.join(body_lines).strip()

        # Pre-render body and source through md_inline() — footnote refs are
        # stashed and restored so the outer pass can number them correctly.
        # We cannot rely on python-markdown processing Markdown inside a <div>.
        body_html = md_inline(body)
        # Strip the outer <p>...</p> that md_inline adds so blockquote styling
        # controls the paragraph spacing, not an extra wrapper.
        body_html = re.sub(r'^\s*<p>(.*)</p>\s*$', r'\1', body_html, flags=re.DOTALL)

        if source:
            source_html = re.sub(r'^\s*<p>(.*)</p>\s*$', r'\1',
                                 md_inline(source).strip(), flags=re.DOTALL)
            return (
                f'<div class="pull-quote">'
                f'<blockquote><p>{body_html}</p></blockquote>'
                f'<cite class="pull-source">{source_html}</cite>'
                f'</div>\n'
            )
        return (
            f'<div class="pull-quote">'
            f'<blockquote><p>{body_html}</p></blockquote>'
            f'</div>\n'
        )

    # Match one or more consecutive pull-quote lines.
    # Pull-quote lines start with "| " and do NOT end with "|\s*" (line-end pipe).
    # Table rows always end with a trailing "|", so this cleanly excludes them.
    return re.sub(
        r'(?m)^(?:\| (?!.*\|\s*$)[^\n]+\n?)+',
        replace_block,
        text,
    )


# ---------------------------------------------------------------------------
# Annex page breaks
# ---------------------------------------------------------------------------

def inject_annex_breaks(text: str) -> str:
    """
    Insert a CSS page-break div before every ## Annex N, ## Further Reading,
    and ## Notes heading so each starts on a fresh page.
    """
    BREAK = '<div class="annex-break"></div>\n\n'
    return re.sub(
        r'(?m)^(## (?:Annex \d+|Further Reading|Notes)\b)',
        BREAK + r'\1',
        text,
    )


# ---------------------------------------------------------------------------
# HTML conversion
# ---------------------------------------------------------------------------

def resolve_image_paths(html: str, base_dir: Path) -> str:
    """Rewrite relative img src attributes to absolute file:// URIs."""
    def rewrite(m):
        src = m.group(1)
        if src.startswith(('http://', 'https://', 'data:', 'file://')):
            return m.group(0)
        abs_path = (base_dir / src).resolve()
        return f'src="file://{abs_path}"'
    return re.sub(r'src="([^"]+)"', rewrite, html)


def md_to_html(md_path: Path) -> str:
    """Run all pre-processing steps and convert Markdown to a full HTML document."""
    import markdown
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.footnotes import FootnoteExtension
    from markdown.extensions.fenced_code import FencedCodeExtension
    from markdown.extensions.toc import TocExtension
    from markdown.extensions.attr_list import AttrListExtension
    from markdown.extensions.def_list import DefListExtension
    from markdown.extensions.abbr import AbbrExtension
    from markdown.extensions.smarty import SmartyExtension

    text = md_path.read_text(encoding='utf-8')
    text = convert_gfm_callouts(text)
    text = render_mermaid_blocks(text, md_path.parent / 'images')
    text = convert_pullquotes(text)
    text = inject_annex_breaks(text)

    extensions = [
        TableExtension(),
        FootnoteExtension(UNIQUE_IDS=True),
        FencedCodeExtension(),
        TocExtension(permalink=False),
        AttrListExtension(),
        DefListExtension(),
        AbbrExtension(),
        SmartyExtension(),
    ]
    try:
        from markdown.extensions.codehilite import CodeHiliteExtension
        extensions.append(CodeHiliteExtension(guess_lang=False))
    except Exception:
        pass

    md = markdown.Markdown(extensions=extensions)
    body_html = md.convert(text)

    # Post-process: replace any raw [^key] tokens that survived inside raw HTML
    # islands (pull-quotes, callout divs) where python-markdown's footnote
    # extension couldn't reach them.  We extract the <sup> anchors the footnote
    # extension already rendered at the normal reference sites and replay them.
    # With UNIQUE_IDS=True, footnote extension generates ids like fnref:2-key
    # where the prefix is a numeric hash.  We build a map of bare key → anchor.
    fn_anchors = {}
    # Primary: extract from rendered <sup> anchors in normal flow
    for m in re.finditer(
        r'<sup id="fnref:(\d+-)?([^"]+)"><a[^>]+href="(#fn:[^"]+)"\s*>(\d+)</a></sup>',
        body_html
    ):
        key, href, num = m.group(2), m.group(3), m.group(4)
        if key not in fn_anchors:
            fn_anchors[key] = (
                f'<sup>'
                f'<a class="footnote-ref" href="{href}">{num}</a>'
                f'</sup>'
            )
    # Fallback: for keys whose refs were entirely inside HTML islands (no <sup>
    # was emitted in normal flow), recover the footnote number from the <li> in
    # the footnote block and build the anchor from there.
    for m in re.finditer(
        r'<li id="fn:(\d+-)?([^"]+)">\s*<p>.*?<a[^>]+href="#fnref:(\d+-)?[^"]*"',
        body_html, flags=re.DOTALL
    ):
        key = m.group(2)
        if key not in fn_anchors:
            # Determine ordinal position of this <li> in the footnote list
            fn_id = m.group(0).split('"')[1]   # e.g. "fn:2-vanityfair-canofworms"
            # Count position among all <li id="fn:..."> entries
            all_fn_ids = re.findall(r'<li id="(fn:[^"]+)">', body_html)
            try:
                num = str(all_fn_ids.index(fn_id) + 1)
            except ValueError:
                continue
            href = '#' + fn_id
            fn_anchors[key] = (
                f'<sup>'
                f'<a class="footnote-ref" href="{href}">{num}</a>'
                f'</sup>'
            )

    def replace_raw_fnref(m):
        key = m.group(1)
        if key in fn_anchors:
            return fn_anchors[key]
        return m.group(0)   # unknown key — leave as-is

    body_html = re.sub(r'\[\^([^\]]+)\]', replace_raw_fnref, body_html)

    # Convert width="X%" or width="Xpx" HTML attributes to inline style so CSS max-width:100%
    # doesn't override them.  WeasyPrint honours inline style over stylesheet rules.
    def apply_width_attr(html: str) -> str:
        def rewrite(m: re.Match) -> str:
            tag = m.group(0)
            w = m.group(1)
            # Remove the width= attribute and inject as inline style instead
            tag = re.sub(r'\s*width="[^"]*"', '', tag)
            # Insert style before the closing > or />
            # Use min() to cap px widths to 100% of reading area, preserving % widths as-is
            tag = re.sub(r'\s*/?>$',
                         f' style="max-width:min({w}, 100%);width:min({w}, 100%);">', tag)
            return tag
        return re.sub(r'<img\b[^>]*\bwidth="([\d.]+(?:px|%))"[^>]*/?>',
                      rewrite, html)
    body_html = apply_width_attr(body_html)

    # Block-isolate bare <img> tags: when two or more <img> tags appear adjacent
    # (only whitespace between them) WeasyPrint lays them out inline, shrinking
    # each to a fraction of the line width regardless of their width= attribute.
    # Fix: wrap each bare <img> in its own <p> so it gets a full block context.
    # "Bare" means not already preceded on the same line by an opening block tag.
    # We do this by replacing runs of whitespace-separated <img> tags with
    # newline-separated <p><img></p> blocks.
    def isolate_images(html: str) -> str:
        # Find sequences of two or more <img> tags separated only by whitespace
        # and replace each img with a <p>-wrapped version.
        def wrap_run(m: re.Match) -> str:
            imgs = re.findall(r'<img\b[^>]*/?>',  m.group(0))
            return '\n'.join(f'<p>{img}</p>' for img in imgs) + '\n'
        return re.sub(
            r'(?:<img\b[^>]*/?>[ \t]*\n?){2,}',
            wrap_run,
            html,
        )
    body_html = isolate_images(body_html)

    # Tag image captions: a <p><em>...</em></p> immediately following an <img>.
    # python-markdown renders standalone *italic text* as <p><em>...</em></p>.
    # We add class="img-caption" so style.css can style them distinctly.
    # The pattern allows optional inline <sup>/<a> elements (footnote anchors).
    body_html = re.sub(
        r'(<img\b[^>]*/?>)\s*(<p>(<em>.*?</em>)\s*</p>)',
        lambda m: m.group(1) + '\n' + m.group(2).replace('<p>', '<p class="img-caption">'),
        body_html,
        flags=re.DOTALL,
    )

    title = md_path.stem.replace('_', ' ').replace('-', ' ')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
</head>
<body>
{body_html}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Conversion engines
# ---------------------------------------------------------------------------

def convert_weasyprint(md_path: Path, pdf_path: Path,
                       css_path: Path | None = None) -> None:
    """Primary pipeline: Markdown → HTML → PDF via WeasyPrint."""
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration

    mmdc = find_mmdc()
    if mmdc:
        print(f"  [mermaid] mmdc found at {mmdc} — diagrams will render as PNG")
    else:
        print("  [mermaid] mmdc not found — diagrams will show as placeholders")
        print("            Install: npm install -g @mermaid-js/mermaid-cli")

    print(f"  [weasyprint] Converting {md_path.name} ...")

    html_str = md_to_html(md_path)
    html_str = resolve_image_paths(html_str, md_path.parent)

    font_config = FontConfiguration()

    # Always load the bundled style.css first, then any caller-supplied override
    sheets = []
    base_css = css_path if css_path else DEFAULT_CSS_PATH
    sheets.append(CSS(filename=str(base_css), font_config=font_config))
    if css_path and css_path != DEFAULT_CSS_PATH and DEFAULT_CSS_PATH.exists():
        # If a custom file was explicitly passed, still load defaults first
        sheets = [
            CSS(filename=str(DEFAULT_CSS_PATH), font_config=font_config),
            CSS(filename=str(css_path), font_config=font_config),
        ]

    doc = HTML(string=html_str, base_url=str(md_path.parent))
    doc.write_pdf(str(pdf_path), stylesheets=sheets, font_config=font_config)
    print(f"  [weasyprint] Written to {pdf_path}")


def convert_pandoc(md_path: Path, pdf_path: Path,
                   css_path: Path | None = None) -> None:
    """Fallback pipeline: Markdown → PDF via pandoc + wkhtmltopdf."""
    import pypandoc

    print(f"  [pandoc] Converting {md_path.name} ...")
    extra_args = [
        '--standalone',
        '--pdf-engine=wkhtmltopdf',
        '--variable', 'margin-top=2.5cm',
        '--variable', 'margin-bottom=2.5cm',
        '--variable', 'margin-left=2.8cm',
        '--variable', 'margin-right=2.8cm',
        '--variable', 'fontsize=10pt',
        '--variable', 'papersize=a4',
    ]
    effective_css = css_path if css_path else DEFAULT_CSS_PATH
    if effective_css.exists():
        extra_args += ['--css', str(effective_css)]

    pypandoc.convert_file(str(md_path), 'pdf',
                          outputfile=str(pdf_path), extra_args=extra_args)
    print(f"  [pandoc] Written to {pdf_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Convert Markdown to PDF (WeasyPrint primary, pandoc fallback).'
    )
    parser.add_argument('input',
                        help='Input Markdown file (.md)')
    parser.add_argument('output', nargs='?',
                        help='Output PDF path (default: same name as input, .pdf)')
    parser.add_argument('--css',
                        help='CSS override file (layered on top of style.css)')
    parser.add_argument('--engine',
                        choices=['weasyprint', 'pandoc', 'auto'],
                        default='auto',
                        help='Rendering engine (default: auto)')
    args = parser.parse_args()

    md_path = Path(args.input).resolve()
    if not md_path.exists():
        print(f"Error: {md_path} not found.", file=sys.stderr)
        sys.exit(1)

    pdf_path = (Path(args.output).resolve()
                if args.output else md_path.with_suffix('.pdf'))
    css_path = Path(args.css).resolve() if args.css else None

    print(f"Input  : {md_path}")
    print(f"Output : {pdf_path}")
    print(f"CSS    : {css_path or DEFAULT_CSS_PATH}")

    engine = args.engine

    if engine in ('weasyprint', 'auto'):
        try:
            convert_weasyprint(md_path, pdf_path, css_path)
            return
        except ImportError:
            if engine == 'weasyprint':
                print("WeasyPrint not installed. Run:", file=sys.stderr)
                print("  conda run -n python_313x pip install markdown weasyprint",
                      file=sys.stderr)
                sys.exit(1)
            print("  WeasyPrint not available, trying pandoc...")

    if engine in ('pandoc', 'auto'):
        try:
            convert_pandoc(md_path, pdf_path, css_path)
        except ImportError:
            print("Neither WeasyPrint nor pypandoc is installed.", file=sys.stderr)
            print("Install: conda run -n python_313x pip install markdown weasyprint",
                  file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
