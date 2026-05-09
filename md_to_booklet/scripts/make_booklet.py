import os
import re
import textwrap

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

DATA_DIR = 'data'
SMALL_DIR = 'build/smallpages'
IMPOSED_DIR = 'build/imposed'
FONT_DIR = 'fonts'
LATIN_SOURCE_URL = 'https://www.thelatinlibrary.com/resgestae.html'

SECTION_MARKER = '== SECTION {idx} ==\n'

# Register fonts if available
try:
    if not pdfmetrics.getFont('EBGaramond'):
        pdfmetrics.registerFont(TTFont('EBGaramond', os.path.join(FONT_DIR, 'EBGaramond-Regular.ttf')))
except Exception:
    pass
try:
    if not pdfmetrics.getFont('NotoSerif'):
        pdfmetrics.registerFont(TTFont('NotoSerif', os.path.join(FONT_DIR, 'NotoSerif-Regular.ttf')))
except Exception:
    pass

BODY_FONT = 'EBGaramond' if 'EBGaramond' in pdfmetrics.getRegisteredFontNames() else 'Times-Roman'
FALLBACK_FONT = 'NotoSerif' if 'NotoSerif' in pdfmetrics.getRegisteredFontNames() else 'Times-Roman'

# Mapping for quick transliteration/glossing.
BASIC_TRANSLATION = {
    'annos': 'years', 'undeviginti': 'nineteen', 'natus': 'born', 'exercitum': 'army',
    'privato': 'private', 'consilio': 'plan', 'impensa': 'expense', 'comparavi': 'raised',
    'res': 'affairs', 'publicam': 'the republic', 'libertatem': 'freedom', 'vindicavi': 'avenged',
    'senatus': 'senate', 'decretis': 'decrees', 'honorificis': 'honorary', 'consulibus': 'consuls',
    'consulatum': 'consulate', 'triumphavi': 'triumphs', 'curulis': 'curule', 'imperator': 'commander',
    'augustus': 'Augustus', 'qui': 'who', 'cum': 'when', 'erat': 'was', 'dedi': 'gave',
    'pax': 'peace', 'bellum': 'war', 'populus': 'people', 'Romanus': 'Roman', 'miles': 'soldier',
}

HISTORY_TEMPLATES = [
    'Augustus emphasizes military honor and constitutional legitimacy.',
    'Section reflects the Augustan narrative of restoring peace and order after civil war.',
    'References to senatorial honours and provincial benefactions.',
    'Use of numismatic and civic terms to assert public virtue (virtus, pietas).',
    'Mention of religious reforms and priestly offices at Rome.',
]


def ensure_dirs():
    for d in [DATA_DIR, SMALL_DIR, IMPOSED_DIR, FONT_DIR]:
        os.makedirs(d, exist_ok=True)


