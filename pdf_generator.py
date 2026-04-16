# pdf_generator.py
# ─────────────────────────────────────────────────────────────────────────────
# Generates a clean, ATS-friendly PDF resume from the tailored resume data.
#
# Why ReportLab instead of HTML-to-PDF?
#   ReportLab produces a pure programmatic PDF — no headless browser, no
#   Puppeteer, no Playwright. It works reliably on Streamlit Cloud without
#   additional system dependencies and keeps the deployment lightweight.
#
# Design decisions:
#   - Single-column layout: maximises text density for ATS parsers, which
#     often fail to correctly read multi-column PDFs.
#   - Minimal styling (accent colour + ruled sections): looks professional
#     without relying on fonts that may not be available on the server.
#   - Returns raw bytes (io.BytesIO) so Streamlit's st.download_button can
#     serve the PDF directly without writing a temp file to disk.
# ─────────────────────────────────────────────────────────────────────────────

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
# Kept minimal — only the accent blue is bold; everything else is near-neutral.
# This makes the PDF both readable on screen and parse-friendly for ATS tools.
ACCENT   = colors.HexColor("#1a56db")   # section headers and candidate name
TEXT     = colors.HexColor("#1a1a2e")   # primary body text (near-black)
MUTED    = colors.HexColor("#555770")   # secondary labels (tech stack, dates)
RULE     = colors.HexColor("#d0d5dd")   # horizontal dividers between sections
BG_SKILL = colors.HexColor("#eff4ff")   # pale blue — reserved for skill chips


# ── Style helpers ────────────────────────────────────────────────────────────
def _style(name, **kw):
    """
    Creates a ReportLab ParagraphStyle with sensible defaults.
    Any keyword arg overrides the base — avoids repeating font/size/color
    across every style definition below.
    """
    base = dict(fontName="Helvetica", fontSize=10, textColor=TEXT,
                leading=14, spaceAfter=0, spaceBefore=0)
    base.update(kw)
    return ParagraphStyle(name, **base)

# Name at the top — large, bold, accent colour to stand out visually.
NAME_S    = _style("name",    fontName="Helvetica-Bold", fontSize=22,
                   textColor=ACCENT, leading=26, spaceAfter=2)

# Small single line of contact details — email, phone, location, links.
CONTACT_S = _style("contact", fontSize=8.5, textColor=MUTED, leading=12)

# Section titles (SUMMARY, SKILLS, etc.) — small caps feel via letter spacing.
SECTION_S = _style("section", fontName="Helvetica-Bold", fontSize=9,
                   textColor=ACCENT, leading=11, spaceBefore=14, spaceAfter=4,
                   letterSpacing=1)

# General body text — summary paragraph, education line.
BODY_S    = _style("body",    fontSize=9.5, leading=14)

# Bullet point indented text — left indent creates visual grouping under projects.
BULLET_S  = _style("bullet",  fontSize=9.5, leading=14, leftIndent=10,
                   bulletIndent=0)

# Project name — slightly larger and bold to create visual hierarchy.
PROJ_S    = _style("proj",    fontName="Helvetica-Bold", fontSize=10,
                   leading=13, spaceBefore=8)

# Tech stack line under project name — muted so it doesn't compete with bullets.
TECH_S    = _style("tech",    fontSize=8.5, textColor=MUTED, leading=11,
                   spaceAfter=3)

# Education sub-line (degree, CGPA, year) — same muted treatment.
SMALL_S   = _style("small",   fontSize=8.5, textColor=MUTED, leading=11)


def _rule():
    """Thin horizontal line used to separate resume sections visually."""
    return HRFlowable(width="100%", thickness=0.5, color=RULE,
                      spaceAfter=6, spaceBefore=2)


def _section(title):
    """Returns a [section heading, divider rule] pair for each resume section."""
    return [Paragraph(title.upper(), SECTION_S), _rule()]


