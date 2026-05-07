"""
Generador de Informes PDF - LUMEN Sistema de Tasación
Versión 2.0 - Calidad profesional, sin superposición de texto
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas as pdf_canvas

# ── COLORES ───────────────────────────────────────────────────────────────────
AZUL_OSCURO = colors.HexColor("#1A3C6E")
AZUL_MEDIO  = colors.HexColor("#2563AB")
AZUL_CLARO  = colors.HexColor("#E8EEF7")
GRIS_OSCURO = colors.HexColor("#2C3E50")
GRIS_MEDIO  = colors.HexColor("#7F8C8D")
GRIS_CLARO  = colors.HexColor("#F2F5F9")
VERDE       = colors.HexColor("#1E8449")
BLANCO      = colors.white
DORADO      = colors.HexColor("#C8A84B")
BORDE       = colors.HexColor("#D0D9E8")
NEGRO       = colors.HexColor("#1A1A2E")

PAGE_W, PAGE_H = A4
MARGIN_H   = 2 * cm
MARGIN_BOT = 2.8 * cm
CONTENT_W  = PAGE_W - 2 * MARGIN_H

ESTADO_LABELS    = {1: "Malo", 2: "Regular", 3: "Bueno", 4: "Excelente"}
UBICACION_LABELS = {1: "Mala", 2: "Regular", 3: "Buena", 4: "Excelente"}


def format_usd(v):
    try:
        return "USD {:,.0f}".format(float(v)).replace(",", ".")
    except Exception:
        return "USD 0"


def format_usd_m2(v):
    try:
        s = "USD {:,.2f}".format(float(v))
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "USD 0,00"


# ── CANVAS ────────────────────────────────────────────────────────────────────

class NumberedCanvas(pdf_canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._saved_page_states)
        for idx, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            self._draw_decoration(idx + 1, n)
            super().showPage()
        super().save()

    def _draw_decoration(self, page_num, total):
        self.saveState()
        # Banda superior (pág > 1)
        if page_num > 1:
            self.setFillColor(AZUL_OSCURO)
            self.rect(0, PAGE_H - 9*mm, PAGE_W, 9*mm, fill=1, stroke=0)
            self.setFillColor(DORADO)
            self.rect(0, PAGE_H - 10.5*mm, PAGE_W, 1.5*mm, fill=1, stroke=0)
        # Footer
        self.setFillColor(AZUL_OSCURO)
        self.rect(0, 0, PAGE_W, 19*mm, fill=1, stroke=0)
        self.setFillColor(DORADO)
        self.rect(0, 19*mm, PAGE_W, 1.2*mm, fill=1, stroke=0)
        # Textos footer
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#A8BCD4"))
        self.drawString(MARGIN_H, 12*mm, "LUMEN · Propiedades & Negocios Rurales")
        self.setFont("Helvetica", 7)
        self.drawString(MARGIN_H, 7*mm, "Informe de Tasación Inmobiliaria · Confidencial")
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(DORADO)
        self.drawRightString(PAGE_W - MARGIN_H, 9.5*mm, f"Pág. {page_num} / {total}")
        self.restoreState()


# ── GENERADOR ─────────────────────────────────────────────────────────────────

def generate_pdf(tasacion_data, resultado, output_path, logo_path=None):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=MARGIN_H, leftMargin=MARGIN_H,
        topMargin=2*cm, bottomMargin=MARGIN_BOT,
        title=f"Informe de Tasación – {tasacion_data.get('direccion', 'Propiedad')}",
        author="LUMEN · Propiedades & Negocios Rurales",
    )
    styles = _build_styles()
    story  = []

    story += _build_header(tasacion_data, logo_path, styles)
    story.append(Spacer(1, 0.5*cm))
    story += _build_agent_section(tasacion_data, styles)
    story.append(Spacer(1, 0.4*cm))
    story += _build_property_section(tasacion_data, styles)
    story.append(Spacer(1, 0.4*cm))
    story += _build_method_section(styles)
    story.append(Spacer(1, 0.4*cm))
    story += _build_comparables_table(resultado, styles)
    story.append(Spacer(1, 0.5*cm))
    story += _build_results_section(resultado, tasacion_data, styles)
    story.append(Spacer(1, 0.4*cm))
    if tasacion_data.get("notas", "").strip():
        story += _build_notes_section(tasacion_data["notas"], styles)
        story.append(Spacer(1, 0.4*cm))
    story += _build_signature_section(tasacion_data, styles)

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path


# ── ESTILOS ───────────────────────────────────────────────────────────────────

def _build_styles():
    s = {}
    s["titulo"] = ParagraphStyle("titulo",
        fontName="Helvetica-Bold", fontSize=17, textColor=AZUL_OSCURO,
        alignment=TA_LEFT, leading=21, spaceAfter=2)
    s["subtitulo"] = ParagraphStyle("subtitulo",
        fontName="Helvetica", fontSize=9.5, textColor=GRIS_MEDIO,
        alignment=TA_LEFT, leading=13, spaceAfter=1)
    s["sec_hdr"] = ParagraphStyle("sec_hdr",
        fontName="Helvetica-Bold", fontSize=9.5, textColor=BLANCO,
        leading=12, alignment=TA_LEFT)
    s["label"] = ParagraphStyle("label",
        fontName="Helvetica-Bold", fontSize=8, textColor=GRIS_MEDIO, leading=11)
    s["valor"] = ParagraphStyle("valor",
        fontName="Helvetica", fontSize=9, textColor=NEGRO, leading=12)
    s["metodo"] = ParagraphStyle("metodo",
        fontName="Helvetica", fontSize=8.5, textColor=GRIS_OSCURO,
        alignment=TA_JUSTIFY, leading=13)
    s["disclaimer"] = ParagraphStyle("disclaimer",
        fontName="Helvetica-Oblique", fontSize=7.5, textColor=GRIS_MEDIO,
        alignment=TA_CENTER, leading=11)
    s["normal"] = ParagraphStyle("normal",
        fontName="Helvetica", fontSize=9, textColor=GRIS_OSCURO, leading=13)
    return s


# ── AYUDAS ────────────────────────────────────────────────────────────────────

def _sec_hdr(title, styles):
    """Barra de sección azul."""
    bar = Table([[Paragraph(f"▸  {title.upper()}", styles["sec_hdr"])]],
                colWidths=[CONTENT_W])
    bar.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), AZUL_OSCURO),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
    ]))
    return [bar, Spacer(1, 3)]


def _kv_table(items, styles):
    """Tabla label/valor con filas alternadas."""
    rows = [[Paragraph(k.upper(), styles["label"]),
             Paragraph(str(v) if v else "—", styles["valor"])]
            for k, v in items]
    t = Table(rows, colWidths=[4*cm, CONTENT_W - 4*cm])
    cmds = [
        ("VALIGN",        (0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",   (0,0),(-1,-1), 9),
        ("RIGHTPADDING",  (0,0),(-1,-1), 9),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("BACKGROUND",    (0,0),(0,-1),  GRIS_CLARO),
        ("LINEBELOW",     (0,0),(-1,-2), 0.3, BORDE),
    ]
    for i in range(len(rows)):
        cmds.append(("BACKGROUND",(1,i),(1,i), BLANCO if i%2==0 else colors.HexColor("#FAFBFD")))
    t.setStyle(TableStyle(cmds))
    return t


# ── SECCIONES ─────────────────────────────────────────────────────────────────

def _build_header(data, logo_path, styles):
    fecha     = data.get("fecha", datetime.now().strftime("%d/%m/%Y"))
    tipo      = data.get("tipo_propiedad", "Propiedad")
    direccion = data.get("direccion", "")
    barrio    = data.get("barrio", "")
    sub = tipo + (f" · {direccion}" if direccion else "") + (f", {barrio}" if barrio else "")

    if logo_path and os.path.exists(logo_path):
        try:
            logo_cell = Image(logo_path, width=3.8*cm, height=1.4*cm, kind="proportional")
        except Exception:
            logo_cell = Paragraph("<b>LUMEN</b>", styles["titulo"])
    else:
        logo_cell = Paragraph("<b>LUMEN</b>",
            ParagraphStyle("logo_big", fontName="Helvetica-Bold", fontSize=22,
                           textColor=AZUL_OSCURO, leading=26))

    right = [
        Paragraph("INFORME DE TASACIÓN INMOBILIARIA", styles["titulo"]),
        Spacer(1, 3),
        Paragraph(sub, styles["subtitulo"]),
        Paragraph(f"Fecha de emisión: {fecha}", styles["subtitulo"]),
    ]
    tbl = Table([[logo_cell, right]], colWidths=[4*cm, CONTENT_W - 4*cm])
    tbl.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
    ]))
    hr1 = HRFlowable(width="100%", thickness=2.5, color=AZUL_OSCURO, spaceAfter=2, spaceBefore=4)
    hr2 = HRFlowable(width="100%", thickness=1.2, color=DORADO,      spaceAfter=4, spaceBefore=0)
    return [tbl, hr1, hr2]


def _build_agent_section(data, styles):
    items = [
        ("Agente",   data.get("agent_name",  data.get("full_name", ""))),
        ("Email",    data.get("agent_email", data.get("email", ""))),
        ("Teléfono", data.get("agent_phone", data.get("phone", ""))),
    ]
    return _sec_hdr("Datos del Agente", styles) + [_kv_table(items, styles)]


def _build_property_section(data, styles):
    estado    = int(data.get("estado_edilicio", 1))
    ubicacion = int(data.get("ubicacion", 1))
    items = [
        ("Tipo de Propiedad", data.get("tipo_propiedad", "")),
        ("Dirección",         data.get("direccion", "")),
        ("Barrio / Zona",     data.get("barrio", "")),
        ("Superficie",        f"{data.get('metros2', 0):.1f} m²"),
        ("Estado Edilicio",   f"{estado} – {ESTADO_LABELS.get(estado,'—')}"),
        ("Ubicación",         f"{ubicacion} – {UBICACION_LABELS.get(ubicacion,'—')}"),
    ]
    link = data.get("link_propiedad", "").strip()
    if link:
        items.append(("Publicación", link[:100] + ("..." if len(link) > 100 else "")))
    return _sec_hdr("Datos de la Propiedad Tasada", styles) + [_kv_table(items, styles)]


def _build_method_section(styles):
    txt = (
        "El presente informe utiliza el <b>Método Comparativo de Mercado (MCM)</b>, "
        "que determina el valor de una propiedad mediante el análisis de inmuebles similares "
        "recientemente ofrecidos o transaccionados en el mercado. "
        "Para cada comparable se calcula el precio por metro cuadrado (USD/m²) y se aplica un "
        "<b>factor de ajuste</b> que pondera las diferencias en estado edilicio y ubicación, "
        "en una escala de 1 (Malo/Mala) a 4 (Excelente). "
        "El promedio de los USD/m² ajustados multiplicado por la superficie tasada determina "
        "el <b>valor medio estimado</b>. El rango mínimo y máximo se obtiene aplicando ±8% "
        "sobre dicho valor central."
    )
    box = Table([[Paragraph(txt, styles["metodo"])]], colWidths=[CONTENT_W])
    box.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#F0F4FA")),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("TOPPADDING",    (0,0),(-1,-1), 9),
        ("BOTTOMPADDING", (0,0),(-1,-1), 9),
        ("LINEBEFORE",    (0,0),(0,-1),  2.5, DORADO),
    ]))
    return _sec_hdr("Metodología de Tasación", styles) + [box]


def _build_comparables_table(resultado, styles):
    comps = resultado.get("comparables", [])
    if not comps:
        return _sec_hdr("Tabla de Comparables", styles) + [
            Paragraph("No se registraron comparables.", styles["normal"])]

    # Estilos de celda
    def ps(name, align=TA_CENTER, bold=False, color=NEGRO, size=7.5):
        return ParagraphStyle(name, fontName="Helvetica-Bold" if bold else "Helvetica",
                              fontSize=size, textColor=color, alignment=align, leading=10)

    th  = ps("th",  TA_CENTER, bold=True,  color=BLANCO,      size=7.5)
    tdc = ps("tdc", TA_CENTER, bold=False, color=NEGRO,        size=8)
    tdr = ps("tdr", TA_RIGHT,  bold=False, color=NEGRO,        size=8)
    tdb = ps("tdb", TA_RIGHT,  bold=True,  color=AZUL_OSCURO,  size=8)

    # Anchos de columna ajustados para que quepan sin solaparse
    col_w = [0.7*cm, 1.5*cm, 2.8*cm, 2.1*cm, 2.1*cm, 2.3*cm, 1.9*cm, 2.4*cm]
    # Total = 15.8 cm < CONTENT_W ~17 cm → OK con padding

    hdrs = ["N°", "m²", "Precio USD", "Estado\nEdilicio",
            "Ubicación", "USD/m²\nBase", "Factor\nAjuste", "USD/m²\nAjust."]
    table_data = [[Paragraph(h, th) for h in hdrs]]

    for c in comps:
        table_data.append([
            Paragraph(str(c["numero"]), tdc),
            Paragraph(f"{c['metros2']:.0f}", tdc),
            Paragraph(format_usd(c["precio"]), tdr),
            Paragraph(f"{c['estado_edilicio']}–{c['estado_label']}", tdc),
            Paragraph(f"{c['ubicacion']}–{c['ubicacion_label']}", tdc),
            Paragraph(format_usd(c["usd_m2_base"]), tdr),
            Paragraph(f"{c['factor_ajuste']:.3f}", tdc),
            Paragraph(f"<b>{format_usd(c['usd_m2_ajustado'])}</b>", tdb),
        ])

    # Fila promedio (SPAN sobre las 7 primeras cols)
    promedio = resultado.get("promedio_usd_m2", 0)
    prom_l = ps("pl", TA_CENTER, bold=True, color=AZUL_OSCURO, size=8)
    prom_v = ps("pv", TA_RIGHT,  bold=True, color=AZUL_OSCURO, size=9)
    table_data.append([
        Paragraph("PROMEDIO USD/m²", prom_l),
        Paragraph("", prom_l),
        Paragraph("", prom_l),
        Paragraph("", prom_l),
        Paragraph("", prom_l),
        Paragraph("", prom_l),
        Paragraph("", prom_l),
        Paragraph(f"<b>{format_usd(promedio)}</b>", prom_v),
    ])

    n = len(comps)
    t = Table(table_data, colWidths=col_w, repeatRows=1)
    cmds = [
        ("BACKGROUND",    (0,0),(-1,0),   AZUL_OSCURO),
        ("LINEBELOW",     (0,0),(-1,0),   1.2, DORADO),
        ("BACKGROUND",    (0,-1),(-1,-1), AZUL_CLARO),
        ("LINEABOVE",     (0,-1),(-1,-1), 0.8, AZUL_OSCURO),
        ("SPAN",          (0,-1),(6,-1)),
        ("VALIGN",        (0,0),(-1,-1),  "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1),  5),
        ("BOTTOMPADDING", (0,0),(-1,-1),  5),
        ("LEFTPADDING",   (0,0),(-1,-1),  3),
        ("RIGHTPADDING",  (0,0),(-1,-1),  3),
        ("GRID",          (0,0),(-1,-1),  0.25, BORDE),
    ]
    for i in range(1, n + 1):
        cmds.append(("BACKGROUND",(0,i),(-1,i), GRIS_CLARO if i%2==1 else BLANCO))
    t.setStyle(TableStyle(cmds))
    return _sec_hdr("Tabla de Comparables", styles) + [t]


def _build_results_section(resultado, data, styles):
    v_min  = resultado.get("valor_minimo", 0)
    v_med  = resultado.get("valor_medio",  0)
    v_max  = resultado.get("valor_maximo", 0)
    usd_m2 = resultado.get("usd_m2_ajustado_final", 0)
    m2     = data.get("metros2", resultado.get("metros2_sujeto", 0))
    margen = resultado.get("margen_pct", 8)

    # Celdas de valor individual
    def val_cell(label, value, bg, val_color, val_size, col_w):
        lbl_ps = ParagraphStyle("lbl", fontName="Helvetica-Bold", fontSize=9,
                                textColor=colors.HexColor("#B8CCE4"), alignment=TA_CENTER, leading=12)
        val_ps = ParagraphStyle("val", fontName="Helvetica-Bold", fontSize=val_size,
                                textColor=val_color, alignment=TA_CENTER, leading=val_size+4)
        c = Table([[Paragraph(label, lbl_ps)],[Paragraph(value, val_ps)]],
                  colWidths=[col_w])
        c.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), bg),
            ("TOPPADDING",    (0,0),(-1,-1), 11),
            ("BOTTOMPADDING", (0,0),(-1,-1), 11),
            ("LEFTPADDING",   (0,0),(-1,-1), 5),
            ("RIGHTPADDING",  (0,0),(-1,-1), 5),
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ]))
        return c

    cw_side = 5.1*cm
    cw_mid  = CONTENT_W - 2*cw_side

    cell_min = val_cell("VALOR MÍNIMO",   format_usd(v_min), AZUL_MEDIO,  BLANCO, 15, cw_side)
    cell_med = val_cell("VALOR ESTIMADO", format_usd(v_med), AZUL_OSCURO, DORADO, 21, cw_mid)
    cell_max = val_cell("VALOR MÁXIMO",   format_usd(v_max), AZUL_MEDIO,  BLANCO, 15, cw_side)

    row_tbl = Table([[cell_min, cell_med, cell_max]], colWidths=[cw_side, cw_mid, cw_side])
    row_tbl.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
        ("LINEAFTER",     (0,0),(1,-1),  1, BLANCO),
    ]))

    # Fila resumen
    lbl_r = ParagraphStyle("lr", fontName="Helvetica-Bold", fontSize=7.5,
                           textColor=GRIS_MEDIO, alignment=TA_CENTER, leading=10)
    val_r = ParagraphStyle("vr", fontName="Helvetica-Bold", fontSize=9.5,
                           textColor=AZUL_OSCURO, alignment=TA_CENTER, leading=13)
    cw_summary = [3.2*cm, 2.8*cm, 2.6*cm, 2.4*cm, 2.8*cm, 2.6*cm]
    summary = Table([[
        Paragraph("USD/m²\nAjustado Prom.", lbl_r),
        Paragraph(format_usd(usd_m2)+"/m²", val_r),
        Paragraph("Superficie\nTasada", lbl_r),
        Paragraph(f"{m2:.1f} m²", val_r),
        Paragraph("Margen de\nVariación", lbl_r),
        Paragraph(f"±{margen:.0f}%", val_r),
    ]], colWidths=cw_summary)
    summary.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), GRIS_CLARO),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LINEAFTER",     (0,0),(4,-1),  0.3, BORDE),
    ]))

    return _sec_hdr("Resultado de la Tasación", styles) + [
        row_tbl, Spacer(1, 2), summary]


def _build_notes_section(notas, styles):
    box = Table([[Paragraph(notas, styles["metodo"])]], colWidths=[CONTENT_W])
    box.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#FFFDF0")),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LINEBEFORE",    (0,0),(0,-1),  2.5, DORADO),
    ]))
    return _sec_hdr("Notas y Observaciones", styles) + [box]


def _build_signature_section(data, styles):
    agent = data.get("agent_name", data.get("full_name", ""))
    fecha = data.get("fecha", datetime.now().strftime("%d/%m/%Y"))

    ag_ps   = ParagraphStyle("ag", fontName="Helvetica-Bold", fontSize=10,
                             textColor=AZUL_OSCURO, alignment=TA_CENTER, leading=14)
    role_ps = ParagraphStyle("ro", fontName="Helvetica", fontSize=8,
                             textColor=GRIS_MEDIO, alignment=TA_CENTER, leading=12)

    hw = (CONTENT_W / 2) - 0.4*cm
    sig_left = Table([
        [Paragraph("_" * 36, role_ps)],
        [Paragraph(agent, ag_ps)],
        [Paragraph("Agente Inmobiliario Certificado", role_ps)],
        [Paragraph(f"Fecha: {fecha}", role_ps)],
    ], colWidths=[hw])
    sig_left.setStyle(TableStyle([
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
    ]))

    disc = Table([[Paragraph(
        "Este informe es de carácter referencial y no constituye una "
        "oferta formal de compra o venta. Los valores expresados son "
        "estimaciones basadas en datos de mercado disponibles.",
        styles["disclaimer"]
    )]], colWidths=[hw + 0.8*cm])
    disc.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), GRIS_CLARO),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))

    full = Table([[sig_left, disc]], colWidths=[hw, hw + 0.8*cm])
    full.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
    ]))
    return [Spacer(1, 0.8*cm), full]
