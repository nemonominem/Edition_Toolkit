#!/usr/bin/env python3
"""
etk_md2pdf.convert — Markdown → PDF conversion pipeline.

Entry point: main()  (registered as console_script 'md2pdf' in pyproject.toml)
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from importlib import resources as _res
from pathlib import Path

# ---------------------------------------------------------------------------
# Bundled style resolution
# ---------------------------------------------------------------------------

def _styles_dir() -> Path:
    """
    Return the Path to the package's bundled styles/ directory.
    Works for editable installs, regular installs, and zipimport (wheels).
    """
    # importlib.resources.files() is the canonical API (Python 3.9+).
    # It returns a Traversable; we convert to a real Path via as_posix /
    # a temporary extraction if necessary (wheels store files in a zip).
    pkg_files = _res.files('etk_md2pdf')
    styles = pkg_files / 'styles'
    # If styles is already a real directory (editable / regular install),
    # return it directly.  Otherwise materialise it with as_file().
    try:
        p = Path(str(styles))
        if p.is_dir():
            return p
    except TypeError:
        pass
    # Fallback: extract to a temp dir (zip-based installs)
    import atexit, tempfile as _tf
    tmp = Path(_tf.mkdtemp(prefix='etk_md2pdf_styles_'))
    atexit.register(shutil.rmtree, tmp, ignore_errors=True)
    for item in styles.iterdir():
        dest = tmp / item.name
        dest.write_bytes(item.read_bytes())
    return tmp


def resolve_css(spec: str | None) -> Path:
    """
    Resolve a --css argument to an absolute Path.

    Resolution order for a given spec string:
      1. Exact path that exists on disk           → use as-is
      2. Relative path from cwd that exists       → resolve to absolute
      3. Exact filename in bundled styles/         → use bundled
      4. 'style_<spec>.css' in bundled styles/    → use bundled
      5. '<spec>.css' in bundled styles/           → use bundled
      6. Strip leading 'style_' / trailing '.css' and retry 4+5

    If spec is None, returns the default bundled style (style_thinktank.css).
    """
    styles = _styles_dir()
    default = styles / 'style_thinktank.css'

    if spec is None:
        return default

    # 1 & 2: real filesystem path
    p = Path(spec)
    if p.exists():
        return p.resolve()
    abs_p = Path.cwd() / p
    if abs_p.exists():
        return abs_p.resolve()

    # Normalise: strip path separators (user typed a bare name)
    name = Path(spec).name  # drop any directory component

    # Build candidate filenames to try against the bundled styles dir
    stem = name
    if stem.endswith('.css'):
        stem = stem[:-4]             # strip extension
    if stem.startswith('style_'):
        bare = stem[len('style_'):]  # e.g. 'intelligence'
    else:
        bare = stem

    candidates = [
        f'{name}',                   # exact as given
        f'{stem}.css',               # with extension if missing
        f'style_{bare}.css',         # style_<bare>.css
        f'{bare}.css',               # <bare>.css
    ]

    for c in candidates:
        hit = styles / c
        if hit.exists():
            return hit.resolve()

    # Nothing found — let the caller fail with a clear message
    return Path(spec).resolve()


# Default (used in legacy md_to_pdf.py shim and --css display)
DEFAULT_CSS_PATH = resolve_css(None)


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
                f'<p class="img-block"><img src="{png_path}" alt="Diagram {idx}" '
                f'style="max-width:100%;display:block;margin:1em auto;"></p>'
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
    Convert a Markdown fragment to HTML, preserving footnote refs ([^key])
    so the outer document-level footnote pass can resolve them with correct
    numbering.
    """
    import markdown

    refs = []
    def stash_ref(m):
        refs.append(m.group(0))
        return f'\x00FNREF{len(refs)-1}\x00'

    src_stashed = re.sub(r'\[\^[^\]]+\](?!:)', stash_ref, src)
    html = markdown.markdown(
        src_stashed,
        extensions=['tables', 'fenced_code', 'attr_list', 'def_list', 'abbr', 'smarty'],
    )
    for i, ref in enumerate(refs):
        html = html.replace(f'\x00FNREF{i}\x00', ref)
    return html


