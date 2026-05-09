from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm

output = 'build/imposed/test_front_folio1.pdf'
W, H = landscape(A4)

c = canvas.Canvas(output, pagesize=(W, H))

content_w = 260 * mm
content_h = 215 * mm
x0 = (W - content_w) / 2
y0 = (H - content_h) / 2

c.setStrokeColorRGB(0.5,0.5,0.5)
c.setLineWidth(0.5)
c.rect(x0, y0, content_w, content_h)

mid_x = x0 + content_w / 2
c.setStrokeColorRGB(0.7,0.7,0.7)
c.setLineWidth(0.2)
c.line(mid_x, y0, mid_x, y0 + content_h)

c.setFont('Helvetica-Bold', 16)
c.drawCentredString(x0 + content_w * 0.25, y0 + content_h * 0.5, 'Page 4 (Back of folio placeholder)')
c.drawCentredString(x0 + content_w * 0.75, y0 + content_h * 0.5, 'Page 1 (Front cover placeholder)')

cm_len = 7 * mm
c.setStrokeColorRGB(0,0,0)
for xx, yy, dx, dy in [
    (x0, y0, 1, 0), (x0, y0, 0, 1),
    (x0 + content_w, y0, -1, 0), (x0 + content_w, y0, 0, 1),
    (x0, y0 + content_h, 1, 0), (x0, y0 + content_h, 0, -1),
    (x0 + content_w, y0 + content_h, -1, 0), (x0 + content_w, y0 + content_h, 0, -1),
]:
    c.line(xx, yy, xx + dx * cm_len, yy + dy * cm_len)

c.setStrokeColorRGB(0.6,0.6,0.6)
c.setDash(3, 3)
c.line(mid_x, y0, mid_x, y0 + content_h)
c.setDash()

c.setFont('Helvetica', 8)
c.drawString(20 * mm, 10 * mm, 'Phase 1 test front folio layout - Res Gestae')

c.showPage()
c.save()

print('generated:', output)
