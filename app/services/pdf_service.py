from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, KeepTogether)
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import Flowable
from datetime import datetime
import os

REPORTS_DIR = "app/static/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# ── Color Palette ──────────────────────────────────────────────────────────────
NAVY       = HexColor("#0F172A")
BLUE       = HexColor("#2563EB")
BLUE_MID   = HexColor("#3B82F6")
BLUE_LIGHT = HexColor("#EFF6FF")
BLUE_BORDER= HexColor("#BFDBFE")
TEAL       = HexColor("#0D9488")
TEAL_LIGHT = HexColor("#F0FDFA")
GREEN      = HexColor("#16A34A")
GREEN_LIGHT= HexColor("#DCFCE7")
ORANGE     = HexColor("#EA580C")
ORANGE_LIGHT=HexColor("#FFF7ED")
RED        = HexColor("#DC2626")
RED_LIGHT  = HexColor("#FEF2F2")
PURPLE     = HexColor("#7C3AED")
PURPLE_LIGHT=HexColor("#F5F3FF")
GRAY_900   = HexColor("#111827")
GRAY_700   = HexColor("#374151")
GRAY_500   = HexColor("#6B7280")
GRAY_300   = HexColor("#D1D5DB")
GRAY_100   = HexColor("#F3F4F6")
GRAY_50    = HexColor("#F9FAFB")
WHITE      = white

W, H = A4
PAGE_W = W - 3.6*cm   # usable width with 1.8cm margins each side

# ── Custom Flowables ───────────────────────────────────────────────────────────
class ColorRect(Flowable):
    def __init__(self, width, height, color, radius=6):
        super().__init__()
        self.width = width
        self.height = height
        self.color = color
        self.radius = radius
    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=0)

class SectionChip(Flowable):
    def __init__(self, text, bg_color, text_color, width=PAGE_W):
        super().__init__()
        self.text = text
        self.bg_color = bg_color
        self.text_color = text_color
        self.width = width
        self.height = 36
    def draw(self):
        c = self.canv
        c.setFillColor(self.bg_color)
        c.roundRect(0, 0, self.width, self.height, 6, fill=1, stroke=0)
        c.setFillColor(self.text_color)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(14, 12, self.text)

# ── Style Helpers ──────────────────────────────────────────────────────────────
def S(name, **kw):
    base = dict(fontName="Helvetica", fontSize=10, textColor=GRAY_700, leading=16, spaceAfter=0, spaceBefore=0)
    base.update(kw)
    return ParagraphStyle(name, **base)

H1  = S("H1", fontName="Helvetica-Bold", fontSize=22, textColor=WHITE, leading=28, alignment=TA_CENTER)
H2  = S("H2", fontName="Helvetica-Bold", fontSize=13, textColor=NAVY, leading=18, spaceBefore=4)
H3  = S("H3", fontName="Helvetica-Bold", fontSize=11, textColor=BLUE, leading=15)
BODY= S("BODY", fontSize=10, textColor=GRAY_700, leading=15)
BODY_BOLD = S("BB", fontName="Helvetica-Bold", fontSize=10, textColor=GRAY_900, leading=15)
SMALL= S("SM", fontSize=9, textColor=GRAY_500, leading=13)
CENTER= S("CEN", fontSize=10, textColor=GRAY_700, alignment=TA_CENTER, leading=14)
WHITE_S = S("WS", fontSize=10, textColor=WHITE, leading=15)
WHITE_BOLD = S("WB", fontName="Helvetica-Bold", fontSize=11, textColor=WHITE, leading=16)
DISC_S = S("DISC", fontSize=8, textColor=GRAY_500, leading=12, alignment=TA_CENTER)

def sp(h=6): return Spacer(1, h)
def hr(color=GRAY_300, thickness=0.5): return HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=4, spaceBefore=4)

def bullet_row(text, color=BLUE, bold_prefix=None):
    if bold_prefix:
        return Paragraph(f'<font color="{color.hexval()}" name="Helvetica-Bold">■ {bold_prefix}</font>  {text}', BODY)
    return Paragraph(f'<font color="{color.hexval()}">●</font>  {text}', BODY)