def convert_gfm_callouts(text: str) -> str:
    """Convert > [!NOTE] / [!WARNING] etc. blocks to styled HTML divs."""
    LABELS = {
        'NOTE': 'Note', 'TIP': 'Tip', 'IMPORTANT': 'Important',
        'WARNING': 'Warning', 'CAUTION': 'Caution',
    }

    def replace_callout(m: re.Match) -> str:
        kind = m.group(1).upper()
        label = LABELS.get(kind, kind.capitalize())
        css_class = kind.lower()
        body_lines = []
        for line in m.group(2).splitlines():
            if line.startswith('> '):
                body_lines.append(line[2:])
            elif line == '>':
                body_lines.append('')
            else:
                body_lines.append(line)
        body_html = md_inline('\n'.join(body_lines).strip())
        return (
            f'<div class="callout callout-{css_class}">\n'
            f'<p class="callout-label">{label}</p>\n'
            f'{body_html}\n'
            f'</div>'
        )

    return re.sub(
        r'> \[!(' + '|'.join(LABELS) + r')\]\n((?:>[ \t]?.*\n?)*)',
        replace_callout, text, flags=re.IGNORECASE,
    )


# ---------------------------------------------------------------------------
# Pull-quote conversion
# ---------------------------------------------------------------------------

def convert_pullquotes(text: str) -> str:
    """
    Convert pipe-prefixed pull-quote blocks to HTML blockquotes.

        | "Quote text."[^fn]
        | source: Attribution line.
    """
    def replace_block(m: re.Match) -> str:
        lines = [l[2:] for l in m.group(0).splitlines()]
        if lines and lines[-1].lower().startswith('source:'):
            body_lines, source = lines[:-1], lines[-1][len('source:'):].strip()
        else:
            body_lines, source = lines, ''

        body_html = md_inline(' '.join(body_lines).strip())
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

    return re.sub(
        r'(?m)^(?:\| (?!.*\|\s*$)[^\n]+\n?)+',
        replace_block, text,
    )


# ---------------------------------------------------------------------------
# Annex page breaks
# ---------------------------------------------------------------------------

def inject_annex_breaks(text: str) -> str:
    """Insert CSS page-break divs before ## Annex N / Further Reading / Notes."""
    BREAK = '<div class="annex-break"></div>\n\n'
    return re.sub(
        r'(?m)^(## (?:Annex \d+|Further Reading|Notes)\b)',
        BREAK + r'\1', text,
    )


# ---------------------------------------------------------------------------
# Markdown image pre-processing
# ---------------------------------------------------------------------------

def convert_md_images(text: str) -> str:
    """
    Pre-convert Markdown image syntax to raw HTML before python-markdown
    processes the document.

    Python-Markdown does not parse ![]() inside raw HTML blocks (e.g.
    <div class="single-column">), so images inside those divs render as plain
    text.  Converting them to <img> tags first fixes this for both wrapped and
    unwrapped images.

    Two cases are distinguished:

    Standalone image — ![]() is the only non-whitespace content on its line:
        Emitted as <p><img ...></p> so it forms its own block and never appears
        as inline content inside a paragraph.  This avoids the WeasyPrint crash
        (assert BlockReplacedBox) that occurs when a block-level img lands inside
        a paragraph that also triggers a ::first-letter float (e.g. drop caps in
        column layouts).

    Inline image — ![]() appears within a line of other text:
        Emitted as a bare <img> with display:inline so it flows with surrounding
        text.

    Handles optional width attribute:
        ![alt](path){width=60%}  →  max-width:60%
        ![alt](path)             →  max-width:100%

    resolve_image_paths() later rewrites relative src values to file:// URIs
    and continues to work correctly on the output of this step.
    """
    # Pattern: optional leading whitespace, image syntax, optional {width=...},
    # optional trailing whitespace — entire line.
    STANDALONE = re.compile(
        r'^[ \t]*'
        r'!\[([^\]]*)\]\(([^)]+)\)'
        r'(?:\{width=([^}]+)\})?'
        r'[ \t]*$',
        re.MULTILINE,
    )
    # Inline pattern (used after standalone lines are already replaced)
    INLINE = re.compile(
        r'!\[([^\]]*)\]\(([^)]+)\)(?:\{width=([^}]+)\})?'
    )

    def standalone_img(m: re.Match) -> str:
        alt   = m.group(1)
        src   = m.group(2)
        width = m.group(3)
        max_w = width if width else '100%'
        # class="img-block" lets CSS drop-cap selectors exclude image paragraphs
        return (
            f'<p class="img-block"><img src="{src}" alt="{alt}" '
            f'style="max-width:{max_w};display:block;margin:0.5em auto;"></p>'
        )

    def inline_img(m: re.Match) -> str:
        alt   = m.group(1)
        src   = m.group(2)
        width = m.group(3)
        max_w = width if width else '100%'
        return (
            f'<img src="{src}" alt="{alt}" '
            f'style="max-width:{max_w};display:inline;vertical-align:middle;">'
        )

    text = STANDALONE.sub(standalone_img, text)
    text = INLINE.sub(inline_img, text)
    return text


