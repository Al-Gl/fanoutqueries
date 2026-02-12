from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import io

def create_pdf_report(data):
    """
    Generates a PDF report based on the provided data.
    Returns a BytesIO object containing the PDF.
    
    data structure expected:
    {
        "target_country": str,
        "primary_brand": str,
        "competitors": list,
        "metrics": {
            "sov_you": float,
            "sov_comp": float,
            "you_count": int,
            "comp_count": int,
            "total_queries": int
        },
        "detailed_hits": list of dicts [{'query', 'brands', 'type', 'snippet'}]
    }
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CenterTitle', parent=styles['Heading1'], alignment=TA_CENTER, spaceAfter=20, fontSize=24, textColor=colors.HexColor("#2C3E50")))
    styles.add(ParagraphStyle(name='SubTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=14, textColor=colors.HexColor("#7F8C8D")))
    styles.add(ParagraphStyle(name='SectionHeader', parent=styles['Heading2'], spaceBefore=20, spaceAfter=10, textColor=colors.HexColor("#2980B9")))
    styles.add(ParagraphStyle(name='NormalSmall', parent=styles['Normal'], fontSize=9, leading=11))
    
    story = []
    
    # --- TITLE PAGE ---
    story.append(Spacer(1, 60))
    story.append(Paragraph("Fan-Out Query Explorer", styles['CenterTitle']))
    story.append(Paragraph("Market Intelligence Report", styles['SubTitle']))
    story.append(Spacer(1, 30))
    
    date_str = datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph(f"Generated on: {date_str}", styles['SubTitle']))
    story.append(Paragraph(f"Target Market: {data.get('target_country', 'N/A')}", styles['SubTitle']))
    
    if data.get('primary_brand'):
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Focus Brand: {data.get('primary_brand')}", styles['SubTitle']))
        
    story.append(PageBreak())
    
    # --- EXECUTIVE SUMMARY ---
    story.append(Paragraph("Executive Summary", styles['SectionHeader']))
    
    metrics = data.get('metrics', {})
    
    summary_text = f"""
    This report analyzes <b>{metrics.get('total_queries', 0)}</b> generated search queries to understand brand visibility 
    and share of voice in the <b>{data.get('target_country')}</b> market.
    """
    story.append(Paragraph(summary_text, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Metrics Table
    t_data = [
        ['Metric', 'Count', 'Share of Voice'],
        ['Your Brand', f"{metrics.get('you_count', 0)}", f"{metrics.get('sov_you', 0):.1f}%"],
        ['Competitors', f"{metrics.get('comp_count', 0)}", f"{metrics.get('sov_comp', 0):.1f}%"],
    ]
    
    t = Table(t_data, colWidths=[200, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ECF0F1")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#BDC3C7")),
        ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor("#27AE60")), # Green for You
        ('TEXTCOLOR', (0, 2), (0, 2), colors.HexColor("#C0392B")), # Red for Comp
        ('FONTNAME', (0, 1), (0, 2), 'Helvetica-Bold'),
    ]))
    story.append(t)
    
    story.append(Spacer(1, 40))
    
    # --- DETAILED FINDINGS ---
    story.append(Paragraph("Brand Mentions Log", styles['SectionHeader']))
    story.append(Paragraph("The following table details specific search queries where brand mentions were detected.", styles['Normal']))
    story.append(Spacer(1, 15))
    
    hits = data.get('detailed_hits', [])
    
    if not hits:
        story.append(Paragraph("No specific brand mentions were found in this analysis.", styles['Normal']))
    else:
        # Table Header
        h_data = [['Who', 'Fan-Out Query', 'Brands Found']]
        
        # Limit rows to avoid huge PDFs if many results, or just paginate
        # For this version, we list all
        for hit in hits:
            # Shorten query if too long
            q = hit.get('query', '')
            if len(q) > 60: q = q[:57] + "..."
            
            b_found = hit.get('brands', '')
            who = hit.get('type', 'Unknown')
            
            h_data.append([who, q, b_found])
            
        t2 = Table(h_data, colWidths=[80, 250, 120], repeatRows=1)
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#ECF0F1")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'), # Who column center
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),   # Query column left
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        # Color code rows based on 'Who'
        for i, row in enumerate(h_data[1:], start=1):
            if "You" in row[0]: # "✅ You"
                t2.setStyle(TableStyle([('TEXTCOLOR', (0, i), (0, i), colors.HexColor("#27AE60"))]))
            elif "Competitor" in row[0]:
                t2.setStyle(TableStyle([('TEXTCOLOR', (0, i), (0, i), colors.HexColor("#C0392B"))]))

        story.append(t2)

    doc.build(story)
    buffer.seek(0)
    return buffer
