"""
Table builders for PM reports.
Coverage tables, comparison tables, source reference tables.
"""

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle
from .styles import C


def coverage_table(data, col_widths=None):
    """
    Build a colored coverage table.

    data: list of rows, each row = [section_name, ops_count, coverage_level, notes]
    coverage_level should be one of: FULL, HIGH, MEDIUM, LOW, NONE

    Returns a Table flowable.
    """
    header = ["Section", "Operations", "Coverage", "Notes"]
    table_data = [header] + data

    if col_widths is None:
        col_widths = [2.2*inch, 0.8*inch, 1.0*inch, 3.0*inch]

    t = Table(table_data, colWidths=col_widths)

    base_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(C.BLUE_DARK)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (2, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(C.BORDER_LIGHT)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(C.BG_ROW_ALT)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]

    # Color the coverage column by level
    coverage_colors = {
        "FULL": C.GREEN,
        "HIGH": C.GREEN,
        "MEDIUM": C.YELLOW,
        "LOW": C.RED,
        "NONE": C.RED,
    }
    for i, row in enumerate(data, start=1):
        level = row[2].upper() if len(row) > 2 else ""
        color = coverage_colors.get(level)
        if color:
            base_style.append(("TEXTCOLOR", (2, i), (2, i), colors.HexColor(color)))
        if level in ("LOW", "NONE"):
            base_style.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))

    t.setStyle(TableStyle(base_style))
    return t


def comparison_table(headers, data, col_widths=None):
    """
    Build a side-by-side comparison table.

    headers: list of column headers
    data: list of rows
    """
    table_data = [headers] + data

    if col_widths is None:
        total = 7.0 * inch
        col_widths = [total / len(headers)] * len(headers)

    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(C.GRAY_DARK)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(C.BORDER_LIGHT)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(C.BG_ROW_ALT)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def bridge_table(data, col_widths=None):
    """
    Build a "how we bridge the gap" table.

    data: list of rows = [gap_area, module, api_used, browser_fills]
    """
    header = ["Gap Area", "Module", "API Used", "Browser Fills"]
    table_data = [header] + data

    if col_widths is None:
        col_widths = [1.2*inch, 1.3*inch, 1.6*inch, 2.4*inch]

    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(C.BLUE)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(C.BORDER_LIGHT)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(C.BG_BLUE)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def source_table(doc_refs):
    """
    Build a source documentation reference table.

    doc_refs: list of (label, url, scope_description)
    """
    table_data = [["Source", "URL", "Scope"]]
    for label, url, scope in doc_refs:
        table_data.append([label, url, scope])

    t = Table(table_data, colWidths=[1.5*inch, 3.2*inch, 2.0*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(C.GRAY_DARK)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor(C.BORDER_LIGHT)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(C.BG_ROW_ALT)]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR", (1, 1), (1, -1), colors.HexColor(C.BLUE)),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t
