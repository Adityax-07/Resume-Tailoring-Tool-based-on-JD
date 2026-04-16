# app.py
# ─────────────────────────────────────────────────────────────────────────────
# Main Streamlit application — UI, sidebar auth, and pipeline orchestration.
#
# Responsibilities:
#   1. Bootstrap the Groq API key from Streamlit secrets into os.environ
#      so tailor.py (which reads os.environ directly) works on Cloud.
#   2. Render the full UI: hero section, JD input, pipeline progress bar,
#      and all result sections (ATS analysis, tailored resume, cover note).
#   3. Manage Supabase auth state in the sidebar (sign in / sign up / sign out).
#   4. Save each pipeline run to the user's history and increment the
#      global usage counter after a successful run.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import os
import json
import math
from resume_data import resume
from pdf_generator import build_pdf
from supabase_client import get_supabase

# ── Bootstrap Groq API key into os.environ ────────────────────────────────────
# tailor.py reads os.environ["GROQ_API_KEY"] at import time via the Groq client.
# On Streamlit Cloud, env vars aren't set automatically — secrets live in
# st.secrets. We push the key into os.environ here (before tailor.py is
# imported inside the pipeline block) so both local and Cloud deployments work
# with the same code path.
if "GROQ_API_KEY" not in os.environ:
    try:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    except Exception:
        pass  # will fail later with a clear error when the pipeline runs

st.set_page_config(page_title="Resume Tailor AI", layout="wide", page_icon="🎯")

