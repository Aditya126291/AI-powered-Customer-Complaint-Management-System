import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

output_dir = r"c:\Users\Aditya Kumar\OneDrive\Desktop\AI powered customer complaint management system\sample_documents"
os.makedirs(output_dir, exist_ok=True)

# ---------------------------------------------------------
# Document 1: Zenith_Life_Sciences_Complaint_Report.pdf
# ---------------------------------------------------------
pdf_path_1 = os.path.join(output_dir, "Zenith_Life_Sciences_Complaint_Report.pdf")
doc1 = SimpleDocTemplate(pdf_path_1, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontName='Helvetica-Bold',
    fontSize=18,
    textColor=colors.HexColor('#1E293B'),
    spaceAfter=6
)
subtitle_style = ParagraphStyle(
    'DocSubTitle',
    parent=styles['Normal'],
    fontName='Helvetica-Oblique',
    fontSize=10,
    textColor=colors.HexColor('#64748B'),
    spaceAfter=15
)
body_style = ParagraphStyle(
    'DocBody',
    parent=styles['Normal'],
    fontName='Helvetica',
    fontSize=10,
    leading=14,
    textColor=colors.HexColor('#334155')
)
bold_body_style = ParagraphStyle(
    'DocBodyBold',
    parent=body_style,
    fontName='Helvetica-Bold'
)

story1 = []
story1.append(Paragraph("QUALITY ASSURANCE CUSTOMER COMPLAINT REPORT", title_style))
story1.append(Paragraph("Reference No: CC-2026-00154 | Date: 26 July 2026 | Priority: HIGH", subtitle_style))
story1.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#4F46E5'), spaceAfter=15))

table_data_1 = [
    [Paragraph("Complaint Source:", bold_body_style), Paragraph("Email Notification", body_style)],
    [Paragraph("Customer Name:", bold_body_style), Paragraph("ABC Formulations Ltd. (Client: Zenith Life Sciences)", body_style)],
    [Paragraph("Product Name:", bold_body_style), Paragraph("Metformin Hydrochloride API", body_style)],
    [Paragraph("Product Strength / Grade:", bold_body_style), Paragraph("IP / BP Grade", body_style)],
    [Paragraph("Batch / Lot Number:", bold_body_style), Paragraph("MFH260712A", body_style)],
    [Paragraph("Affected Quantity:", bold_body_style), Paragraph("25 kg (1 HDPE Drum)", body_style)],
    [Paragraph("Manufacturing Date:", bold_body_style), Paragraph("25 June 2026", body_style)],
    [Paragraph("Expiry Date:", bold_body_style), Paragraph("Not Provided", body_style)],
    [Paragraph("Originating Site Block:", bold_body_style), Paragraph("API Synthesis Unit - Block B", body_style)],
    [Paragraph("Impacted Materials:", bold_body_style), Paragraph("Primary Packaging (HDPE Drum & Poly Liner)", body_style)],
]

t1 = Table(table_data_1, colWidths=[160, 370])
t1.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ('PADDING', (0,0), (-1,-1), 6),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
]))
story1.append(t1)
story1.append(Spacer(1, 15))

story1.append(Paragraph("DEFECT SUMMARY & NARRATIVE", ParagraphStyle('SectionHeader', parent=bold_body_style, fontSize=12, textColor=colors.HexColor('#1E293B'))))
story1.append(Spacer(1, 6))
narrative_text_1 = (
    "During incoming quality control inspection at ABC Formulations Ltd., quality inspectors observed multiple dark foreign particles "
    "embedded within the bulk powder of one sealed 25 kg HDPE drum of Metformin Hydrochloride API (Batch: MFH260712A). "
    "The outer HDPE container showed no visible external damage or tamper marks upon receipt. The material has been immediately quarantined "
    "pending formal laboratory investigation and investigation of manufacturing logs."
)
story1.append(Paragraph(narrative_text_1, body_style))
story1.append(Spacer(1, 15))

story1.append(Paragraph("INITIAL RISK CLASSIFICATION", ParagraphStyle('SectionHeader2', parent=bold_body_style, fontSize=12, textColor=colors.HexColor('#1E293B'))))
story1.append(Spacer(1, 6))
story1.append(Paragraph("<b>Suggested Severity:</b> CRITICAL", body_style))
story1.append(Paragraph("<b>Suggested Next Action:</b> Immediate Laboratory investigation & manufacturing record audit", body_style))
story1.append(Paragraph("<b>Initial Assessment:</b> Potential foreign matter contamination. High impact to API quality requiring immediate QA containment.", body_style))

