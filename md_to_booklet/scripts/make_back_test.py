from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.lib import colors

output = 'build/imposed/test_back_folio1.pdf'
W, H = landscape(A4)
content_w = 260 * mm
content_h = 215 * mm
x0 = (W - content_w) / 2
y0 = (H - content_h) / 2
mid_x = x0 + content_w / 2

c = canvas.Canvas(output, pagesize=(W, H))

# outer content rectangle
c.setStrokeColor(colors.Color(0.5, 0.5, 0.5))
c.setLineWidth(0.5)
c.rect(x0, y0, content_w, content_h)

# center seam line (content split)
c.setStrokeColor(colors.Color(0.7, 0.7, 0.7))
c.setLineWidth(0.4)
c.line(mid_x, y0, mid_x, y0 + content_h)

# crop marks
cm_len = 7 * mm
c.setStrokeColor(colors.black)
for xx, yy, dx, dy in [
    (x0, y0, 1, 0), (x0, y0, 0, 1),
    (x0 + content_w, y0, -1, 0), (x0 + content_w, y0, 0, 1),
    (x0, y0 + content_h, 1, 0), (x0, y0 + content_h, 0, -1),
    (x0 + content_w, y0 + content_h, -1, 0), (x0 + content_w, y0 + content_h, 0, -1),
]:
    c.line(xx, yy, xx + dx * cm_len, yy + dy * cm_len)

# left panel margins
left_margin = x0 + 10 * mm
right_margin = mid_x - 10 * mm
top_text = y0 + content_h - 12 * mm
line_height = 10

# Add left page heading and Latin text
c.setFont('Times-Bold', 12)
c.drawString(left_margin, top_text, 'Res Gestae · Sect. I')

c.setFont('Times-Roman', 11)
latin_paragraph = [
    'Imperator divi filius Augustus.',
    'A prima luce et in conspectu omnium se exercituum imperavit;',
    'Post urbem Romae captam et religionis hostes victos,',
    'socia se civitas, senatus, populusque Romanus esse voluit.'
]

text_y = top_text - 18
for line in latin_paragraph:
    c.drawString(left_margin, text_y, line)
    text_y -= 14

# left page number outer bottom
c.setFont('Times-Roman', 10)
c.drawRightString(mid_x - 5 * mm, y0 + 8 * mm, '2')

# Right panel intro
right_left = mid_x + 10 * mm
right_right = x0 + content_w - 10 * mm

c.setFont('Times-Bold', 12)
c.drawString(right_left, top_text, 'Res Gestae · Translation & Notes · Sect. I')

c.setFont('Times-Roman', 11)
translate_paragraph = [
    'The Emperor Augustus, son of the deified,',
    'commanded from first light in the sight of all the armies;',
    'After Rome had been captured and the enemies of religion defeated,',
    'he wished to be treated as the ally of the state, senate, and Roman people.'
]
text_y = top_text - 18
for line in translate_paragraph:
    c.drawString(right_left, text_y, line)
    text_y -= 14

# Notes section
notes_title_y = text_y - 14
c.setFont('Times-Bold', 11)
c.drawString(right_left, notes_title_y, 'Notes')
text_y = notes_title_y - 16
c.setFont('Times-Bold', 10)
c.drawString(right_left, text_y, 'Vocabulary:')
text_y -= 12
c.setFont('Times-Roman', 10)
vocab_lines = [
    'Imperator: commander, later the official title of Roman emperors.',
    'divi filius: "son of the deified" (postumus divus Augustus).',
    'prima luce: ablative temporal, "at first light".',
    'socia: accusative object of esse ìn mind of "to be a partner".'
]
for line in vocab_lines:
    c.drawString(right_left + 8, text_y, line)
    text_y -= 12

text_y -= 4
c.setFont('Times-Bold', 10)
c.drawString(right_left, text_y, 'Grammar:')
text_y -= 12
c.setFont('Times-Roman', 10)
grammar_lines = [
    '1. Ablative absolute: prima luce — time phrase "at first light".',
    '2. Indirect statement implied: voluit + se esse soci(um).',
    '3. Dative + esse (dativus commodi): civitas, senatus, populusque ...to be allied.'
]
for line in grammar_lines:
    c.drawString(right_left + 8, text_y, line)
    text_y -= 12

text_y -= 4
c.setFont('Times-Bold', 10)
c.drawString(right_left, text_y, 'History:')
text_y -= 12
c.setFont('Times-Roman', 10)
history_lines = [
    '1. Augustus frames his achievements in piety and military success.',
    '2. Sets tone for Res Gestae: legitimacy through divine descent, consensus.',
    '3. “Senatus populusque Romanus” (SPQR) as constitutional veneer.'
]
for line in history_lines:
    c.drawString(right_left + 8, text_y, line)
    text_y -= 12

# right page number outer bottom
c.drawString(mid_x + 5 * mm, y0 + 8 * mm, '3')

c.showPage()
c.save()
print('generated:', output)