# ── Session state initialisation ──────────────────────────────────────────────
# Streamlit reruns the entire script on every user interaction. Session state
# persists values across reruns within a single browser session.
# sb_user    : dict with {id, email} of the signed-in user, or None
# sb_access  : Supabase JWT access token (needed to restore auth on reruns)
# sb_refresh : Supabase refresh token (used to get a new access token if expired)
for _k, _v in [("sb_user", None), ("sb_access", None), ("sb_refresh", None)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Supabase client (per-session instance) ────────────────────────────────────
sb = get_supabase()

# Restore auth session on every rerun so Supabase Row Level Security (RLS)
# tokens are valid. Without this, the client would be unauthenticated after
# the first rerun and all history queries would be rejected by RLS policies.
if sb and st.session_state["sb_access"]:
    try:
        sb.auth.set_session(
            st.session_state["sb_access"],
            st.session_state["sb_refresh"],
        )
    except Exception:
        # Session expired or invalid — clear auth state and force re-login.
        st.session_state.update({"sb_user": None, "sb_access": None, "sb_refresh": None})


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ── Base ── */
*, *::before, *::after { font-family: 'Inter', sans-serif !important; box-sizing: border-box; }
#MainMenu, footer, header { visibility: hidden; }

[data-testid="stAppViewContainer"] {
    background: #07090f;
    background-image:
        radial-gradient(ellipse 80% 60% at 10% 5%,  rgba(99,102,241,.10) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 90% 90%, rgba(16,185,129,.07) 0%, transparent 55%),
        radial-gradient(ellipse 50% 40% at 55% 0%,  rgba(59,130,246,.07) 0%, transparent 50%);
}
[data-testid="stMain"] { padding-top: 0 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0b0d16 !important;
    border-right: 1px solid rgba(255,255,255,.06) !important;
}
[data-testid="stSidebar"] input {
    background: rgba(255,255,255,.05) !important;
    border: 1px solid rgba(255,255,255,.09) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-size: 13px !important;
}
[data-testid="stSidebar"] input:focus {
    border-color: rgba(99,102,241,.5) !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,.12) !important;
    outline: none !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    border: none !important;
    border-radius: 8px !important;
    color: #fff !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 9px 16px !important;
    margin-top: 4px !important;
    width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
    box-shadow: 0 4px 16px rgba(99,102,241,.4) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: rgba(255,255,255,.03) !important;
    border: 1px solid rgba(255,255,255,.07) !important;
    border-radius: 10px !important;
    margin-bottom: 6px !important;
}
[data-testid="stSidebar"] label { color: #94a3b8 !important; font-size: 12px !important; }
.sb-signout > button {
    background: rgba(244,63,94,.12) !important;
    border: 1px solid rgba(244,63,94,.25) !important;
    color: #fb7185 !important;
}
.sb-signout > button:hover {
    background: rgba(244,63,94,.2) !important;
    box-shadow: none !important;
}

/* ── Animations ── */
@keyframes fadeUp   { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }
@keyframes popIn    { from{opacity:0;transform:scale(.92)}        to{opacity:1;transform:scale(1)}      }
@keyframes shimmer  { 0%{background-position:200% center} 100%{background-position:-200% center}      }
@keyframes glow     { 0%,100%{box-shadow:0 0 18px rgba(99,102,241,.25)} 50%{box-shadow:0 0 32px rgba(99,102,241,.5)} }
@keyframes spin     { to{transform:rotate(360deg)} }
@keyframes dash     { from{stroke-dashoffset:var(--full)} to{stroke-dashoffset:var(--offset)} }

.fade-up  { animation: fadeUp .55s ease both; }
.pop-in   { animation: popIn .4s cubic-bezier(.34,1.4,.64,1) both; }

/* ── Gradient text ── */
.grad-text {
    background: linear-gradient(135deg, #818cf8 0%, #60a5fa 40%, #34d399 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.grad-text-warm {
    background: linear-gradient(135deg, #f472b6 0%, #a78bfa 50%, #60a5fa 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ── Glass card ── */
.glass {
    background: rgba(255,255,255,.035);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 20px;
    padding: 24px 28px;
    margin-bottom: 16px;
    transition: border-color .25s;
}
.glass:hover { border-color: rgba(255,255,255,.15); }

/* Accent-bordered card */
.glass-indigo { border-left: 3px solid #6366f1; border-radius: 0 20px 20px 0; }
.glass-emerald { border-left: 3px solid #10b981; border-radius: 0 20px 20px 0; }
.glass-amber  { border-left: 3px solid #f59e0b; border-radius: 0 20px 20px 0; }
.glass-rose   { border-left: 3px solid #f43f5e; border-radius: 0 20px 20px 0; }

/* ── Hero ── */
.hero-title {
    font-size: clamp(36px, 5vw, 58px);
    font-weight: 900;
    letter-spacing: -1.5px;
    line-height: 1.05;
    margin: 0 0 10px 0;
}
.hero-sub {
    font-size: 17px;
    color: #6b7280;
    font-weight: 400;
    margin: 0 0 40px 0;
    line-height: 1.6;
}

/* ── Step cards ── */
.steps-row { display: flex; gap: 16px; margin-bottom: 40px; }
.step-card {
    flex: 1;
    background: rgba(255,255,255,.03);
    border: 1px solid rgba(255,255,255,.07);
    border-radius: 16px;
    padding: 18px 20px;
}
.step-num {
    width: 32px; height: 32px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700; margin-bottom: 10px;
}
.step-title { font-size: 14px; font-weight: 700; color: #e2e8f0; margin-bottom: 4px; }
.step-desc  { font-size: 12px; color: #6b7280; line-height: 1.5; }

/* ── Textarea ── */
textarea {
    background: rgba(255,255,255,.04) !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(255,255,255,.1) !important;
    border-radius: 14px !important;
    font-size: 14px !important;
    resize: vertical !important;
    transition: border-color .2s, box-shadow .2s !important;
}
textarea:focus {
    border-color: rgba(99,102,241,.6) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,.15) !important;
}
[data-testid="stTextArea"] label { display: none; }

/* ── Primary button ── */
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    border: none !important;
    border-radius: 12px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    letter-spacing: .02em !important;
    padding: 12px 32px !important;
    color: #fff !important;
    box-shadow: 0 4px 24px rgba(99,102,241,.35) !important;
    transition: all .2s !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    box-shadow: 0 6px 32px rgba(99,102,241,.55) !important;
    transform: translateY(-1px) !important;
}

/* ── Step progress bar ── */
.pipeline-bar {
    display: flex; gap: 0; align-items: center;
    background: rgba(255,255,255,.03);
    border: 1px solid rgba(255,255,255,.07);
    border-radius: 14px;
    padding: 14px 20px;
    margin: 16px 0;
}
.pip-step {
    display: flex; align-items: center; gap: 10px; flex: 1;
}
.pip-dot {
    width: 28px; height: 28px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; flex-shrink: 0;
}
.pip-dot.done    { background: #10b981; color: #fff; }
.pip-dot.active  { background: linear-gradient(135deg,#6366f1,#4f46e5); color: #fff;
                   animation: glow 1.5s ease infinite; }
.pip-dot.waiting { background: rgba(255,255,255,.07); color: #4b5563; }
.pip-label { font-size: 13px; font-weight: 500; }
.pip-label.done   { color: #10b981; }
.pip-label.active { color: #a5b4fc; }
.pip-label.wait   { color: #374151; }
.pip-arrow { color: #374151; margin: 0 8px; font-size: 14px; }

/* ── Section header ── */
.sec-hdr {
    display: flex; align-items: center; gap: 12px;
    margin: 36px 0 20px 0;
}
.sec-hdr-line {
    flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(99,102,241,.4), transparent);
}
.sec-hdr-text {
    font-size: 11px; font-weight: 800; letter-spacing: .15em;
    text-transform: uppercase; color: #6366f1;
}

/* ── Meta chips (role/domain/company) ── */
.meta-grid { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.meta-chip {
    background: rgba(255,255,255,.04);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 10px;
    padding: 10px 16px;
}
.meta-chip-key   { font-size: 10px; color: #6b7280; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 3px; }
.meta-chip-value { font-size: 14px; font-weight: 700; color: #e2e8f0; }

/* ── Emphasis box ── */
.emphasis-box {
    background: linear-gradient(135deg, rgba(99,102,241,.08), rgba(59,130,246,.05));
    border: 1px solid rgba(99,102,241,.2);
    border-radius: 12px;
    padding: 14px 18px;
    font-size: 14px;
    color: #c7d2fe;
    line-height: 1.6;
    margin-bottom: 18px;
}

/* ── Keyword pills ── */
.pill-row { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 8px; }
.pill {
    padding: 4px 12px; border-radius: 999px;
    font-size: 12px; font-weight: 600;
    transition: transform .15s;
}
.pill:hover { transform: translateY(-1px); }
.pill-green  { background: rgba(16,185,129,.12);  color: #34d399; border: 1px solid rgba(16,185,129,.25); }
.pill-red    { background: rgba(244,63,94,.10);   color: #fb7185; border: 1px solid rgba(244,63,94,.25); }
.pill-indigo { background: rgba(99,102,241,.12);  color: #a5b4fc; border: 1px solid rgba(99,102,241,.25); }
.pill-violet { background: rgba(139,92,246,.12);  color: #c4b5fd; border: 1px solid rgba(139,92,246,.25); }
.pill-slate  { background: rgba(255,255,255,.05); color: #94a3b8; border: 1px solid rgba(255,255,255,.1); }
.pill-cyan   { background: rgba(6,182,212,.10);   color: #67e8f9; border: 1px solid rgba(6,182,212,.2); }

/* ── Score breakdown bars ── */
.prog-wrap { margin-bottom: 16px; }
.prog-label { display: flex; justify-content: space-between; font-size: 12px; color: #6b7280; margin-bottom: 6px; font-weight: 500; }
.prog-track { background: rgba(255,255,255,.06); border-radius: 999px; height: 6px; overflow: hidden; }
.prog-fill  { height: 6px; border-radius: 999px; transition: width .8s cubic-bezier(.4,0,.2,1); }

/* ── Project cards ── */
.proj-card {
    background: rgba(255,255,255,.03);
    border: 1px solid rgba(255,255,255,.07);
    border-radius: 16px;
    padding: 20px 22px;
    margin-bottom: 14px;
    position: relative;
    overflow: hidden;
    transition: border-color .2s, transform .2s;
}
.proj-card:hover { border-color: rgba(99,102,241,.3); transform: translateY(-2px); }
.proj-card::before {
    content: '';
    position: absolute; top: 0; left: 0; bottom: 0; width: 3px;
    background: linear-gradient(180deg, #6366f1, #4f46e5);
    border-radius: 3px 0 0 3px;
}
.proj-card.rank-2::before { background: linear-gradient(180deg, #8b5cf6, #7c3aed); }
.proj-card.rank-3::before { background: linear-gradient(180deg, #06b6d4, #0891b2); }
.proj-card.rank-4::before { background: linear-gradient(180deg, #475569, #334155); }
.proj-title { font-size: 16px; font-weight: 800; color: #f1f5f9; margin-bottom: 6px; }
.top-badge {
    display: inline-flex; align-items: center; gap: 4px;
    background: linear-gradient(135deg, rgba(99,102,241,.2), rgba(79,70,229,.15));
    border: 1px solid rgba(99,102,241,.4);
    color: #a5b4fc; font-size: 10px; font-weight: 700; letter-spacing: .05em;
    padding: 2px 10px; border-radius: 999px; margin-left: 10px; vertical-align: middle;
    text-transform: uppercase;
}
.bullet-item {
    color: #94a3b8; font-size: 13.5px; line-height: 1.7;
    margin: 6px 0 6px 8px; padding-left: 12px;
    border-left: 2px solid rgba(99,102,241,.2);
}
.proj-why {
    font-size: 12px; color: #4b5563; margin-top: 12px;
    padding-top: 10px; border-top: 1px solid rgba(255,255,255,.05);
    font-style: italic;
}

/* ── Verdict badge ── */
.verdict-badge {
    display: inline-block; padding: 6px 16px;
    border-radius: 999px; font-size: 13px; font-weight: 700;
    margin-top: 12px; letter-spacing: .02em;
}

/* ── Cover note ── */
.cover-wrap {
    background: linear-gradient(135deg, rgba(16,185,129,.07), rgba(6,182,212,.05));
    border: 1px solid rgba(16,185,129,.2);
    border-radius: 16px;
    padding: 24px 28px;
    font-size: 15px; line-height: 1.8;
    color: #a7f3d0;
    position: relative;
    overflow: hidden;
}
.cover-wrap::after {
    content: '"';
    position: absolute; top: -10px; right: 20px;
    font-size: 120px; color: rgba(16,185,129,.08);
    font-family: Georgia, serif; line-height: 1;
}

/* ── Download buttons ── */
[data-testid="stDownloadButton"] > button {
    background: rgba(255,255,255,.04) !important;
    border: 1px solid rgba(255,255,255,.1) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    transition: all .2s !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: rgba(99,102,241,.15) !important;
    border-color: rgba(99,102,241,.4) !important;
    transform: translateY(-1px) !important;
}

/* ── Divider ── */
.fancy-hr {
    height: 1px; margin: 36px 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.08), transparent);
    border: none;
}

/* ── Summary card ── */
.summary-text {
    font-size: 15px; line-height: 1.8; color: #cbd5e1;
    border-left: 3px solid rgba(99,102,241,.5);
    padding-left: 16px; margin: 0;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
# Small pure functions that generate HTML snippets. Kept separate from the
# main render flow so each visual element can be reused without duplication.
# ═══════════════════════════════════════════════════════════════════════════════

def pills(items, cls):
    """Renders a list of strings as a row of styled pill badges."""
    inner = "".join(f'<span class="pill {cls}">{i}</span>' for i in items)
    return f'<div class="pill-row">{inner}</div>'

def progress_bar(label, value, max_val, gradient):
    """
    Renders a labelled progress bar for the ATS score breakdown.
    Converts raw scores (e.g. 32/40) to a percentage width for the CSS fill.
    """
    pct = int(value / max_val * 100)
    return f"""
    <div class="prog-wrap">
      <div class="prog-label"><span>{label}</span><span>{value} / {max_val}</span></div>
      <div class="prog-track">
        <div class="prog-fill" style="width:{pct}%;background:{gradient};"></div>
      </div>
    </div>"""

def score_colors(score):
    """
    Returns a (primary, light, background, glow) colour tuple based on score.
    Green ≥75, amber ≥50, red below — mirrors how recruiters read ATS scores.
    Used by both the SVG gauge and the verdict badge to keep colours consistent.
    """
    if score >= 75:
        return "#10b981", "#34d399", "#0d2e22", "rgba(16,185,129,.35)"
    if score >= 50:
        return "#f59e0b", "#fbbf24", "#2d1f0a", "rgba(245,158,11,.35)"
    return "#ef4444", "#f87171", "#2d0b0b", "rgba(239,68,68,.35)"

def svg_gauge(score):
    """
    Renders an animated SVG circular gauge for the ATS score.
    Uses stroke-dasharray to draw the filled arc proportional to the score —
    a pure SVG approach that works without any JS charting library.
    The glow drop-shadow colour is tied to score_colors() for visual consistency.
    """
    c1, c2, bg, glow = score_colors(score)
    R = 54
    circ = 2 * math.pi * R
    filled = circ * score / 100
    gap    = circ - filled
    return f"""
    <div style="display:flex;justify-content:center;padding:8px 0;filter:drop-shadow(0 0 20px {glow});">
      <svg viewBox="0 0 120 120" width="170" height="170">
        <defs>
          <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="{c1}"/>
            <stop offset="100%" stop-color="{c2}"/>
          </linearGradient>
        </defs>
        <circle cx="60" cy="60" r="{R}" fill="none"
          stroke="rgba(255,255,255,.06)" stroke-width="10"/>
        <circle cx="60" cy="60" r="{R}" fill="none"
          stroke="url(#g1)" stroke-width="10"
          stroke-dasharray="{filled:.1f} {gap:.1f}"
          stroke-linecap="round"
          transform="rotate(-90 60 60)"/>
        <text x="60" y="53" text-anchor="middle"
          font-family="Inter,sans-serif" font-size="26" font-weight="900"
          fill="{c1}">{score}</text>
        <text x="60" y="70" text-anchor="middle"
          font-family="Inter,sans-serif" font-size="10" font-weight="500"
          fill="#6b7280">ATS SCORE</text>
      </svg>
    </div>"""

def pipeline_status(step):
    """
    Renders the 3-step pipeline progress bar shown during processing.
    step 1 = Analyze JD running, step 2 = Tailor Resume running,
    step 3 = ATS Score running, step 4 = all done.
    Each dot is styled done/active/waiting based on the current step,
    giving the user live feedback as each LLM call completes.
    """
    labels = ["Analyze JD", "Tailor Resume", "ATS Score"]
    parts = []
    for i, lbl in enumerate(labels, 1):
        if i < step:
            cls = "done"; sym = "✓"
        elif i == step:
            cls = "active"; sym = str(i)
        else:
            cls = "waiting"; sym = str(i)
        lbl_cls = "done" if i < step else ("active" if i == step else "wait")
        parts.append(f"""
          <div class="pip-step">
            <div class="pip-dot {cls}">{sym}</div>
            <span class="pip-label {lbl_cls}">{lbl}</span>
          </div>""")
        if i < 3:
            parts.append('<span class="pip-arrow">›</span>')
    return f'<div class="pipeline-bar">{"".join(parts)}</div>'

def section_header(text):
    """Styled section divider with gradient lines flanking the section title."""
    return f"""
    <div class="sec-hdr">
      <div class="sec-hdr-line"></div>
      <div class="sec-hdr-text">{text}</div>
      <div class="sec-hdr-line" style="background:linear-gradient(90deg,transparent,rgba(99,102,241,.4));"></div>
    </div>"""


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — AUTH + HISTORY + COUNTER
# ─────────────────────────────────────────────────────────────────────────────
# The sidebar handles all Supabase-powered features:
#   - Sign in / Sign up (email + password via Supabase Auth)
#   - Recent history (last 5 pipeline runs for the logged-in user)
#   - Global usage counter (total resumes tailored across all users)
#
# The three states are mutually exclusive:
#   1. sb is None        → Supabase secrets not configured, show a notice
#   2. sb_user is None   → not signed in, show Sign In / Sign Up tabs
#   3. sb_user is set    → signed in, show user info + history
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        '<div style="padding:4px 0 2px;font-size:15px;font-weight:800;'
        'color:#e2e8f0;letter-spacing:-.3px;">Resume Tailor AI</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="height:1px;background:rgba(255,255,255,.06);margin:10px 0 18px;"></div>',
        unsafe_allow_html=True,
    )

    if sb is None:
        # Supabase secrets missing — auth and history are disabled but the
        # core pipeline still works (Groq key is all that's required).
        st.caption("Auth unavailable — add Supabase secrets to enable.")

    elif st.session_state["sb_user"] is None:
        # ── Not signed in: show Sign In / Sign Up tabs ────────────────────────
        st.markdown(
            '<div style="font-size:12px;color:#6b7280;margin-bottom:10px;">'
            'Sign in to save your history.</div>',
            unsafe_allow_html=True,
        )
        tab_in, tab_up = st.tabs(["Sign In", "Sign Up"])

        with tab_in:
            li_email = st.text_input("Email", key="li_email", placeholder="you@example.com")
            li_pw    = st.text_input("Password", type="password", key="li_pw", placeholder="••••••••")
            if st.button("Sign In", key="btn_signin", use_container_width=True):
                if li_email and li_pw:
                    try:
                        res = sb.auth.sign_in_with_password({"email": li_email, "password": li_pw})
                        # Store minimal user info as a plain dict (not the full
                        # Supabase user object) — avoids serialization issues
                        # and keeps only what we actually need downstream.
                        st.session_state["sb_user"]    = {"id": res.user.id, "email": res.user.email}
                        st.session_state["sb_access"]  = res.session.access_token
                        st.session_state["sb_refresh"] = res.session.refresh_token
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.warning("Enter email and password.")

        with tab_up:
            su_email = st.text_input("Email", key="su_email", placeholder="you@example.com")
            su_pw    = st.text_input("Password (min 6 chars)", type="password", key="su_pw", placeholder="••••••••")
            if st.button("Create Account", key="btn_signup", use_container_width=True):
                if su_email and su_pw:
                    try:
                        # Supabase sends a confirmation email before the account
                        # is active — user must verify before they can sign in.
                        sb.auth.sign_up({"email": su_email, "password": su_pw})
                        st.success("Account created! Check your email to confirm, then sign in.")
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.warning("Fill in all fields.")

    else:
        # ── Signed in: show user info, sign out, and history ─────────────────
        user = st.session_state["sb_user"]
        st.markdown(
            f'<div style="font-size:11px;color:#6b7280;margin-bottom:2px;">Signed in as</div>'
            f'<div style="font-size:13px;font-weight:700;color:#e2e8f0;'
            f'word-break:break-all;margin-bottom:12px;">{user["email"]}</div>',
            unsafe_allow_html=True,
        )
        # .sb-signout wraps the button in a CSS class that overrides the default
        # indigo button style to a red/rose variant for destructive actions.
        st.markdown('<div class="sb-signout">', unsafe_allow_html=True)
        if st.button("Sign Out", key="btn_signout", use_container_width=True):
            try:
                sb.auth.sign_out()
            except Exception:
                pass
            # Clear all auth state from session — the next rerun will show the
            # sign-in form and the Supabase client will be unauthenticated.
            st.session_state.update({"sb_user": None, "sb_access": None, "sb_refresh": None})
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Per-user history ──────────────────────────────────────────────────
        # Fetches the 5 most recent runs for this user from the Supabase
        # `history` table. RLS policies on the table ensure users can only
        # query their own rows — the filter by user_id is an extra safeguard.
        st.markdown(
            '<div style="height:1px;background:rgba(255,255,255,.06);margin:16px 0;"></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="font-size:11px;font-weight:700;letter-spacing:.1em;'
            'text-transform:uppercase;color:#6366f1;margin-bottom:10px;">Recent Runs</div>',
            unsafe_allow_html=True,
        )
        try:
            hist = (
                sb.table("history")
                .select("id,role_type,ats_score,jd_snippet,created_at")
                .eq("user_id", user["id"])
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            if hist.data:
                for h in hist.data:
                    # Show role type + ATS score as the expander label so the
                    # user can identify runs at a glance without expanding.
                    label = f"{h['role_type']}  ·  {h['ats_score']}/100"
                    with st.expander(label):
                        st.caption((h["jd_snippet"] or "")[:140] + "…")
            else:
                st.caption("No runs yet — tailor your first resume!")
        except Exception:
            st.caption("History unavailable.")

    # ── Global usage counter — always visible regardless of auth state ────────
    # Reads from the `usage_counter` table (single row with id=1).
    # Displayed at the bottom of the sidebar as a social proof metric.
    st.markdown(
        '<div style="height:1px;background:rgba(255,255,255,.06);margin:20px 0 14px;"></div>',
        unsafe_allow_html=True,
    )
    if sb:
        try:
            cnt = sb.table("usage_counter").select("count").eq("id", 1).execute()
            if cnt.data:
                n = cnt.data[0]["count"]
                st.markdown(
                    f'<div style="text-align:center;">'
                    f'<div style="font-size:30px;font-weight:900;'
                    f'background:linear-gradient(135deg,#818cf8,#34d399);'
                    f'-webkit-background-clip:text;-webkit-text-fill-color:transparent;">'
                    f'{n:,}</div>'
                    f'<div style="font-size:11px;color:#6b7280;margin-top:2px;">'
                    f'resumes tailored</div></div>',
                    unsafe_allow_html=True,
                )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# HERO
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="padding:52px 0 12px 0;" class="fade-up">
  <div class="hero-title">
    Land the Interview<br>
    <span class="grad-text">Every Single Time.</span>
  </div>
  <p class="hero-sub">
    Paste any job description and get a perfectly tailored resume,<br>
    ATS score, and cover note — powered by AI in under 30 seconds.
  </p>

  <div class="steps-row">
    <div class="step-card">
      <div class="step-num" style="background:rgba(99,102,241,.15);color:#a5b4fc;">1</div>
      <div class="step-title">Analyze JD</div>
      <div class="step-desc">Extracts role type, must-have skills, ATS keywords, and company tone.</div>
    </div>
    <div class="step-card">
      <div class="step-num" style="background:rgba(139,92,246,.15);color:#c4b5fd;">2</div>
      <div class="step-title">Tailor Resume</div>
      <div class="step-desc">Rewrites summary and bullets to mirror the JD — zero fabrication.</div>
    </div>
    <div class="step-card">
      <div class="step-num" style="background:rgba(16,185,129,.12);color:#34d399;">3</div>
      <div class="step-title">ATS Simulation</div>
      <div class="step-desc">Scores keyword coverage, skill alignment, and experience fit.</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT
# ═══════════════════════════════════════════════════════════════════════════════
jd_input = st.text_area(
    label="JD",
    placeholder="Paste the full job description here — include requirements, responsibilities, and tech stack…",
    height=200,
    label_visibility="collapsed",
)

_, btn_col, _ = st.columns([2, 3, 2])
with btn_col:
    run = st.button("✦  Tailor My Resume", type="primary", use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
if run:
    if not jd_input.strip():
        st.error("Please paste a job description first.")
    else:
        # Import lazily so the Groq client isn't instantiated until the button
        # is clicked — by that point, os.environ["GROQ_API_KEY"] is guaranteed
        # to be set by the bootstrap block at the top of this file.
        from tailor import analyze_jd, tailor_resume, ats_score, PipelineError

        # st.empty() gives us a single placeholder we can overwrite on each
        # step to update the pipeline progress bar in-place rather than
        # appending a new bar below the previous one.
        ph = st.empty()

        try:
            # Step 1: Extract structured data from the JD
            ph.markdown(pipeline_status(1), unsafe_allow_html=True)
            jd_analysis = analyze_jd(jd_input)

            # Step 2: Rewrite resume sections to match the JD
            ph.markdown(pipeline_status(2), unsafe_allow_html=True)
            tailored = tailor_resume(jd_analysis)

            # Step 3: Score the tailored resume against the JD
            ph.markdown(pipeline_status(3), unsafe_allow_html=True)
            ats = ats_score(jd_input, tailored)

            # All steps done — show the completed bar
            ph.markdown(pipeline_status(4), unsafe_allow_html=True)

        except PipelineError as e:
            # PipelineError carries a clean user-facing message from tailor.py.
            # Clear the progress bar so the error replaces it cleanly.
            ph.empty()
            st.error(str(e))
            st.stop()

        # Bundle all three results into one dict for JSON download and history storage.
        result    = {"jd_analysis": jd_analysis, "tailored_resume": tailored, "ats_score": ats}
        score_val = ats["ats_score"]
        c1, _, vbg, _  = score_colors(score_val)

        # ── Save run to per-user history ──────────────────────────────────────
        # Only runs if the user is signed in. Failures are silently swallowed —
        # a history write failure should never block the user from seeing results.
        # The full_result JSONB column stores everything so users can revisit
        # past runs in detail from the history panel.
        if sb and st.session_state["sb_user"]:
            try:
                sb.table("history").insert({
                    "user_id":    st.session_state["sb_user"]["id"],
                    "jd_snippet": jd_input[:200],       # first 200 chars as preview
                    "role_type":  jd_analysis.get("role_type", "Unknown"),
                    "ats_score":  score_val,
                    "full_result": result,
                }).execute()
            except Exception:
                pass  # non-critical — don't surface to user

        # ── Increment global usage counter ────────────────────────────────────
        # Calls a SECURITY DEFINER SQL function (increment_usage) that atomically
        # increments the single row in usage_counter. SECURITY DEFINER bypasses
        # RLS so even anonymous users contribute to the count. Silent on failure.
        if sb:
            try:
                sb.rpc("increment_usage").execute()
            except Exception:
                pass

        st.markdown('<div class="fancy-hr"></div>', unsafe_allow_html=True)

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 1 — ATS Overview
        # ═══════════════════════════════════════════════════════════════════════
        st.markdown(section_header("ATS Analysis"), unsafe_allow_html=True)

        col_gauge, col_jd = st.columns([5, 8], gap="large")

        with col_gauge:
            verdict = ats["one_line_verdict"]
            sb_data = ats["score_breakdown"]
            st.markdown(f"""
            <div class="glass fade-up" style="text-align:center;">
              {svg_gauge(score_val)}
              <div class="verdict-badge" style="background:{vbg};color:{c1};border:1px solid {c1}40;">
                {verdict}
              </div>
              <div style="margin-top:24px;text-align:left;">
                {progress_bar("Keyword Coverage", sb_data["keyword_coverage"], 40,
                              "linear-gradient(90deg,#6366f1,#818cf8)")}
                {progress_bar("Skill Alignment",  sb_data["skill_alignment"],  30,
                              "linear-gradient(90deg,#8b5cf6,#a78bfa)")}
                {progress_bar("Experience Fit",   sb_data["experience_relevance"], 30,
                              "linear-gradient(90deg,#10b981,#34d399)")}
              </div>
            </div>
            """, unsafe_allow_html=True)

        with col_jd:
            st.markdown(f"""
            <div class="glass fade-up">
              <div class="meta-grid">
                <div class="meta-chip">
                  <div class="meta-chip-key">Role</div>
                  <div class="meta-chip-value">{jd_analysis["role_type"]}</div>
                </div>
                <div class="meta-chip">
                  <div class="meta-chip-key">Domain</div>
                  <div class="meta-chip-value">{jd_analysis["domain"]}</div>
                </div>
                <div class="meta-chip">
                  <div class="meta-chip-key">Company Type</div>
                  <div class="meta-chip-value">{jd_analysis["company_tone"]}</div>
                </div>
              </div>

              <div class="emphasis-box">💡 {jd_analysis["emphasis"]}</div>

              <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:18px;">
                <div>
                  <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#10b981;margin-bottom:8px;">✓ Keyword Matches</div>
                  {pills(ats["keyword_matches"], "pill-green")}
                </div>
                <div>
                  <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#f43f5e;margin-bottom:8px;">✗ Missing Keywords</div>
                  {pills(ats["keyword_misses"], "pill-red")}
                </div>
              </div>

              <div style="margin-bottom:14px;">
                <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#6366f1;margin-bottom:8px;">Must-Have Skills</div>
                {pills(jd_analysis["must_have_skills"], "pill-indigo")}
              </div>
              <div>
                <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#8b5cf6;margin-bottom:8px;">Good to Have</div>
                {pills(jd_analysis["good_to_have_skills"], "pill-violet")}
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="fancy-hr"></div>', unsafe_allow_html=True)

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 2 — Tailored Resume
        # ═══════════════════════════════════════════════════════════════════════
        st.markdown(section_header("Tailored Resume"), unsafe_allow_html=True)

        col_sum, col_sk = st.columns([3, 2], gap="large")

        with col_sum:
            st.markdown(f"""
            <div class="glass fade-up">
              <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#6366f1;margin-bottom:14px;">Professional Summary</div>
              <p class="summary-text">{tailored["tailored_summary"]}</p>
            </div>
            """, unsafe_allow_html=True)

        with col_sk:
            move_up = tailored.get("skills_to_add_if_familiar", [])
            move_up_html = ""
            if move_up:
                move_up_html = f"""
                <div style="margin-top:18px;padding-top:16px;border-top:1px solid rgba(255,255,255,.06);">
                  <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#8b5cf6;margin-bottom:8px;">Worth Moving Up</div>
                  {pills(move_up, "pill-violet")}
                </div>"""
            st.markdown(f"""
            <div class="glass fade-up">
              <div style="font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#06b6d4;margin-bottom:14px;">Skills to Highlight</div>
              {pills(tailored["skills_to_highlight"], "pill-cyan")}
              {move_up_html}
            </div>
            """, unsafe_allow_html=True)

        # Projects
        st.markdown("""
        <div style="font-size:15px;font-weight:800;color:#e2e8f0;margin:28px 0 14px 0;
             letter-spacing:-.2px;">
          Projects <span style="color:#6366f1;">—</span>
          <span style="font-weight:400;color:#6b7280;font-size:13px;"> ranked by relevance</span>
        </div>
        """, unsafe_allow_html=True)

        rank_cls = ["", "rank-2", "rank-3", "rank-4"]
        for i, proj in enumerate(tailored["projects"]):
            badge = '<span class="top-badge">⭐ Top Match</span>' if i == 0 else ""
            bullets_html = "".join(
                f'<div class="bullet-item">{b}</div>' for b in proj["bullets"]
            )
            st.markdown(f"""
            <div class="proj-card {rank_cls[min(i, 3)]} fade-up">
              <div class="proj-title">{proj["name"]}{badge}</div>
              {pills(proj["tech"], "pill-slate")}
              <div style="margin-top:14px;">{bullets_html}</div>
              <div class="proj-why">💡 {proj["relevance_note"]}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="fancy-hr"></div>', unsafe_allow_html=True)

        # ═══════════════════════════════════════════════════════════════════════
        # SECTION 3 — Cover Note + Downloads
        # ═══════════════════════════════════════════════════════════════════════
        st.markdown(section_header("Cover Note & Downloads"), unsafe_allow_html=True)

        col_cv, col_dl = st.columns([3, 1], gap="large")

        with col_cv:
            st.markdown(f"""
            <div class="cover-wrap fade-up">
              {tailored["cover_note"]}
            </div>
            """, unsafe_allow_html=True)

        with col_dl:
            st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
            st.download_button(
                label="⬇  Download PDF",
                data=build_pdf(resume, tailored),
                file_name="tailored_resume.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.download_button(
                label="⬇  Download JSON",
                data=json.dumps(result, indent=2),
                file_name="tailored_resume.json",
                mime="application/json",
                use_container_width=True,
            )

        st.markdown('<div style="height:48px;"></div>', unsafe_allow_html=True)
