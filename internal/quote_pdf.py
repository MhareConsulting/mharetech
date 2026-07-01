"""Branded quote PDF (reportlab) — shared by both products' pricing toolkits.

build_quote_pdf(payload) renders a Mhare-branded quotation from the numbers the
client-side calculator already computed (single source of truth stays in JS).
"""
from __future__ import annotations

import io

from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

VIOLET = colors.HexColor('#5041d9')
MAGENTA = colors.HexColor('#f7357b')
INK = colors.HexColor('#0b0146')
MUTED = colors.HexColor('#5c5678')
TINT = colors.HexColor('#eef0fb')
LINE = colors.HexColor('#d7d9ea')

LOGO = 'Assets/Digital logos/PNG/2000w/Mhare Consulting_Primary Logo.png'


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _zar(v):
    return 'R' + format(int(round(_f(v))), ',d')


def build_quote_pdf(p: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f'{p.get("product_name", "Mhare")} Quote')
    ss = getSampleStyleSheet()
    body = ParagraphStyle('body', parent=ss['Normal'], fontName='Helvetica', fontSize=9,
                          textColor=INK, leading=13)
    small = ParagraphStyle('small', parent=body, fontSize=8, textColor=MUTED)
    rt = ParagraphStyle('rt', parent=body, alignment=TA_RIGHT)
    rtb = ParagraphStyle('rtb', parent=rt, fontName='Helvetica-Bold')
    h_title = ParagraphStyle('title', parent=body, fontName='Helvetica-Bold', fontSize=20, textColor=INK)
    label = ParagraphStyle('label', parent=small, fontName='Helvetica-Bold', textColor=VIOLET)

    story = []
    CW = doc.width

    # ── Header: logo + QUOTATION / meta ──────────────────────────────────
    logo_path = finders.find(LOGO)
    logo_flow = ''
    if logo_path:
        img = Image(logo_path)
        img._restrictSize(46 * mm, 16 * mm)
        logo_flow = img
    meta = [
        Paragraph('QUOTATION', h_title),
        Paragraph(f'Ref: {p.get("quote_ref", "-")}', rt),
        Paragraph(f'Date: {p.get("date", "-")}', rt),
        Paragraph(f'{p.get("product_name", "")} · subscription', rt),
    ]
    header = Table([[logo_flow, meta]], colWidths=[CW * 0.5, CW * 0.5])
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (0, 0), 'TOP'), ('VALIGN', (1, 0), (1, 0), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story += [header, Spacer(1, 4)]
    story.append(Table([['']], colWidths=[CW], rowHeights=[3],
                       style=TableStyle([('BACKGROUND', (0, 0), (-1, -1), VIOLET)])))
    story.append(Spacer(1, 10))

    # ── Prepared for / summary strip ─────────────────────────────────────
    left = [Paragraph('PREPARED FOR', label),
            Paragraph(p.get('prepared_for') or '—', body),
            Paragraph('Prepared by: ' + (p.get('prepared_by') or '—'), small)]
    t = p.get('totals', {})
    meta2 = p.get('meta', {})
    right = [Paragraph('SUMMARY', label),
             Paragraph(f'Units: {int(_f(t.get("units")))}', body),
             Paragraph(f'Contract term: {int(_f(meta2.get("term")))} months', small),
             Paragraph(f'Tier: {meta2.get("tier", "-")}  ·  Discount: {meta2.get("discount_pct", 0)}%', small)]
    pf = Table([[left, right]], colWidths=[CW * 0.6, CW * 0.4])
    pf.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    story += [pf, Spacer(1, 14)]

    # ── Line items ───────────────────────────────────────────────────────
    head = ['Item', 'Qty', 'Once-off /unit', 'Monthly /unit', 'Line once-off', 'Line monthly']
    data = [head]
    for ln in p.get('lines', []):
        qty = _f(ln.get('qty'))
        once_u = _f(ln.get('once_unit'))
        mo_u = _f(ln.get('monthly_unit'))
        data.append([Paragraph(str(ln.get('desc', '')), body), _fmt_int(qty),
                     _zar(once_u), _zar(mo_u), _zar(qty * once_u), _zar(qty * mo_u)])
    tbl = Table(data, colWidths=[CW * 0.34, CW * 0.08, CW * 0.16, CW * 0.16, CW * 0.13, CW * 0.13])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), VIOLET), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 1), (-1, -1), 0.4, LINE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f8fb')]),
    ]))
    story += [tbl, Spacer(1, 14)]

    # ── Totals box ───────────────────────────────────────────────────────
    labels = p.get('labels', {})
    rows = [
        [labels.get('subtotal', 'Subtotal'), _zar(t.get('subtotal_once'))],
        [labels.get('fee', 'Setup fee'), _zar(t.get('fee_once'))],
        ['Total once-off', _zar(t.get('once_off'))],
        ['Total monthly', _zar(t.get('monthly'))],
        ['Contract total value (TCV)', _zar(t.get('tcv'))],
    ]
    trows = []
    for i, (k, v) in enumerate(rows):
        strong = k.startswith('Total') or 'TCV' in k
        trows.append([Paragraph(k, rtb if strong else rt), Paragraph(v, rtb if strong else rt)])
    totals = Table(trows, colWidths=[CW * 0.32, CW * 0.18], hAlign='RIGHT')
    totals.setStyle(TableStyle([
        ('LINEABOVE', (0, 2), (-1, 2), 0.5, LINE), ('LINEABOVE', (0, 4), (-1, 4), 0.8, VIOLET),
        ('BACKGROUND', (0, 4), (-1, 4), TINT), ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story += [totals, Spacer(1, 18)]

    # ── Terms / footer ───────────────────────────────────────────────────
    story.append(Paragraph(
        'Pricing is indicative and subject to a site survey and final scope confirmation. '
        'Valid for 30 days from the date above. All amounts exclude VAT unless stated. E&OE.', small))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        'Mhare Tech · a MyReach / Mhare Consulting product · sales@mhareconsulting.co.za · mharetech.co.za', small))

    doc.build(story)
    return buf.getvalue()


def _fmt_int(v):
    return format(int(round(_f(v))), ',d') if v else '—'
