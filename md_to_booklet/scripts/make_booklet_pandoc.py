import os
import re
from datetime import date

import requests
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

DATA_DIR = 'data'
SMALL_DIR = 'build/smallpages'
IMPOSED_DIR = 'build/imposed'
LATIN_SOURCE_URL = 'https://www.thelatinlibrary.com/resgestae.html'
ENGLISH_SECTIONS = None

BASIC_TRANSLATION = {
    'annos': 'years', 'undeviginti': 'nineteen', 'natus': 'born', 'exercitum': 'army',
    'privato': 'private', 'consilio': 'counsels', 'impensa': 'expense', 'comparavi': 'procured',
    'res': 'affairs', 'publicam': 'the republic', 'libertatem': 'freedom', 'vindicavi': 'vindicated',
    'senatus': 'senate', 'decretis': 'decrees', 'honorificis': 'honorary', 'consulibus': 'consuls',
    'consulatum': 'consulate', 'triumphavi': 'I triumphed', 'curulis': 'curule', 'imperator': 'commander',
    'augustus': 'Augustus', 'qui': 'who', 'cum': 'when', 'erat': 'was', 'dedi': 'I gave',
    'pax': 'peace', 'bellum': 'war', 'populus': 'people', 'romanorum': 'of the Romans', 'miles': 'soldier',
}

HISTORY_BASE = [
    'Augustus frames actions as restoration and peace after civil conflict.',
    'Senate and people language provides constitutional legitimization (SPQR).',
    'Tonal emphasis on pietas and military success is central propaganda.',
    'Religious office-count and triumphs express auctoritas in inscription tradition.',
]


def ensure_dirs():
    for d in [DATA_DIR, SMALL_DIR, IMPOSED_DIR]:
        os.makedirs(d, exist_ok=True)


def fetch_latin_sections():
    ensure_dirs()
    latin_file = os.path.join(DATA_DIR, 'latin.txt')

    if os.path.exists(latin_file):
        with open(latin_file, 'r', encoding='utf-8') as f:
            data = f.read()
        if '== SECTION 1 ==' in data:
            return parse_latin_with_sections(data)

    r = requests.get(LATIN_SOURCE_URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
    r.raise_for_status()
    html = r.text

    paras = re.findall(r'<p>(.*?)</p>', html, flags=re.S)
    sections = {}
    for p in paras:
        clean = re.sub(r'<[^>]+>', '', p).strip()
        m = re.match(r'\s*\[(\d+)\]\s*(.*)', clean, flags=re.S)
        if m:
            idx = int(m.group(1))
            text = m.group(2).replace('\n', ' ').strip()
            text = re.sub(r'\s+', ' ', text)
            sections[idx] = text

    if not sections:
        raise RuntimeError('Could not parse Latin sections from source HTML.')

    for i in range(1, 36):
        sections.setdefault(i, f'Latin text unavailable for section {i}.')

    with open(latin_file, 'w', encoding='utf-8') as f:
        for i in range(1, 36):
            f.write(f'== SECTION {i} ==\n')
            f.write(sections[i] + '\n\n')

    return [sections[i] for i in range(1, 36)]


def parse_latin_with_sections(content):
    sections = []
    parts = re.split(r'^== SECTION (\d+) ==$', content, flags=re.M)
    i = 1
    while i < len(parts):
        sections.append(parts[i + 1].strip() if i + 1 < len(parts) else '')
        i += 2
    return sections


SECTION_TRANSLATIONS = {
    1: 'At nineteen years old I raised an army with my own means and from my own funds, by which I freed the Republic from the domination of a faction.',
    2: 'I expelled those who murdered my father into exile by legal judgment and defeated the enemies of the republic twice in battle.',
    3: 'I waged wars by land and sea, civil and foreign, and spared those communities whom it was safe to forgive.',
    4: 'I was twice ovationed, three times received curule triumphs and called victor in twenty-one deserts; I refused further triumphs.',
    5: 'I did not accept dictatorship from the people and senate, and I managed the grain supply so that the populace was freed from present fear and danger.',
    6: 'I refused to accept magistracies superseding the mos maiorum and performed the tasks the senate ordered through tribunician power.',
    7: 'I was triumvir for ten consecutive years, princeps senatus, pontifex maximus, augur, and held all major priesthoods.',
    8: 'I increased the number of patricians, twice endowed the census and adjusted the senate, voting and agrarian registers.',
    9: 'The senate decreed vows for my health every five years; the people and provinces joined in offering games and sacrifices.',
    10: 'My name was included in the salian hymn by senate decree so that I was sacred for life under the law.',
    # fallback for all deeper sections when we have no full prepared translation yet
}

def translate_section(latin, idx):
    """
    Return an English translation or concise English summary for a given Latin section.
    - Use an explicit `SECTION_TRANSLATIONS` entry when available.
    - Otherwise attempt a word-by-word mapping using `BASIC_TRANSLATION`.
    - If that yields too little, fall back to a keyword-based English summary.
    The goal is to ensure the "Translation" pages contain English text (not raw Latin).
    """
    # Prefer an explicit English file (data/english.txt) when available
    global ENGLISH_SECTIONS
    if ENGLISH_SECTIONS is None:
        ENGLISH_SECTIONS = load_english_sections() if 'load_english_sections' in globals() else {}
    if ENGLISH_SECTIONS and idx in ENGLISH_SECTIONS:
        return ENGLISH_SECTIONS[idx]

    if idx in SECTION_TRANSLATIONS:
        return SECTION_TRANSLATIONS[idx]

    # Attempt word-by-word mapping to English using our small dictionary.
    words = re.findall(r"[A-Za-záéíóúâêîôûãõçœæ]+", latin)
    mapped = [BASIC_TRANSLATION.get(w.lower()) for w in words]
    mapped = [m for m in mapped if m]

    if len(mapped) >= 6:
        sentence = ' '.join(mapped)
        sentence = sentence[0].upper() + sentence[1:]
        if not sentence.endswith('.'):
            sentence += '.'
        return sentence

    # Keyword-driven topic summary (English) for coarse fallback
    l = latin.lower()
    topics = []
    if 'congi' in l or 'viritim' in l or 'hs' in l or 'sestert' in l:
        topics.append('per-capita monetary distributions (congiaria)')
    if 'consul' in l or 'consulatu' in l:
        topics.append('consulships and official acts')
    if 'triumph' in l or 'triumphavi' in l:
        topics.append('triumphs and public honors')
    if 'pontif' in l or 'augur' in l or 'sacerdot' in l:
        topics.append('religious offices and priesthoods')
    if 'theatr' in l or 'lud' in l or 'venation' in l or 'naumach' in l:
        topics.append('public games and spectacles')
    if 'aqu' in l or 'riv' in l:
        topics.append('waterworks and aqueducts')
    if 'colon' in l or 'milit' in l:
        topics.append('colonies and veteran settlements')
    if 'parth' in l or 'arab' in l or 'aegypt' in l:
        topics.append('foreign campaigns and client kingdoms')
    if 'pax' in l or 'pac' in l:
        topics.append('peace settlements')

    if topics:
        # concise English summary listing the detected topics
        return 'This section discusses ' + ', '.join(topics) + '.'

    # Last-resort fallback: short English notice referencing the Latin text
    if mapped:
        s = ' '.join(mapped)
        s = s[0].upper() + s[1:]
        if not s.endswith('.'):
            s += '.'
        return s

    return f'Translation for section {idx} is not available; this section discusses Roman administrative, military, or religious actions.'


def load_english_sections():
    """Parse `data/english.txt` if present and return a dict of section->English text.

    The file is expected to contain numbered paragraphs like "1. ...", "2. ...".
    """
    path = os.path.join(DATA_DIR, 'english.txt')
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        txt = f.read()

    # Find numbered paragraphs like "1. ..." up to next numbered paragraph
    matches = re.findall(r"\b(\d{1,2})\.\s*(.*?)(?=\n\s*\d{1,2}\.\s|\Z)", txt, flags=re.S)
    sections = {}
    for num, body in matches:
        try:
            n = int(num)
        except ValueError:
            continue
        s = re.sub(r"\s+", ' ', body).strip()
        sections[n] = s
    return sections


def notes_for_section(latin, idx):
    words = re.findall(r"[A-Za-záéíóúâêîôûãõçœæ]+", latin)
    seen = set()
    vocab = []

    def boys_form(word):
        w = word.lower()
        if w.endswith('us'):
            return 'nom sg m (2nd declension)'
        if w.endswith('i'):
            return 'gen sg / nom pl m (2nd declension)'
        if w.endswith('ae'):
            return 'gen sg / nom pl f (1st declension)'
        if w.endswith('am'):
            return 'acc sg f (1st declension)'
        if w.endswith('um'):
            return 'acc sg n (2nd declension)'
        if w.endswith('em'):
            return 'acc sg m/f (3rd declension)'
        if w.endswith('a'):
            return 'nom sg f / nom pl n'
        return ''

    for w in words:
        key = w.lower()
        if key in BASIC_TRANSLATION and key not in seen:
            if len(vocab) >= 6:
                break
            seen.add(key)
            form = boys_form(key)
            if key in ['augustus', 'imperator', 'populus', 'senatus']:
                decl = '2nd declension' if key != 'senatus' else '4th declension'
                vocab.append(f'{key} ({form}, {decl}): "{BASIC_TRANSLATION[key]}"')
            else:
                vocab.append(f'{key} ({form}): "{BASIC_TRANSLATION[key]}"')

    if not vocab:
        vocab = ['imperator (nom sg m, 2nd declension): "commander"', 'senatus (nom sg m, 4th declension): "senate"', 'populus (nom sg m, 2nd declension): "people"']

    grammar = []
    if 'cum' in latin.lower():
        grammar.append('cum + clause (temporal/causal)')
    if 'ut' in latin.lower():
        grammar.append('ut clause (purpose/result)')
    if 'a me' in latin.lower() or 'ab me' in latin.lower():
        grammar.append('a/ab + ablative (agent, dative auctoris)')

    # provide one grammar note only, not repeated by every section
    if 'ut' in latin.lower() or 'cum' in latin.lower() or 'a me' in latin.lower() or 'ab me' in latin.lower():
        pass
    else:
        # no special constructions in this short excerpt
        pass

    if not grammar:
        grammar.append('Ablative absolute and participial constructions are key.')


    # Provide a single concise historical note per section from HISTORY_BASE.
    history = [HISTORY_BASE[(idx - 1) % len(HISTORY_BASE)]]
    return {'vocabulary': vocab, 'grammar': grammar, 'history': history}


def write_markdown(sections):
    os.makedirs(SMALL_DIR, exist_ok=True)
    md_path = os.path.join(SMALL_DIR, 'booklet.md')
    today = date.today().isoformat()

    with open(md_path, 'w', encoding='utf-8') as f:
        # Cover page (page 1, no number)
        f.write('# Res Gestae Divi Augusti\n\n')
        f.write('**Author:** Augustus Imperator\n\n')
        f.write('![](import/augustus-imperator.PNG){width=40%}\n\n')
        # cover should NOT contain production metadata; leave it minimal
        f.write('\\thispagestyle{empty}\n\n')
        f.write('\\newpage\n\n')

        # Blank page (physical page 2) — intentionally empty
        f.write('\\thispagestyle{empty}\n\n')
        f.write('\\newpage\n\n')

        # Impressum (physical page 3) — use plain text to avoid creating running headers
        f.write('**Impressum**\n\n')
        f.write('Produced by: Gilles Demaneuf + GitHub Copilot (Raptor mini, Preview)\n\n')
        f.write('Date: ' + today + '\n\n')
        # Clear LaTeX header marks so this title does not appear in running headers
        f.write('\\markboth{}{}\n')
        f.write('\\thispagestyle{empty}\n\n')
        f.write('\\newpage\n\n')

        # Insert an intentionally blank smallpage after the Impressum so that
        # the first numbered A5 page (Latin) falls on a left-hand page.
        f.write('\\thispagestyle{empty}\n\n')
        f.write('\\newpage\n\n')

        # Start Arabic numbering at section page 3
        f.write('\\pagenumbering{arabic}\n')
        f.write('\\setcounter{page}{1}\n\n')

        # Each Latin page gets two sections; each translation/notes page also two sections
        for base in range(0, len(sections), 2):
            f.write('**Latin**\n\n')
            for j in range(2):
                idx = base + j
                if idx < len(sections):
                    f.write('### Sectio ' + str(idx + 1) + '\n\n')
                    f.write(sections[idx] + '\n\n')
            f.write('\\newpage\n\n')

            f.write('**Translation & Notes**\n\n')
            for j in range(2):
                idx = base + j
                if idx < len(sections):
                    sec_index = idx + 1
                    trans = translate_section(sections[idx], sec_index)
                    notes = notes_for_section(sections[idx], sec_index)
                    f.write('### Sectio ' + str(sec_index) + ' — English\n\n')
                    f.write('**Translation:** ' + trans + '\n\n')
                    f.write('**Vocabulary:**\n')
                    for v in notes['vocabulary']:
                        f.write('- ' + v + '\n')
                    f.write('\n')
                    f.write('**Grammar:**\n')
                    for g in notes['grammar']:
                        f.write('- ' + g + '\n')
                    f.write('\n')
                    f.write('**History:**\n')
                    for h in notes['history']:
                        f.write('- ' + h + '\n')
                    f.write('\n')
            f.write('\\newpage\n\n')

        # Back pages (no page numbering) — put the historical write-up on the
        # penultimate smallpage and the curated backcover blurb as the final page.
        f.write('\\pagenumbering{gobble}\n\n')

        # Penultimate page: include Wikipedia summary (sanitised)
        res_md_path = os.path.join(DATA_DIR, 'res_gestae_wikipedia.md')
        if os.path.exists(res_md_path):
            with open(res_md_path, 'r', encoding='utf-8') as rf:
                res_md = rf.read()
            # remove top-level title lines and drop an explicit 'Reception' section
            res_md = re.sub(r"^#.*?\n+", '', res_md, flags=re.M)
            res_md = re.sub(r"##\s*Reception[\s\S]*$", '', res_md, flags=re.M)
            res_md = res_md.strip()
            if res_md:
                f.write(res_md + '\n\n')
            else:
                f.write('\n\n')
        else:
            # leave an intentionally blank penultimate page if no md present
            f.write('\n\n')
        f.write('\\newpage\n\n')

        # Final page: Back Cover (curated blurb)
        back_path = os.path.join(DATA_DIR, 'backpage.txt')
        if os.path.exists(back_path):
            with open(back_path, 'r', encoding='utf-8') as bf:
                back = bf.read()
            f.write(back + '\n')
        else:
            f.write('\n')
    return md_path
def render_smallpages(md_path):
    out_pdf = os.path.join(SMALL_DIR, 'res_gestae_smallpages.pdf')
    base_cmd = [
        'pandoc', md_path,
        '--pdf-engine=xelatex',
        '-V', 'geometry:paperwidth=148mm',
        '-V', 'geometry:paperheight=210mm',
        '-V', 'geometry:inner=18mm',
        '-V', 'geometry:outer=12mm',
        '-V', 'geometry:top=20mm',
        '-V', 'geometry:bottom=20mm',
        '-V', 'geometry:bindingoffset=10mm',
        '-V', 'documentclass=book',
        '-V', 'classoption=twoside',
        '-V', 'fontsize=10pt',
        '-o', out_pdf,
    ]

    import subprocess
    # First try xelatex with no explicit font settings (better for environments without those fonts)
    result = subprocess.run(base_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return out_pdf
    print(f"pandoc failed with default xelatex: {result.stderr[:320]}")

    # Then try xelatex with some common font fallbacks
    try_fonts = [
        ('Noto Serif', 'Noto Sans', 'Noto Serif'),
        ('EB Garamond', 'Noto Sans', 'Noto Serif'),
        ('TeX Gyre Pagella', 'TeX Gyre Heros', 'TeX Gyre Cursor'),
    ]

    for main, sans, mono in try_fonts:
        cmd = base_cmd + ['-V', f'mainfont={main}', '-V', f'sansfont={sans}', '-V', f'monofont={mono}']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return out_pdf
        print(f"pandoc failed with font {main}: {result.stderr[:320]}")

    # fallback to pdflatex (default fonts available in almost every TeX installation)
    fallback_cmd = [
        'pandoc', md_path,
        '--pdf-engine=pdflatex',
        '-V', 'geometry:paperwidth=148mm',
        '-V', 'geometry:paperheight=210mm',
        '-V', 'geometry:inner=18mm',
        '-V', 'geometry:outer=12mm',
        '-V', 'geometry:top=20mm',
        '-V', 'geometry:bottom=20mm',
        '-V', 'geometry:bindingoffset=10mm',
        '-V', 'documentclass=book',
        '-V', 'classoption=twoside',
        '-V', 'fontsize=10pt',
        '-o', out_pdf,
    ]
    result = subprocess.run(fallback_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return out_pdf

    print('pdflatex fallback failed:', result.stderr[:320])
    raise RuntimeError('All pandoc render attempts failed in render_smallpages.')


def impose_pdf(small_pdf):
    os.makedirs(IMPOSED_DIR, exist_ok=True)
    output = os.path.join(IMPOSED_DIR, 'res_gestae_imposed_A4.pdf')

    reader = PdfReader(small_pdf)
    writer = PdfWriter()

    a5_w = float(reader.pages[0].mediabox.width)
    a5_h = float(reader.pages[0].mediabox.height)
    a4_w = 842.0  # points (landscape A4)
    a4_h = 595.0

    left_x = (a4_w - 2 * a5_w) / 2
    right_x = left_x + a5_w

    total_pages = len(reader.pages)
    folios = (total_pages + 3) // 4

    # Standard booklet imposition: pair first and last pages, then second and penultimate, etc.
    for s in range(folios):
        # front of sheet: left = last - 2*s, right = 2*s
        front_right = 2 * s
        front_left = total_pages - 1 - 2 * s

        page = writer.add_blank_page(width=a4_w, height=a4_h)
        if 0 <= front_left < total_pages:
            page.merge_translated_page(reader.pages[front_left], left_x, 0, expand=False)
        if 0 <= front_right < total_pages:
            page.merge_translated_page(reader.pages[front_right], right_x, 0, expand=False)

        # back of sheet: left = 2*s + 1, right = total_pages - 2 - 2*s
        back_left = 2 * s + 1
        back_right = total_pages - 2 - 2 * s

        page = writer.add_blank_page(width=a4_w, height=a4_h)
        if 0 <= back_left < total_pages:
            page.merge_translated_page(reader.pages[back_left], left_x, 0, expand=False)
        if 0 <= back_right < total_pages:
            page.merge_translated_page(reader.pages[back_right], right_x, 0, expand=False)

    # Add crop and fold guides on each page using reportlab overlay
    overlay_path = os.path.join(IMPOSED_DIR, 'impose_overlay.pdf')
    c = canvas.Canvas(overlay_path, pagesize=(a4_w, a4_h))
    for _ in range(folios * 2):
        c.setStrokeColorRGB(0.5, 0.5, 0.5)
        c.setLineWidth(0.5)
        # crop marks (4 corners)
        cm = 7 * mm
        x0 = 0
        y0 = 0
        x1 = a4_w
        y1 = a4_h
        c.line(x0, y0, x0 + cm, y0)
        c.line(x0, y0, x0, y0 + cm)
        c.line(x1, y0, x1 - cm, y0)
        c.line(x1, y0, x1, y0 + cm)
        c.line(x0, y1, x0 + cm, y1)
        c.line(x0, y1, x0, y1 - cm)
        c.line(x1, y1, x1 - cm, y1)
        c.line(x1, y1, x1, y1 - cm)
        # fold guide
        c.setStrokeColorRGB(0.6, 0.6, 0.6)
        c.setDash(3, 3)
        c.line(a4_w / 2, 0, a4_w / 2, a4_h)
        c.setDash()
        c.showPage()
    c.save()

    overlay = PdfReader(overlay_path)
    out_writer = PdfWriter()
    assert len(overlay.pages) == len(writer.pages)
    for i, page in enumerate(writer.pages):
        page.merge_page(overlay.pages[i])
        out_writer.add_page(page)

    with open(output, 'wb') as f:
        out_writer.write(f)

    return output


if __name__ == '__main__':
    ensure_dirs()
    sections = fetch_latin_sections()
    md_path = write_markdown(sections)
    print('Markdown saved:', md_path)

    small_pdf = render_smallpages(md_path)
    print('Small pages PDF created:', small_pdf)

    imposed_pdf = impose_pdf(small_pdf)
    print('Imposed A4 PDF created:', imposed_pdf)