doc1.build(story1)

# ---------------------------------------------------------
# Document 2: Apollo_Pharmacy_Discolored_Capsules.txt
# ---------------------------------------------------------
txt_path_2 = os.path.join(output_dir, "Apollo_Pharmacy_Discolored_Capsules.txt")
with open(txt_path_2, "w", encoding="utf-8") as f:
    f.write("""CUSTOMER COMPLAINT INTAKE FORM

Customer Name: Apollo Pharmacy
Complaint Source: Retail Pharmacy Outlet
Date of Incident: 28 July 2026

PRODUCT & BATCH INFORMATION:
Product Name: Amoxicillin Capsules
Product Strength: 500 mg
Batch / Lot Number: AMX240602
Manufacturing Date: March 2026
Expiry Date: February 2028
Affected Quantity: 48 capsules (4 blister packs)

DESCRIPTION OF COMPLAINT:
Apollo Pharmacy reported 48 discolored capsules in Amoxicillin Capsules 500 mg (Batch AMX240602) found in a sealed customer box. 
Capsules showed brownish discoloration instead of normal yellow/white color. 
Requesting root cause investigation, replacement of batch, and formal QA closure.

REMARKS / INITIAL RISK:
Suggested Severity: Major
Initial Risk Assessment: Potential moisture ingress or primary packaging seal failure leading to capsule discoloration.
""")

# ---------------------------------------------------------
# Document 3: Global_Pharma_Packaging_Defect_Report.pdf
# ---------------------------------------------------------
pdf_path_3 = os.path.join(output_dir, "Global_Pharma_Packaging_Defect_Report.pdf")
doc3 = SimpleDocTemplate(pdf_path_3, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)

story3 = []
story3.append(Paragraph("QUALITY MANAGEMENT SYSTEM - INCIDENT REPORT", title_style))
story3.append(Paragraph("Report ID: QMS-2026-9042 | Customer: Global Pharma Logistics | Date: 28 July 2026", subtitle_style))
story3.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#DC2626'), spaceAfter=15))

table_data_3 = [
    [Paragraph("Complaint Source:", bold_body_style), Paragraph("Logistics Warehouse Inspection", body_style)],
    [Paragraph("Customer Name:", bold_body_style), Paragraph("Global Pharma Logistics", body_style)],
    [Paragraph("Product Name:", bold_body_style), Paragraph("Paracetamol Oral Suspension", body_style)],
    [Paragraph("Product Strength / Dosage:", bold_body_style), Paragraph("120 mg / 5 mL (100 mL Bottle)", body_style)],
    [Paragraph("Batch / Lot Number:", bold_body_style), Paragraph("PAR202604B", body_style)],
    [Paragraph("Affected Quantity:", bold_body_style), Paragraph("500 bottles (5 Master Shipper Cartons)", body_style)],
    [Paragraph("Manufacturing Date:", bold_body_style), Paragraph("10 April 2026", body_style)],
    [Paragraph("Expiry Date:", bold_body_style), Paragraph("09 April 2028", body_style)],
    [Paragraph("Impacted Non-Product Material:", bold_body_style), Paragraph("Secondary Shipper Packaging & Bottle Cap Seals", body_style)],
]

t3 = Table(table_data_3, colWidths=[160, 370])
t3.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FCA5A5')),
    ('PADDING', (0,0), (-1,-1), 6),
    ('VALIGN', (0,0), (-1,-1), 'TOP'),
]))
story3.append(t3)
story3.append(Spacer(1, 15))

story3.append(Paragraph("INCIDENT DETAILS", ParagraphStyle('SectionHeader3', parent=bold_body_style, fontSize=12, textColor=colors.HexColor('#991B1B'))))
story3.append(Spacer(1, 6))
story3.append(Paragraph(
    "Upon receipt at central distribution hub, 5 master cartons of Paracetamol Oral Suspension 120mg/5ml (Batch: PAR202604B) "
    "were found wet with leaking liquid syrup. Inspection revealed loose cap torque on multiple bottles causing leakage during transit. "
    "Stock has been placed on QA hold.", body_style
))

doc3.build(story3)

print("Generated sample documents successfully!")