def severity_color(sev):
    return {"Mild": GREEN, "Moderate": ORANGE, "Needs Attention": RED}.get(sev, BLUE)

# ── Section builder helper ─────────────────────────────────────────────────────
def section(icon_text, title, bg, text_color=WHITE):
    return [sp(14), SectionChip(f"  {icon_text}  {title}", bg, text_color), sp(8)]

# ── Main PDF Generator ────────────────────────────────────────────────────────
def generate_health_report(user, report_data: dict, session_id: str) -> str:
    filename = f"health_report_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.8*cm, bottomMargin=2*cm
    )

    story = []
    now = datetime.now()

    # ── COVER HEADER ──────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("🩺", S("ic", fontSize=28, textColor=WHITE, alignment=TA_CENTER)),
        [Paragraph("CareBot Health Report", H1),
         Paragraph("AI-Powered Personal Health Assessment", S("hs", fontSize=11, textColor=BLUE_LIGHT, alignment=TA_CENTER, leading=16))],
        Paragraph(now.strftime("%d %b %Y"), S("dt", fontSize=10, textColor=BLUE_LIGHT, alignment=TA_RIGHT, leading=14))
    ]]
    ht = Table(header_data, colWidths=[1.8*cm, PAGE_W-3.6*cm, 3.0*cm])
    ht.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), BLUE),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0), (-1,-1), 18),
        ("BOTTOMPADDING",(0,0), (-1,-1), 18),
        ("LEFTPADDING",  (0,0), (0,0),   14),
        ("RIGHTPADDING", (-1,0),(-1,-1), 14),
        ("ROUNDEDCORNERS", [10]),
    ]))
    story.append(ht)
    story.append(sp(12))

    # ── PATIENT INFO STRIP ────────────────────────────────────────────────────
    dob_str = user.dob.strftime("%d %b %Y") if user.dob else "N/A"
    info_data = [
        [Paragraph("👤 Patient", SMALL), Paragraph("📧 Email", SMALL), Paragraph("⚧ Gender", SMALL), Paragraph("🎂 Date of Birth", SMALL)],
        [Paragraph(f"<b>{user.full_name}</b>", BODY_BOLD), Paragraph(user.email, BODY), Paragraph(user.gender or "N/A", BODY), Paragraph(dob_str, BODY)],
    ]
    it = Table(info_data, colWidths=[PAGE_W/4]*4)
    it.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), BLUE_LIGHT),
        ("GRID",        (0,0), (-1,-1), 0.5, BLUE_BORDER),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(it)
    story.append(sp(14))

    # ── REPORT TITLE + SUMMARY ────────────────────────────────────────────────
    title = report_data.get("report_title", "Health Assessment Report")
    summary = report_data.get("summary", "")
    story.append(Paragraph(title, S("RT", fontName="Helvetica-Bold", fontSize=16, textColor=NAVY, leading=22, spaceAfter=6)))
    story.append(hr(BLUE, 1.5))
    story.append(sp(4))
    story.append(Paragraph(summary, BODY))
    story.append(sp(10))

    # ── MAIN CONCERNS ─────────────────────────────────────────────────────────
    concerns = report_data.get("main_concerns", [])
    if concerns:
        story += section("🔍", "Main Health Concerns", NAVY)
        for c in concerns:
            sev = c.get("severity", "Mild")
            sc = severity_color(sev)
            row = [[
                Paragraph(f"<b>{c.get('issue','')}</b>", BODY_BOLD),
                Paragraph(sev, S("sv", fontName="Helvetica-Bold", fontSize=9, textColor=WHITE, alignment=TA_CENTER)),
            ]]
            rt = Table(row, colWidths=[PAGE_W-3.5*cm, 3.0*cm])
            rt.setStyle(TableStyle([
                ("BACKGROUND",  (0,0), (0,0), GRAY_50),
                ("BACKGROUND",  (1,0), (1,0), sc),
                ("TOPPADDING",  (0,0), (-1,-1), 8),
                ("BOTTOMPADDING",(0,0),(-1,-1), 8),
                ("LEFTPADDING", (0,0), (0,0),  10),
                ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
                ("GRID",        (0,0), (-1,-1), 0.5, GRAY_300),
                ("ROUNDEDCORNERS", [4]),
            ]))
            story.append(rt)
            story.append(Paragraph(c.get("description",""), BODY))
            story.append(sp(8))

    # ── POSSIBLE CONDITIONS ───────────────────────────────────────────────────
    conditions = report_data.get("possible_conditions", [])
    if conditions:
        story += section("🧬", "Possible Associated Conditions", HexColor("#1D4ED8"))
        story.append(sp(4))
        cols = [conditions[i::2] for i in range(2)]
        max_r = max(len(cols[0]), len(cols[1]))
        cond_data = []
        for i in range(max_r):
            r = []
            for col in cols:
                r.append(Paragraph(f"◆  {col[i]}" if i < len(col) else "", BODY))
            cond_data.append(r)
        ct = Table(cond_data, colWidths=[PAGE_W/2]*2)
        ct.setStyle(TableStyle([
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[BLUE_LIGHT, WHITE]),
            ("TOPPADDING",(0,0),(-1,-1),7),
            ("BOTTOMPADDING",(0,0),(-1,-1),7),
            ("LEFTPADDING",(0,0),(-1,-1),12),
            ("GRID",(0,0),(-1,-1),0.3,BLUE_BORDER),
        ]))
        story.append(ct)
        story.append(sp(4))

    # ── SUGGESTIONS ───────────────────────────────────────────────────────────
    suggestions = report_data.get("suggestions", [])
    if suggestions:
        story += section("💡", "Recommendations & Suggestions", TEAL)
        for i, s in enumerate(suggestions, 1):
            num_cell = Paragraph(f"<b>{i:02d}</b>", S("n", fontName="Helvetica-Bold", fontSize=12, textColor=WHITE, alignment=TA_CENTER))
            text_cell = [Paragraph(s.get("title",""), BODY_BOLD), Paragraph(s.get("detail",""), BODY)]
            row = [[num_cell, text_cell]]
            t = Table(row, colWidths=[1.2*cm, PAGE_W-1.4*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(0,0), TEAL),
                ("BACKGROUND",(1,0),(1,0), TEAL_LIGHT),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("TOPPADDING",(0,0),(-1,-1),8),
                ("BOTTOMPADDING",(0,0),(-1,-1),8),
                ("LEFTPADDING",(1,0),(1,0),10),
                ("GRID",(0,0),(-1,-1),0.3,HexColor("#99F6E4")),
                ("ROUNDEDCORNERS",[4]),
            ]))
            story.append(t)
            story.append(sp(4))

    # ── ACTIVITIES & YOGA ─────────────────────────────────────────────────────
    activities = report_data.get("activities_and_yoga", [])
    if activities:
        story += section("🧘", "Exercises, Activities & Yoga", PURPLE)
        for act in activities:
            cells = [
                [Paragraph(f"<b>{act.get('name','')}</b>", S("an", fontName="Helvetica-Bold", fontSize=11, textColor=PURPLE))],
                [Paragraph(f"📋 {act.get('instructions','')}", BODY)],
                [[
                    Paragraph(f"⏱ <b>Duration:</b> {act.get('duration','')}", SMALL),
                    Paragraph(f"✅ <b>Benefit:</b> {act.get('benefit','')}", SMALL),
                ]],
            ]
            at = Table(cells, colWidths=[PAGE_W])
            at.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(0,0), PURPLE_LIGHT),
                ("BACKGROUND",(0,1),(0,1), WHITE),
                ("BACKGROUND",(0,2),(0,2), GRAY_50),
                ("LEFTPADDING",(0,0),(-1,-1),12),
                ("TOPPADDING",(0,0),(-1,-1),6),
                ("BOTTOMPADDING",(0,0),(-1,-1),6),
                ("GRID",(0,0),(-1,-1),0.3,HexColor("#DDD6FE")),
                ("ROUNDEDCORNERS",[4]),
            ]))
            story.append(at)
            story.append(sp(6))

    # ── WHAT TO AVOID ─────────────────────────────────────────────────────────
    avoid = report_data.get("what_to_avoid", [])
    if avoid:
        story += section("🚫", "What to Avoid", RED)
        avoid_data = [[
            Paragraph(f"✕  <b>{a.get('item','')}</b>", S("av", fontName="Helvetica-Bold", fontSize=10, textColor=RED)),
            Paragraph(a.get("reason",""), BODY)
        ] for a in avoid]
        avt = Table(avoid_data, colWidths=[5.5*cm, PAGE_W-5.7*cm])
        avt.setStyle(TableStyle([
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[RED_LIGHT, WHITE]),
            ("TOPPADDING",(0,0),(-1,-1),8),
            ("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(-1,-1),10),
            ("GRID",(0,0),(-1,-1),0.3,HexColor("#FECACA")),
        ]))
        story.append(avt)
        story.append(sp(4))

    # ── WHAT TO FOLLOW ────────────────────────────────────────────────────────
    follow = report_data.get("what_to_follow", [])
    if follow:
        story += section("✅", "Healthy Habits to Follow", GREEN)
        follow_data = [[
            Paragraph(f"✓  <b>{f.get('habit','')}</b>", S("fh", fontName="Helvetica-Bold", fontSize=10, textColor=GREEN)),
            Paragraph(f.get("detail",""), BODY)
        ] for f in follow]
        ft = Table(follow_data, colWidths=[5.5*cm, PAGE_W-5.7*cm])
        ft.setStyle(TableStyle([
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[GREEN_LIGHT, WHITE]),
            ("TOPPADDING",(0,0),(-1,-1),8),
            ("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(-1,-1),10),
            ("GRID",(0,0),(-1,-1),0.3,HexColor("#86EFAC")),
        ]))
        story.append(ft)
        story.append(sp(4))

    # ── DIET PLAN ─────────────────────────────────────────────────────────────
    diet = report_data.get("diet_plan", {})
    if diet:
        story += section("🥗", "Personalized Diet Plan", ORANGE)
        if diet.get("overview"):
            story.append(Paragraph(diet["overview"], BODY))
            story.append(sp(8))

        meal_times = [
            ("🌅 Morning", "morning"),
            ("🍎 Mid-Morning", "midmorning"),
            ("☀️ Lunch", "lunch"),
            ("🌤 Evening", "evening"),
            ("🌙 Dinner", "dinner"),
        ]
        meal_rows = []
        for label, key in meal_times:
            items = diet.get(key, [])
            if items:
                meal_rows.append([
                    Paragraph(f"<b>{label}</b>", S("ml", fontName="Helvetica-Bold", fontSize=10, textColor=ORANGE)),
                    Paragraph("  •  ".join(items), BODY)
                ])
        if meal_rows:
            mt = Table(meal_rows, colWidths=[3.5*cm, PAGE_W-3.7*cm])
            mt.setStyle(TableStyle([
                ("ROWBACKGROUNDS",(0,0),(-1,-1),[ORANGE_LIGHT, WHITE]),
                ("TOPPADDING",(0,0),(-1,-1),8),
                ("BOTTOMPADDING",(0,0),(-1,-1),8),
                ("LEFTPADDING",(0,0),(-1,-1),10),
                ("GRID",(0,0),(-1,-1),0.3,HexColor("#FED7AA")),
            ]))
            story.append(mt)
            story.append(sp(10))

        inc = diet.get("foods_to_include", [])
        exc = diet.get("foods_to_avoid", [])
        if inc or exc:
            max_r = max(len(inc), len(exc))
            food_data = [["✅  Include", "🚫  Avoid"]] + [
                [Paragraph(f"+ {inc[i]}", S("fi", fontSize=10, textColor=GREEN)) if i < len(inc) else Paragraph("", BODY),
                 Paragraph(f"- {exc[i]}", S("fe", fontSize=10, textColor=RED)) if i < len(exc) else Paragraph("", BODY)]
                for i in range(max_r)
            ]
            food_t = Table(food_data, colWidths=[PAGE_W/2, PAGE_W/2])
            food_t.setStyle(TableStyle([
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,0),10),
                ("BACKGROUND",(0,0),(0,0), GREEN_LIGHT),
                ("BACKGROUND",(1,0),(1,0), RED_LIGHT),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, GRAY_50]),
                ("TOPPADDING",(0,0),(-1,-1),7),
                ("BOTTOMPADDING",(0,0),(-1,-1),7),
                ("LEFTPADDING",(0,0),(-1,-1),10),
                ("GRID",(0,0),(-1,-1),0.5,GRAY_300),
            ]))
            story.append(food_t)
            story.append(sp(4))

    # ── WHEN TO SEE A DOCTOR ─────────────────────────────────────────────────
    wtsd = report_data.get("when_to_see_doctor", [])
    if wtsd:
        story += section("🏥", "When to See a Doctor", HexColor("#B91C1C"))
        story.append(sp(4))
        warn_data = [[Paragraph(f"⚠  {w}", S("wr", fontSize=10, textColor=HexColor("#7F1D1D")))] for w in wtsd]
        wt = Table(warn_data, colWidths=[PAGE_W])
        wt.setStyle(TableStyle([
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[RED_LIGHT, WHITE]),
            ("TOPPADDING",(0,0),(-1,-1),7),
            ("BOTTOMPADDING",(0,0),(-1,-1),7),
            ("LEFTPADDING",(0,0),(-1,-1),12),
            ("GRID",(0,0),(-1,-1),0.3,HexColor("#FECACA")),
        ]))
        story.append(wt)
        story.append(sp(10))

    # ── DISCLAIMER FOOTER ─────────────────────────────────────────────────────
    disc_text = report_data.get("disclaimer","This report is for informational purposes only. Consult a qualified healthcare professional for medical advice.")
    disc_data = [[Paragraph("⚠  Medical Disclaimer", S("dh", fontName="Helvetica-Bold", fontSize=9, textColor=GRAY_500))],
                 [Paragraph(disc_text, DISC_S)]]
    dt = Table(disc_data, colWidths=[PAGE_W])
    dt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), GRAY_100),
        ("TOPPADDING",(0,0),(-1,-1),8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),12),
        ("RIGHTPADDING",(0,0),(-1,-1),12),
        ("GRID",(0,0),(-1,-1),0.5,GRAY_300),
        ("ROUNDEDCORNERS",[6]),
    ]))
    story.append(sp(16))
    story.append(dt)

    # ── GENERATED BY LINE ─────────────────────────────────────────────────────
    story.append(sp(8))
    story.append(Paragraph(
        f"Generated by CareBot AI Health Assistant  •  {now.strftime('%d %B %Y, %H:%M')}  •  For informational purposes only",
        DISC_S
    ))

    doc.build(story)
    return filename


