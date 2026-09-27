"""Genera el PDF de una factura emitida (Invoice) para enviar al cliente."""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

from app.models.models import Invoice

_ESTILOS = getSampleStyleSheet()
_TITULO = ParagraphStyle("TituloFactura", parent=_ESTILOS["Title"], alignment=2, fontSize=22)
_ETIQUETA = ParagraphStyle("Etiqueta", parent=_ESTILOS["Normal"], textColor=colors.HexColor("#6b7280"), fontSize=9)
_BLOQUE = ParagraphStyle("Bloque", parent=_ESTILOS["Normal"], fontSize=10, leading=14)
_BLOQUE_NOMBRE = ParagraphStyle("BloqueNombre", parent=_BLOQUE, fontName="Helvetica-Bold")


def _euros(valor: float) -> str:
    return f"{valor:,.2f} €".replace(",", "_").replace(".", ",").replace("_", ".")


def _bloque_parte(etiqueta: str, nombre: str, nif: str | None, direccion: str | None) -> list:
    lineas = [Paragraph(etiqueta, _ETIQUETA), Paragraph(nombre, _BLOQUE_NOMBRE)]
    if nif:
        lineas.append(Paragraph(f"NIF/CIF: {nif}", _BLOQUE))
    if direccion:
        lineas.append(Paragraph(direccion, _BLOQUE))
    return lineas


def generar_pdf_factura(factura: Invoice) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title=f"Factura {factura.numero}",
    )
    elementos = []

    elementos.append(Paragraph("FACTURA", _TITULO))
    elementos.append(Spacer(1, 4))
    elementos.append(Paragraph(f"Nº {factura.numero} · {factura.fecha.strftime('%d/%m/%Y')}", _BLOQUE))
    elementos.append(Spacer(1, 16))

    partes = Table(
        [[
            _bloque_parte("EMISOR", factura.emisor_nombre, factura.emisor_nif, factura.emisor_direccion),
            _bloque_parte("CLIENTE", factura.cliente_nombre, factura.cliente_nif, factura.cliente_direccion),
        ]],
        colWidths=["50%", "50%"],
    )
    partes.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elementos.append(partes)
    elementos.append(Spacer(1, 20))

    concepto = factura.concepto or "Servicios prestados"
    elementos.append(Table([[Paragraph(concepto, _BLOQUE)]], colWidths=["100%"], style=[
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e4e9")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(Spacer(1, 20))

    filas = [["Base imponible", _euros(factura.base_imponible)]]
    filas.append([f"IVA ({factura.tipo_iva:g}%)", _euros(factura.cuota_iva)])
    if factura.retencion_irpf_pct:
        filas.append([f"Retención IRPF ({factura.retencion_irpf_pct:g}%)", "− " + _euros(factura.retencion_importe)])
    filas.append(["TOTAL", _euros(factura.total)])

    tabla_totales = Table(filas, colWidths=[None, 100], hAlign="RIGHT")
    tabla_totales.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.HexColor("#1f2430")),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 4),
    ]))
    elementos.append(tabla_totales)

    doc.build(elementos)
    return buffer.getvalue()
