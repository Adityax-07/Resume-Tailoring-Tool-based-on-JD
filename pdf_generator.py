import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER


# ── Colour palette ──────────────────────────────────────────────────────────
ACCENT   = colors.HexColor("#1a56db")   # blue
TEXT     = colors.HexColor("#1a1a2e")   # near-black
MUTED    = colors.HexColor("#555770")   # grey for labels
RULE     = colors.HexColor("#d0d5dd")   # light divider
BG_SKILL = colors.HexColor("#eff4ff")   # pale blue chip background


# ── Style helpers ────────────────────────────────────────────────────────────
def _style(name, **kw):
    base = dict(fontName="Helvetica", fontSize=10, textColor=TEXT,
                leading=14, spaceAfter=0, spaceBefore=0)
    base.update(kw)
    return ParagraphStyle(name, **base)

NAME_S    = _style("name",    fontName="Helvetica-Bold", fontSize=22,
                   textColor=ACCENT, leading=26, spaceAfter=2)
CONTACT_S = _style("contact", fontSize=8.5, textColor=MUTED, leading=12)
SECTION_S = _style("section", fontName="Helvetica-Bold", fontSize=9,
                   textColor=ACCENT, leading=11, spaceBefore=14, spaceAfter=4,
                   letterSpacing=1)
BODY_S    = _style("body",    fontSize=9.5, leading=14)
BULLET_S  = _style("bullet",  fontSize=9.5, leading=14, leftIndent=10,
                   bulletIndent=0)
PROJ_S    = _style("proj",    fontName="Helvetica-Bold", fontSize=10,
                   leading=13, spaceBefore=8)
TECH_S    = _style("tech",    fontSize=8.5, textColor=MUTED, leading=11,
                   spaceAfter=3)
SMALL_S   = _style("small",   fontSize=8.5, textColor=MUTED, leading=11)


def _rule():
    return HRFlowable(width="100%", thickness=0.5, color=RULE,
                      spaceAfter=6, spaceBefore=2)


def _section(title):
    return [Paragraph(title.upper(), SECTION_S), _rule()]


def _bullet(text):
    return Paragraph(f"\u2022\u2002{text}", BULLET_S)


def _skill_chips(skills):
    """Render skills as a wrapping row of lightly-styled inline text."""
    joined = "  \u00b7  ".join(skills)
    return Paragraph(joined, _style("chips", fontSize=9.5, textColor=TEXT,
                                    leading=15))


# ── Main builder ─────────────────────────────────────────────────────────────
def build_pdf(resume: dict, tailored: dict) -> bytes:
    """
    Returns PDF bytes for the tailored resume.

    Parameters
    ----------
    resume   : original resume dict (from resume_data.py)
    tailored : output of tailor_resume() — contains tailored_summary,
               skills_to_highlight, projects, cover_note, etc.
    """
    buf = io.BytesIO()
    margin = 18 * mm

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=14 * mm, bottomMargin=14 * mm,
    )

    story = []

    # ── Header ───────────────────────────────────────────────────────────────
    c = resume["contact"]
    contact_parts = [c.get("email", ""), c.get("phone", ""),
                     c.get("location", ""), c.get("linkedin", ""),
                     c.get("github", "")]
    contact_line = "  |  ".join(p for p in contact_parts if p and "your-" not in p)

    story.append(Paragraph(resume["name"], NAME_S))
    story.append(Paragraph(contact_line, CONTACT_S))
    story.append(Spacer(1, 6))
    story.append(_rule())

    # ── Summary ───────────────────────────────────────────────────────────────
    story += _section("Summary")
    story.append(Paragraph(tailored["tailored_summary"], BODY_S))
    story.append(Spacer(1, 4))

    # ── Skills ────────────────────────────────────────────────────────────────
    story += _section("Skills")
    story.append(_skill_chips(tailored["skills_to_highlight"]))
    story.append(Spacer(1, 4))

    # ── Projects ──────────────────────────────────────────────────────────────
    story += _section("Projects")

    for proj in tailored["projects"]:
        tech_str = "  ·  ".join(proj["tech"])
        story.append(Paragraph(proj["name"], PROJ_S))
        story.append(Paragraph(tech_str, TECH_S))
        for b in proj["bullets"]:
            story.append(_bullet(b))
        story.append(Spacer(1, 6))

    # ── Education ─────────────────────────────────────────────────────────────
    edu = resume.get("education", {})
    if edu:
        story += _section("Education")
        story.append(Paragraph(
            f"<b>{edu.get('college', '')}</b>", BODY_S))
        story.append(Paragraph(
            f"{edu.get('degree', '')}  ·  CGPA {edu.get('cgpa', '')}  ·  {edu.get('year', '')}",
            SMALL_S))
        story.append(Spacer(1, 4))

    # ── Certifications ────────────────────────────────────────────────────────
    certs = resume.get("certifications", [])
    if certs:
        story += _section("Certifications")
        for cert in certs:
            story.append(_bullet(cert))

    doc.build(story)
    return buf.getvalue()