def fetch_latin_sections():
    data_file = os.path.join(DATA_DIR, 'latin.txt')
    if os.path.exists(data_file):
        sections = parse_latin_file(data_file)
        if len(sections) >= 35:
            return sections

    import requests
    resp = requests.get(LATIN_SOURCE_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    resp.raise_for_status()
    html = resp.text

    paras = re.findall(r'<p>(.*?)</p>', html, flags=re.S)
    sections = {}
    for p in paras:
        pclean = re.sub(r'<[^>]+>', '', p).strip()
        # The Latin Library uses form [1], [2], ... as section markers
        m = re.match(r'\s*\[\s*(\d+)\s*\]\s*(.*)', pclean, flags=re.S)
        if m:
            idx = int(m.group(1))
            text = m.group(2).replace('\n', ' ').strip()
            text = re.sub(r'\s+', ' ', text)
            sections[idx] = text

    if not sections:
        raise RuntimeError('Failed to parse Latin sections from source page.')

    # subscript missing section placeholders up to 35 to ensure coverage
    for idx in range(1, 36):
        if idx not in sections:
            sections[idx] = f'<<Latin text unavailable for section {idx}>>'

    # write to data/latin.txt in stable order
    with open(data_file, 'w', encoding='utf-8') as f:
        for idx in range(1, 36):
            f.write(SECTION_MARKER.format(idx=idx))
            f.write(sections[idx] + '\n\n')

    return [sections[idx] for idx in range(1, 36)]


def parse_latin_file(filepath):
    sections = []
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    chunks = re.split(r'^== SECTION (\d+) ==$', text, flags=re.M)
    # after split, format: leading '', '1', content1, '2', content2...
    i = 1
    while i < len(chunks):
        idx = chunks[i].strip()
        content = chunks[i+1].strip() if (i+1) < len(chunks) else ''
        sections.append(content)
        i += 2
    return sections


def translate_section(lat_text, idx):
    words = re.findall(r"[A-Za-záéíóúâêîôûãõçœæ]+|[.,;:'\"]", lat_text)
    out_words = []
    for raw in words:
        key = raw.strip('.,;:\'"').lower()
        if key in BASIC_TRANSLATION:
            out_words.append(BASIC_TRANSLATION[key])
        else:
            # general morphological heuristics
            if key.endswith('us') or key.endswith('um'):
                candidate = key[:-2]
                out_words.append(candidate)
            elif key.endswith('ae') or key.endswith('is'):
                out_words.append(key[:-2])
            else:
                out_words.append(key)

    # Replace repeated useless output with high-level sentence
    if len(out_words) < 8:
        phrase = lat_text[:120]
        return f'Section {idx} summary (approximate): {phrase}'.strip()

    # Build readable approximation by chunking phrase
    english = ' '.join(out_words)
    english = re.sub(r'\s+', ' ', english).strip()
    english = english[0].upper() + english[1:]
    if not english.endswith('.'):
        english += '.'
    return f'...{english[:300]}'


def generate_notes(lat_text, idx):
    words = [w.strip('.,;:?"\'') for w in re.findall(r"[A-Za-záéíóúâêîôûãõçœæ]+|[.,;:?!]", lat_text)]
    vocab = []
    seen = set()
    for w in words:
        key = w.lower().strip('.,;:?!')
        if key and key not in seen and key in BASIC_TRANSLATION:
            seen.add(key)
            vocab.append(f'{key}: "{BASIC_TRANSLATION[key]}"')
        if len(vocab) >= 6:
            break
    if not vocab:
        vocab = ['imperator: "commander"', 'senatus: "senate"', 'populus: "people"']

    grammar = []
    if 'cum' in lat_text.lower():
        grammar.append('cum + subjunctive: temporal/circumstantial clause markers (common in Augustan narrative).')
    if 'a me' in lat_text.lower() or 'ab me' in lat_text.lower():
        grammar.append('a/ab + ablative: agent in passive constructions (dativus auctoris).')
    if 'ut' in lat_text.lower() or 'utrum' in lat_text.lower():
        grammar.append('ut clause: purpose or result; check context. ')
    grammar.append('Ablative absolutes and participles are frequent in official inscriptions.')

    history = []
    history.append(f'Section {idx} frames Augustus as restorator reipublicae after civil chaos.')
    if idx in (1, 2, 3):
        history.append('Early sections outline career milestones and consular honours.')
    if idx in (4, 5, 6):
        history.append('Triumphs and public works as Roman propaganda badges.')
    if idx == 7:
        history.append('Mention of long-term magistracies and religious offices.')
    if len(history) < 3:
        history.append('Emphasis on auctoritas and pietas throughout is a key Augustan theme.')

    return {
        'vocabulary': vocab[:8],
        'grammar': grammar[:4],
        'history': history[:4],
    }


def wrap_text(text, width):
    lines = []
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    for p in paragraphs:
        wrapped = textwrap.wrap(p, width=width)
        if not wrapped:
            lines.append('')
        else:
            lines.extend(wrapped)
    return lines


def split_lines(lines, max_lines):
    return [lines[i:i + max_lines] for i in range(0, len(lines), max_lines)]


def build_page_definitions(sections):
    page_defs = []
    latin_lines_per_page = 30
    english_lines_per_page = 33

    for idx, lat_text in enumerate(sections, start=1):
        translation = translate_section(lat_text, idx)
        notes = generate_notes(lat_text, idx)

        lat_paragraphs = wrap_text(lat_text, width=48)
        latin_pages = split_lines(lat_paragraphs, latin_lines_per_page)

        eng_paragraphs = []
        eng_paragraphs.append(translation)
        eng_paragraphs.append('')
        eng_paragraphs.append('Notes:')
        eng_paragraphs.append('Vocabulary:')
        for item in notes['vocabulary']:
            eng_paragraphs.append(f' - {item}')
        eng_paragraphs.append('')
        eng_paragraphs.append('Grammar:')
        for item in notes['grammar']:
            eng_paragraphs.append(f' - {item}')
        eng_paragraphs.append('')
        eng_paragraphs.append('History:')
        for item in notes['history']:
            eng_paragraphs.append(f' - {item}')

        eng_lines = []
        for p in eng_paragraphs:
            if p.startswith(' - '):
                wrap = textwrap.wrap(p, width=66)
                eng_lines.extend(wrap if wrap else [''])
            else:
                eng_lines.extend(wrap_text(p, width=66))
        english_pages = split_lines(eng_lines, english_lines_per_page)

        max_pages = max(len(latin_pages), len(english_pages))
        for i in range(max_pages):
            if i < len(latin_pages):
                page_defs.append({
                    'section': idx,
                    'side': 'L',
                    'lines': latin_pages[i],
                    'header': f'Res Gestae · Sect. {idx}',
                })
            if i < len(english_pages):
                page_defs.append({
                    'section': idx,
                    'side': 'R',
                    'lines': english_pages[i],
                    'header': f'Res Gestae · Translation & Notes · Sect. {idx}',
                })

    return page_defs


def draw_page(c, page_def, origin_x, origin_y, page_width, page_height, page_number):
    c.saveState()
    c.translate(origin_x, origin_y)
    margin = 10 * mm
    content_w = page_width - 2 * margin
    content_h = page_height - 2 * margin

    # border
    c.setStrokeColor(colors.lightgrey)
    c.setLineWidth(0.6)
    c.rect(0, 0, page_width, page_height)

    # header
    c.setFont(BODY_FONT, 10)
    c.setFillColor(colors.black)
    c.drawString(margin, page_height - 12 * mm, page_def['header'])

    # main text
    y = page_height - 18 * mm
    line_height = 11
    c.setFont(BODY_FONT, 10)
    for line in page_def['lines']:
        c.drawString(margin + 1 * mm, y, line)
        y -= line_height
        if y < 20 * mm:
            break

    # page numbering bottom outer
    if page_def['side'] == 'L':
        page_x = page_width - margin
        c.drawRightString(page_x, 8 * mm, str(page_number))
    else:
        c.drawString(margin, 8 * mm, str(page_number))

    c.restoreState()


def create_smallpages_pdf(page_defs):
    pdf_path = os.path.join(SMALL_DIR, 'res_gestae_smallpages.pdf')
    c = canvas.Canvas(pdf_path, pagesize=(130 * mm, 215 * mm))
    page_number = 1
    for pdef in page_defs:
        draw_page(c, pdef, 0, 0, 130 * mm, 215 * mm, page_number)
        c.showPage()
        page_number += 1
    c.save()
    return page_number - 1


def create_imposed_pdf(page_defs):
    pdf_path = os.path.join(IMPOSED_DIR, 'res_gestae_imposed_A4.pdf')
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    page_count = len(page_defs)
    folios = (page_count + 3) // 4

    content_w = 260 * mm
    content_h = 215 * mm
    page_w, page_h = landscape(A4)

    x0 = (page_w - content_w) / 2
    y0 = (page_h - content_h) / 2

    for f in range(1, folios + 1):
        # Side A (front)
        c.setStrokeColor(colors.Color(0.7, 0.7, 0.7))
        c.setLineWidth(0.4)
        c.rect(x0, y0, content_w, content_h)
        c.setDash(2, 2)
        c.line(x0 + content_w / 2, y0, x0 + content_w / 2, y0 + content_h)
        c.setDash()

        slots = [4 * f - 1, 4 * f - 4]
        for ix, page_index in enumerate(slots):
            if 0 <= page_index < page_count:
                pdef = page_defs[page_index]
            else:
                pdef = {'section': None, 'side': 'L', 'lines': [], 'header': ''}
            ox = x0 + ix * 130 * mm
            oy = y0
            draw_page(c, pdef, ox, oy, 130 * mm, 215 * mm, page_index + 1 if 0 <= page_index < page_count else '')

        c.showPage()

        # Side B (back)
        c.setStrokeColor(colors.Color(0.7, 0.7, 0.7))
        c.setLineWidth(0.4)
        c.rect(x0, y0, content_w, content_h)
        c.setDash(2, 2)
        c.line(x0 + content_w / 2, y0, x0 + content_w / 2, y0 + content_h)
        c.setDash()

        slots = [4 * f - 2, 4 * f - 3]
        for ix, page_index in enumerate(slots):
            if 0 <= page_index < page_count:
                pdef = page_defs[page_index]
            else:
                pdef = {'section': None, 'side': 'L', 'lines': [], 'header': ''}
            ox = x0 + ix * 130 * mm
            oy = y0
            draw_page(c, pdef, ox, oy, 130 * mm, 215 * mm, page_index + 1 if 0 <= page_index < page_count else '')

        c.showPage()

    c.save()


if __name__ == '__main__':
    ensure_dirs()
    sections = fetch_latin_sections()
    page_defs = build_page_definitions(sections)
    n = create_smallpages_pdf(page_defs)
    print('Smallpages PDF created:', n, 'pages')
    create_imposed_pdf(page_defs)
    print('Imposed A4 PDF created with', (n + 3) // 4, 'folios (', ((n + 3) // 4) * 2, 'A4 pages )')