def generate_bmi_report(user, bmi_records) -> str:
    filename = f"bmi_report_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    doc = SimpleDocTemplate(filepath, pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.8*cm, bottomMargin=2*cm)
    story = []
    now = datetime.now()

    hd = [[Paragraph("CareBot — BMI Report", H1)]]
    ht = Table(hd, colWidths=[PAGE_W])
    ht.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),BLUE),("TOPPADDING",(0,0),(-1,-1),18),("BOTTOMPADDING",(0,0),(-1,-1),18),("ROUNDEDCORNERS",[10])]))
    story.append(ht)
    story.append(sp(14))
    story.append(Paragraph(f"Patient: <b>{user.full_name}</b>   |   {now.strftime('%d %B %Y')}", BODY))
    story.append(sp(10))
    story.append(SectionChip("  📊  BMI History", BLUE, WHITE))
    story.append(sp(8))

    table_data = [["Date","Height (cm)","Weight (kg)","BMI","Category"]]
    for r in bmi_records:
        table_data.append([r.created_at.strftime("%d %b %Y") if r.created_at else "N/A", str(r.height), str(r.weight), f"{r.bmi:.1f}", r.category])
    t = Table(table_data, colWidths=[4*cm,3.5*cm,3.5*cm,2.5*cm,PAGE_W-13.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),BLUE),("TEXTCOLOR",(0,0),(-1,0),WHITE),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,BLUE_LIGHT]),
        ("GRID",(0,0),(-1,-1),0.5,GRAY_300),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(t)
    doc.build(story)
    return filename