def _bullet(text):
    """
    Renders a single bullet point using the Unicode bullet character (•).
    Using a character rather than a ListFlowable keeps the layout simpler
    and more predictable across ReportLab versions.
    """
    return Paragraph(f"\u2022\u2002{text}", BULLET_S)


def _skill_chips(skills):
    """
    Renders the skills list as a single wrapped paragraph with · separators.
    Intentionally avoids a table/grid layout so ATS parsers read the skills
    as a continuous text string rather than isolated table cells.
    """
    joined = "  \u00b7  ".join(skills)
    return Paragraph(joined, _style("chips", fontSize=9.5, textColor=TEXT,
                                    leading=15))


# ── Main builder ─────────────────────────────────────────────────────────────
def build_pdf(resume: dict, tailored: dict) -> bytes:
    """
    Assembles and returns the full tailored resume as a PDF byte string.

    Parameters
    ----------
    resume   : original resume dict from resume_data.py — used for static
               fields (name, contact, education, certifications) that the
               LLM does not rewrite.
    tailored : output of tailor_resume() — contains the LLM-rewritten fields:
               tailored_summary, skills_to_highlight, projects, cover_note.

    The PDF is written to an in-memory BytesIO buffer and returned as bytes
    so Streamlit's st.download_button can serve it without touching disk.
    """
    buf = io.BytesIO()

    # A4 page with 18mm margins — standard resume dimensions that fit
    # comfortably within typical ATS upload size limits.
    margin = 18 * mm
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=14 * mm, bottomMargin=14 * mm,
    )

    story = []  # ReportLab renders this list of Flowables top-to-bottom

    # ── Header ───────────────────────────────────────────────────────────────
    # Filter out placeholder contact values (any field containing "your-")
    # so users who haven't filled them in don't get ugly placeholder text.
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
    # Uses the LLM-tailored summary (not the original from resume_data.py)
    # so the opening statement already speaks directly to this JD's requirements.
    story += _section("Summary")
    story.append(Paragraph(tailored["tailored_summary"], BODY_S))
    story.append(Spacer(1, 4))

    # ── Skills ────────────────────────────────────────────────────────────────
    # Uses the LLM-reordered skills list with JD-relevant skills pushed to front.
    story += _section("Skills")
    story.append(_skill_chips(tailored["skills_to_highlight"]))
    story.append(Spacer(1, 4))

    # ── Projects ──────────────────────────────────────────────────────────────
    # Projects are rendered in the LLM-determined order (most relevant first).
    # Bullet points are the LLM-rewritten versions that mirror JD language.
    # The relevance_note is intentionally excluded — it's an internal LLM note,
    # not something that should appear on the actual resume.
    story += _section("Projects")
    for proj in tailored["projects"]:
        tech_str = "  ·  ".join(proj["tech"])
        story.append(Paragraph(proj["name"], PROJ_S))
        story.append(Paragraph(tech_str, TECH_S))
        for b in proj["bullets"]:
            story.append(_bullet(b))
        story.append(Spacer(1, 6))

    # ── Education ─────────────────────────────────────────────────────────────
    # Taken verbatim from resume_data.py — education is factual and not tailored.
    edu = resume.get("education", {})
    if edu:
        story += _section("Education")
        story.append(Paragraph(f"<b>{edu.get('college', '')}</b>", BODY_S))
        story.append(Paragraph(
            f"{edu.get('degree', '')}  ·  CGPA {edu.get('cgpa', '')}  ·  {edu.get('year', '')}",
            SMALL_S))
        story.append(Spacer(1, 4))

    # ── Certifications ────────────────────────────────────────────────────────
    # Rendered as bullet points — relevant for roles that value credentials.
    certs = resume.get("certifications", [])
    if certs:
        story += _section("Certifications")
        for cert in certs:
            story.append(_bullet(cert))

    doc.build(story)
    return buf.getvalue()