# ---------------------------------------------------------------------------
# HTML conversion
# ---------------------------------------------------------------------------

def resolve_image_paths(html: str, base_dir: Path) -> str:
    """Rewrite relative img src attributes to absolute file:// URIs."""
    def rewrite(m):
        src = m.group(1)
        if src.startswith(('http://', 'https://', 'data:', 'file://')):
            return m.group(0)
        return f'src="file://{(base_dir / src).resolve()}"'
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
    text = convert_md_images(text)
    text = render_mermaid_blocks(text, md_path.parent / 'images')
    text = convert_pullquotes(text)
    text = inject_annex_breaks(text)

    extensions = [
        TableExtension(), FootnoteExtension(UNIQUE_IDS=True),
        FencedCodeExtension(), TocExtension(permalink=False),
        AttrListExtension(), DefListExtension(), AbbrExtension(), SmartyExtension(),
    ]
    try:
        from markdown.extensions.codehilite import CodeHiliteExtension
        extensions.append(CodeHiliteExtension(guess_lang=False))
    except Exception:
        pass

    md = markdown.Markdown(extensions=extensions)
    body_html = md.convert(text)

    # Resolve raw [^key] tokens that survived inside raw HTML islands
    fn_anchors = {}
    for m in re.finditer(
        r'<sup id="fnref:(\d+-)?([^"]+)"><a[^>]+href="(#fn:[^"]+)"\s*>(\d+)</a></sup>',
        body_html
    ):
        key, href, num = m.group(2), m.group(3), m.group(4)
        if key not in fn_anchors:
            fn_anchors[key] = f'<sup><a class="footnote-ref" href="{href}">{num}</a></sup>'

    for m in re.finditer(
        r'<li id="fn:(\d+-)?([^"]+)">\s*<p>.*?<a[^>]+href="#fnref:(\d+-)?[^"]*"',
        body_html, flags=re.DOTALL
    ):
        key = m.group(2)
        if key not in fn_anchors:
            fn_id = m.group(0).split('"')[1]
            all_fn_ids = re.findall(r'<li id="(fn:[^"]+)">', body_html)
            try:
                num = str(all_fn_ids.index(fn_id) + 1)
                fn_anchors[key] = f'<sup><a class="footnote-ref" href="#{fn_id}">{num}</a></sup>'
            except ValueError:
                continue

    body_html = re.sub(
        r'\[\^([^\]]+)\]',
        lambda m: fn_anchors.get(m.group(1), m.group(0)),
        body_html,
    )

    # width= attribute → inline style (WeasyPrint honours inline over stylesheet)
    def apply_width_attr(html: str) -> str:
        def rewrite(m: re.Match) -> str:
            tag = re.sub(r'\s*width="[^"]*"', '', m.group(0))
            w = m.group(1)
            return re.sub(r'\s*/?>$',
                           f' style="max-width:min({w}, 100%);width:min({w}, 100%);">', tag)
        return re.sub(r'<img\b[^>]*\bwidth="([\d.]+(?:px|%))"[^>]*/?>',
                       rewrite, html)
    body_html = apply_width_attr(body_html)

    # Wrap adjacent bare <img> tags in <p> blocks so WeasyPrint sizes them correctly
    def isolate_images(html: str) -> str:
        def wrap_run(m: re.Match) -> str:
            imgs = re.findall(r'<img\b[^>]*/?>',  m.group(0))
            return '\n'.join(f'<p>{img}</p>' for img in imgs) + '\n'
        return re.sub(r'(?:<img\b[^>]*/?>[ \t]*\n?){2,}', wrap_run, html)
    body_html = isolate_images(body_html)

    # Tag image captions: <p><em>…</em></p> immediately after <img>
    body_html = re.sub(
        r'(<img\b[^>]*/?>)\s*(<p>(<em>.*?</em>)\s*</p>)',
        lambda m: m.group(1) + '\n' + m.group(2).replace('<p>', '<p class="img-caption">'),
        body_html, flags=re.DOTALL,
    )

    title = md_path.stem.replace('_', ' ').replace('-', ' ')
    return (
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        f'<meta charset="utf-8">\n<title>{title}</title>\n'
        f'</head>\n<body>\n{body_html}\n</body>\n</html>'
    )


