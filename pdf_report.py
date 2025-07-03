
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch


def generate_unique_name(fixed_part="item"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{fixed_part}_{timestamp}"


def generate_pdf_report(user_query, specific_dates, result_data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch
    )

    elements = []

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.fontName = 'Helvetica-Bold'
    title_style.fontSize = 16
    title_style.alignment = 1  # Center

    subtitle_style = styles['Heading3']
    subtitle_style.fontName = 'Helvetica'
    subtitle_style.fontSize = 12
    subtitle_style.alignment = 1  # Center

    # Cell style
    cell_style = ParagraphStyle(
        name='CellStyle',
        fontName='Helvetica',
        fontSize=10,
        alignment=1,  # Center
        wordWrap='CJK',
        spaceAfter=4
    )

    elements.append(Paragraph(f"Attendance Report<br/>{user_query}", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Spacer(1, 24))

    try:
        if result_data:
            columns = list(result_data[0].keys())
            header_row = [Paragraph(col.title().replace("Empname", "Employee Name").replace("Vrdate", "Date"), cell_style) for col in columns]
            table_data = [header_row]

            for row in result_data:
                wrapped_row = [Paragraph(str(row.get(col, "")), cell_style) for col in columns]
                table_data.append(wrapped_row)
        else:
            table_data = [[Paragraph("No data found", cell_style)]]
            columns = ["Message"]

        total_width = A4[0] - doc.leftMargin - doc.rightMargin
        num_columns = len(columns)
        col_width = total_width / num_columns if num_columns > 0 else total_width

        table = Table(table_data, colWidths=[col_width] * num_columns, repeatRows=1)

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.skyblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(table)

    except Exception as e:
        error_msg = f"Error while generating table: {str(e)}"
        elements.append(Paragraph(error_msg, styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer
