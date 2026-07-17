from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
import os, json, uuid

REPORTS_DIR = "app/static/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

NAVY  = HexColor("#0F172A"); BLUE  = HexColor("#2563EB"); BLUE_L = HexColor("#EFF6FF")
BLUE_B= HexColor("#BFDBFE"); GREEN = HexColor("#16A34A"); GREEN_L= HexColor("#DCFCE7")
GRAY_9= HexColor("#111827"); GRAY_5= HexColor("#6B7280"); GRAY_3= HexColor("#D1D5DB")
GRAY_1= HexColor("#F3F4F6"); TEAL  = HexColor("#0D9488"); TEAL_L = HexColor("#F0FDFA")
ORANGE= HexColor("#EA580C"); ORANGE_L=HexColor("#FFF7ED"); RED=HexColor("#DC2626")
W = A4[0] - 3.6*cm

def S(n,**k):
    b=dict(fontName="Helvetica",fontSize=10,textColor=GRAY_9,leading=15)
    b.update(k); return ParagraphStyle(n,**b)

def sp(h=8): return Spacer(1,h)
def hr(c=GRAY_3,t=0.5): return HRFlowable(width="100%",thickness=t,color=c,spaceAfter=4,spaceBefore=4)

def _doc(filename):
    return SimpleDocTemplate(os.path.join(REPORTS_DIR,filename),pagesize=A4,
        leftMargin=1.8*cm,rightMargin=1.8*cm,topMargin=1.8*cm,bottomMargin=2*cm)

def _header_table(left_lines, right_lines, bg=BLUE):
    left = [Paragraph(t, S(f"hl{i}", fontName="Helvetica-Bold" if i==0 else "Helvetica",
                           fontSize=16 if i==0 else 10, textColor=white, leading=20 if i==0 else 14))
            for i,t in enumerate(left_lines)]
    right= [Paragraph(t, S(f"hr{i}", fontSize=9, textColor=HexColor("#BFDBFE"), alignment=TA_RIGHT, leading=13))
            for i,t in enumerate(right_lines)]
    t = Table([[left, right]], colWidths=[W*0.62, W*0.38])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),bg),("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),18),("BOTTOMPADDING",(0,0),(-1,-1),18),
        ("LEFTPADDING",(0,0),(0,0),18),("RIGHTPADDING",(-1,0),(-1,-1),18),
        ("ROUNDEDCORNERS",[10]),
    ]))
    return t

def generate_invoice_pdf(appointment, user, doctor) -> str:
    filename = f"invoice_{appointment.id}_{appointment.txn_id[:8]}.pdf"
    doc = _doc(filename)
    story = []
    now = datetime.now()
    platform_fee = appointment.platform_fee
    consult_fee  = appointment.fee_paid
    total        = consult_fee + platform_fee

    story.append(_header_table(
        ["CareBot Invoice", "Official Payment Receipt"],
        [f"Invoice #INV-{appointment.id:04d}", f"Date: {now.strftime('%d %b %Y')}", f"Txn: {appointment.txn_id}"]
    ))
    story.append(sp(14))

    # Patient + Doctor info
    info = [[
        [Paragraph("Bill To", S("bt",fontName="Helvetica-Bold",fontSize=9,textColor=GRAY_5)),
         Paragraph(user.full_name, S("un",fontName="Helvetica-Bold",fontSize=13,textColor=NAVY)),
         Paragraph(user.email, S("ue",fontSize=10,textColor=GRAY_5)),
         Paragraph(user.phone or "—", S("up",fontSize=10,textColor=GRAY_5))],
        [Paragraph("Consulting Doctor", S("cd",fontName="Helvetica-Bold",fontSize=9,textColor=GRAY_5)),
         Paragraph(f"Dr. {doctor.full_name}", S("dn",fontName="Helvetica-Bold",fontSize=13,textColor=NAVY)),
         Paragraph(doctor.specialty, S("ds",fontSize=10,textColor=GRAY_5)),
         Paragraph(doctor.qualification or "MBBS", S("dq",fontSize=10,textColor=GRAY_5))],
    ]]
    it = Table(info, colWidths=[W/2, W/2])
    it.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),BLUE_L),("GRID",(0,0),(-1,-1),0.5,BLUE_B),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LEFTPADDING",(0,0),(-1,-1),14),("VALIGN",(0,0),(-1,-1),"TOP"),
        ("ROUNDEDCORNERS",[6]),
    ]))
    story.append(it); story.append(sp(14))

    # Items table
    story.append(Paragraph("Billing Summary", S("bs",fontName="Helvetica-Bold",fontSize=12,textColor=NAVY)))
    story.append(sp(6))
    rows = [
        ["Description","Amount"],
        ["Online Consultation Fee", f"₹{consult_fee:,.0f}"],
        ["Platform Service Fee", f"₹{platform_fee:,.0f}"],
    ]
    bt = Table(rows, colWidths=[W-4*cm, 4*cm])
    bt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),10),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[white,BLUE_L]),
        ("GRID",(0,0),(-1,-1),0.5,GRAY_3),("ALIGN",(1,0),(1,-1),"RIGHT"),
        ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9),
        ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),
    ]))
    story.append(bt); story.append(sp(4))

    # Total row
    tr = Table([["", ""], ["Total Paid", f"₹{total:,.0f}"]], colWidths=[W-4*cm, 4*cm])
    tr.setStyle(TableStyle([
        ("BACKGROUND",(0,1),(-1,1),BLUE),("TEXTCOLOR",(0,1),(-1,1),white),
        ("FONTNAME",(0,1),(-1,1),"Helvetica-Bold"),("FONTSIZE",(0,1),(-1,1),12),
        ("ALIGN",(1,0),(1,-1),"RIGHT"),("TOPPADDING",(0,0),(-1,-1),10),
        ("BOTTOMPADDING",(0,0),(-1,-1),10),("LEFTPADDING",(0,0),(-1,-1),12),
        ("RIGHTPADDING",(0,0),(-1,-1),12),("ROUNDEDCORNERS",[6]),
    ]))
    story.append(tr); story.append(sp(20))

    # Status badge
    sb = Table([[Paragraph("✓  PAYMENT SUCCESSFUL", S("ps",fontName="Helvetica-Bold",fontSize=12,textColor=white,alignment=TA_CENTER))]], colWidths=[W])
    sb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),GREEN),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),("ROUNDEDCORNERS",[8])]))
    story.append(sb); story.append(sp(20))

    story.append(Paragraph(f"Transaction ID: {appointment.txn_id}", S("ti",fontSize=9,textColor=GRAY_5,alignment=TA_CENTER)))
    story.append(Paragraph(f"Paid on {now.strftime('%d %B %Y at %H:%M')} IST  •  CareBot Health Platform", S("pi",fontSize=9,textColor=GRAY_5,alignment=TA_CENTER)))
    story.append(sp(16))
    story.append(Paragraph("This is a computer-generated invoice. No signature required.", S("disc",fontSize=8,textColor=GRAY_5,alignment=TA_CENTER)))

    doc.build(story)
    return filename


def generate_prescription_pdf(appointment, prescription, user, doctor) -> str:
    filename = f"prescription_{appointment.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    doc = _doc(filename)
    story = []
    now = datetime.now()

    # Doctor letterhead
    story.append(_header_table(
        [f"Dr. {doctor.full_name}", doctor.specialty, doctor.qualification or "MBBS, MD"],
        ["CareBot Health Platform", f"Reg. #{doctor.id:04d}", now.strftime("%d %b %Y")]
    ))
    story.append(sp(12))

    # Patient info strip
    dob = user.dob.strftime("%d %b %Y") if user.dob else "N/A"
    pi_data = [
        [Paragraph("Patient Name",S("pl",fontName="Helvetica-Bold",fontSize=9,textColor=GRAY_5)),
         Paragraph("Age / DOB",S("al",fontName="Helvetica-Bold",fontSize=9,textColor=GRAY_5)),
         Paragraph("Gender",S("gl",fontName="Helvetica-Bold",fontSize=9,textColor=GRAY_5)),
         Paragraph("Date",S("dl",fontName="Helvetica-Bold",fontSize=9,textColor=GRAY_5))],
        [Paragraph(user.full_name,S("pv",fontName="Helvetica-Bold",fontSize=11,textColor=NAVY)),
         Paragraph(dob,S("av",fontSize=10,textColor=GRAY_9)),
         Paragraph(user.gender or "N/A",S("gv",fontSize=10,textColor=GRAY_9)),
         Paragraph(now.strftime("%d %b %Y"),S("dv",fontSize=10,textColor=GRAY_9))],
    ]
    pit = Table(pi_data, colWidths=[W/4]*4)
    pit.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),BLUE_L),("GRID",(0,0),(-1,-1),0.5,BLUE_B),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),10),("ROUNDEDCORNERS",[6]),
    ]))
    story.append(pit); story.append(sp(14))

    # Diagnosis
    story.append(Paragraph("Diagnosis", S("dh",fontName="Helvetica-Bold",fontSize=12,textColor=NAVY)))
    story.append(hr(BLUE_B,1))
    story.append(sp(4))
    diag_t = Table([[Paragraph(prescription.diagnosis or "As discussed", S("dg",fontSize=11,textColor=GRAY_9,leading=16))]], colWidths=[W])
    diag_t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),BLUE_L),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),("LEFTPADDING",(0,0),(-1,-1),14),("GRID",(0,0),(-1,-1),0.5,BLUE_B),("ROUNDEDCORNERS",[6])]))
    story.append(diag_t); story.append(sp(14))

    # Medicines
    try:
        meds = json.loads(prescription.medicines or "[]")
    except:
        meds = []
    if meds:
        story.append(Paragraph("℞  Prescription", S("rh",fontName="Helvetica-Bold",fontSize=12,textColor=NAVY)))
        story.append(hr(BLUE_B,1)); story.append(sp(6))
        med_rows = [["#","Medicine","Dosage","Frequency","Duration"]]
        for i,m in enumerate(meds,1):
            med_rows.append([
                str(i), m.get("name",""), m.get("dosage",""), m.get("frequency",""), m.get("duration","")
            ])
        mt = Table(med_rows, colWidths=[0.8*cm, W-9.3*cm, 2.5*cm, 3*cm, 3*cm])
        mt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),10),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[white,BLUE_L]),
            ("GRID",(0,0),(-1,-1),0.5,GRAY_3),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(-1,-1),8),("ALIGN",(0,0),(0,-1),"CENTER"),
        ]))
        story.append(mt); story.append(sp(14))

    # Instructions
    if prescription.instructions:
        story.append(Paragraph("Instructions & Advice", S("ih",fontName="Helvetica-Bold",fontSize=12,textColor=TEAL)))
        story.append(hr(HexColor("#99F6E4"),1)); story.append(sp(6))
        inst_t = Table([[Paragraph(prescription.instructions, S("ins",fontSize=10,textColor=GRAY_9,leading=16))]], colWidths=[W])
        inst_t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),TEAL_L),("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),("LEFTPADDING",(0,0),(-1,-1),14),("GRID",(0,0),(-1,-1),0.5,HexColor("#99F6E4")),("ROUNDEDCORNERS",[6])]))
        story.append(inst_t); story.append(sp(14))

    # Follow-up
    if prescription.follow_up:
        story.append(Paragraph(f"🗓  Follow-up: {prescription.follow_up}", S("fu",fontName="Helvetica-Bold",fontSize=11,textColor=ORANGE)))
        story.append(sp(20))

    # Signature line
    sig_data = [["", f"Dr. {doctor.full_name}"], ["", doctor.specialty], ["", "Digital Signature (CareBot Verified)"]]
    st = Table(sig_data, colWidths=[W*0.6, W*0.4])
    st.setStyle(TableStyle([("ALIGN",(1,0),(1,-1),"RIGHT"),("FONTNAME",(1,0),(1,0),"Helvetica-Bold"),("FONTSIZE",(1,0),(1,0),12),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),("TEXTCOLOR",(1,2),(1,2),GRAY_5),("FONTSIZE",(1,2),(1,2),9)]))
    story.append(hr()); story.append(st); story.append(sp(16))

    story.append(Paragraph("This prescription is issued via CareBot Health Platform and is valid for the stated consultation only. Always follow your doctor's advice.", S("disc2",fontSize=8,textColor=GRAY_5,alignment=TA_CENTER)))

    doc.build(story)
    return filename