# ---------------------------------------------------------------------------
# Conversion engines
# ---------------------------------------------------------------------------

def convert_weasyprint(md_path: Path, pdf_path: Path, css_path: Path) -> None:
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
    sheets = [CSS(filename=str(css_path), font_config=font_config)]

    doc = HTML(string=html_str, base_url=str(md_path.parent))
    doc.write_pdf(str(pdf_path), stylesheets=sheets, font_config=font_config)
    print(f"  [weasyprint] Written to {pdf_path}")


def convert_pandoc(md_path: Path, pdf_path: Path, css_path: Path) -> None:
    """Fallback pipeline: Markdown → PDF via pandoc + wkhtmltopdf."""
    import pypandoc

    print(f"  [pandoc] Converting {md_path.name} ...")
    extra_args = [
        '--standalone', '--pdf-engine=wkhtmltopdf',
        '--variable', 'margin-top=2.5cm',
        '--variable', 'margin-bottom=2.5cm',
        '--variable', 'margin-left=2.8cm',
        '--variable', 'margin-right=2.8cm',
        '--variable', 'fontsize=10pt',
        '--variable', 'papersize=a4',
    ]
    if css_path.exists():
        extra_args += ['--css', str(css_path)]

    pypandoc.convert_file(str(md_path), 'pdf',
                           outputfile=str(pdf_path), extra_args=extra_args)
    print(f"  [pandoc] Written to {pdf_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _list_bundled_styles() -> list[str]:
    """Return sorted list of bundled style names (bare names, no prefix/ext)."""
    styles_dir = _styles_dir()
    names = []
    for p in sorted(styles_dir.glob('style_*.css')):
        names.append(p.stem[len('style_'):])   # strip 'style_' prefix
    return names


def main():
    parser = argparse.ArgumentParser(
        prog='md2pdf',
        description=(
            'Edition ToolKit — Convert Markdown to PDF.\n\n'
            'Bundled styles: ' + ', '.join(_list_bundled_styles())
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('input',
                        help='Input Markdown file (.md)')
    parser.add_argument('output', nargs='?',
                        help='Output PDF path (default: same name as input, .pdf)')
    parser.add_argument(
        '--css',
        metavar='STYLE',
        default=None,
        help=(
            'Style to apply. Accepts: a bare name (thinktank, academic, magazine, '
            'intelligence), style_<name>, style_<name>.css, or a full path to '
            'any .css file. Default: thinktank.'
        ),
    )
    parser.add_argument('--engine',
                        choices=['weasyprint', 'pandoc', 'auto'],
                        default='auto',
                        help='Rendering engine (default: auto)')
    parser.add_argument('--list-styles', action='store_true',
                        help='List available bundled styles and exit.')
    args = parser.parse_args()

    if args.list_styles:
        print("Bundled styles:")
        for name in _list_bundled_styles():
            print(f"  {name}")
        return

    md_path = Path(args.input).resolve()
    if not md_path.exists():
        print(f"Error: {md_path} not found.", file=sys.stderr)
        sys.exit(1)

    pdf_path = (Path(args.output).resolve()
                if args.output else md_path.with_suffix('.pdf'))

    css_path = resolve_css(args.css)
    if not css_path.exists():
        print(f"Error: CSS not found: '{args.css}'", file=sys.stderr)
        print(f"  Bundled styles: {', '.join(_list_bundled_styles())}", file=sys.stderr)
        sys.exit(1)

    print(f"Input  : {md_path}")
    print(f"Output : {pdf_path}")
    print(f"Style  : {css_path}")

    engine = args.engine

    if engine in ('weasyprint', 'auto'):
        try:
            convert_weasyprint(md_path, pdf_path, css_path)
            return
        except ImportError:
            if engine == 'weasyprint':
                print("WeasyPrint not installed.", file=sys.stderr)
                print("  conda install markdown weasyprint pygments", file=sys.stderr)
                sys.exit(1)
            print("  WeasyPrint not available, trying pandoc...")

    if engine in ('pandoc', 'auto'):
        try:
            convert_pandoc(md_path, pdf_path, css_path)
        except ImportError:
            print("Neither WeasyPrint nor pypandoc is installed.", file=sys.stderr)
            print("  conda install markdown weasyprint pygments", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
