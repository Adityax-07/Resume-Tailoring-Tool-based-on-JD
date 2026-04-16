import json
import os
import re
import time
from groq import Groq, RateLimitError, APIConnectionError, APIStatusError
from resume_data import resume

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = "llama-3.3-70b-versatile"


class PipelineError(Exception):
    """User-facing error with a clean message."""
    pass


def _call(messages: list, max_tokens: int) -> str:
    """Single API call with one retry on rate limit."""
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=max_tokens,
                messages=messages,
            )
            return response.choices[0].message.content
        except RateLimitError:
            if attempt == 0:
                time.sleep(5)
                continue
            raise PipelineError("Rate limit reached. Wait a few seconds and try again.")
        except APIConnectionError:
            raise PipelineError("Cannot reach the AI API. Check your internet connection.")
        except APIStatusError as e:
            raise PipelineError(f"AI API returned an error ({e.status_code}). Try again shortly.")
        except Exception as e:
            raise PipelineError(f"Unexpected error during API call: {e}")


def _parse_json(raw: str, step: str) -> dict:
    """
    Parse JSON from LLM output.
    Handles markdown code fences and stray text before/after the object.
    """
    # Strip markdown fences
    text = re.sub(r"```(?:json)?", "", raw).strip()

    # Extract the outermost { ... }
    start = text.find("{")
    end   = text.rfind("}")
    if start == -1 or end == -1:
        raise PipelineError(
            f"Step '{step}': AI returned an unexpected format. Please try again."
        )
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise PipelineError(
            f"Step '{step}': Could not parse AI response as JSON ({e}). Please try again."
        )


# ─────────────────────────────────────────
# PROMPT 1: Analyze the JD
# ─────────────────────────────────────────

def analyze_jd(jd_text: str) -> dict:
    prompt = f"""You are an expert technical recruiter analyzing a job description for an AI/ML internship role.

Analyze this JD carefully and extract the following. Be precise and technical.

JD:
{jd_text}

Return a JSON object with exactly these fields:

{{
  "role_type": "one of: GenAI Engineer / ML Engineer / MLOps / Data Science / Full Stack AI / Research",

  "must_have_skills": ["list of skills explicitly required — max 8"],

  "good_to_have_skills": ["list of preferred/bonus skills — max 5"],

  "key_keywords": ["exact technical terms from JD that ATS will scan for — max 12"],

  "domain": "what industry/domain (fintech, healthtech, SaaS, etc.)",

  "responsibilities": ["top 4 actual day-to-day tasks from JD"],

  "company_tone": "one of: early-stage startup / growth startup / mid-size product / enterprise / research lab",

  "emphasis": "what does this role value most — one sentence (e.g. 'production deployment experience over research')",

  "projects_to_highlight": ["from this candidate's projects: RAG Systems Eval Suite, CodeSage, Autonomous MLOps Agent, Multi-Agent System — which 2 are most relevant and why, as short strings"]
}}

Return ONLY the JSON. No explanation, no markdown, no backticks."""

    raw = _call([{"role": "user", "content": prompt}], max_tokens=1000)
    return _parse_json(raw, "Analyze JD")


# ─────────────────────────────────────────
# PROMPT 2: Tailor the Resume Content
# ─────────────────────────────────────────

def tailor_resume(jd_analysis: dict, resume_data: dict = None) -> dict:
    source = resume_data if resume_data is not None else resume

    prompt = f"""You are an expert resume writer helping an AI/ML student tailor their resume for a specific internship role.

CANDIDATE'S ORIGINAL RESUME:
{json.dumps(source, indent=2)}

JD ANALYSIS:
{json.dumps(jd_analysis, indent=2)}

Your job is to rewrite specific parts of this resume to better match the JD. Follow these strict rules:

RULES:
1. NEVER fabricate experience, projects, or skills that don't exist in the original resume
2. ONLY rephrase, reorder, and emphasize — facts must stay accurate
3. Use keywords from key_keywords naturally — don't keyword stuff
4. Prioritize the 2 most relevant projects (from projects_to_highlight) — put them first
5. Rewrite bullet points to mirror the language and emphasis of the JD
6. Adjust summary to speak directly to what this role needs
7. If company_tone is startup — keep language punchy and impact-focused
8. If company_tone is enterprise — keep language structured and process-oriented

Return a JSON object with exactly these fields:

{{
  "tailored_summary": "2-3 sentence summary rewritten to match this specific role and company tone",

  "skills_to_highlight": ["reordered/filtered skills list — put JD-relevant ones first — max 15 total"],

  "projects": [
    {{
      "name": "project name — unchanged",
      "tech": ["tech stack — unchanged"],
      "bullets": [
        "rewritten bullet 1 — uses JD keywords naturally",
        "rewritten bullet 2",
        "rewritten bullet 3",
        "rewritten bullet 4"
      ],
      "relevance_note": "one line why this project matches this JD — only for your reference, not on resume"
    }}
  ],

  "skills_to_add_if_familiar": ["skills from JD that candidate listed as 'familiar' — worth moving up for this role"],

  "cover_note": "2-3 sentence note YOU would write as the candidate in a cold DM or cover letter for this specific role — casual tone if startup, formal if enterprise"
}}

Project order must be: most relevant first (based on projects_to_highlight), others after.
Return ONLY the JSON. No explanation, no markdown, no backticks."""

    raw = _call([{"role": "user", "content": prompt}], max_tokens=2000)
    return _parse_json(raw, "Tailor Resume")


# ─────────────────────────────────────────
# PROMPT 3: ATS Score Check
# ─────────────────────────────────────────

def ats_score(jd_text: str, tailored: dict) -> dict:
    prompt = f"""You are an ATS (Applicant Tracking System) simulator.

Score this tailored resume against the JD.

JD:
{jd_text}

TAILORED RESUME CONTENT:
{json.dumps(tailored, indent=2)}

Return a JSON object:

{{
  "ats_score": <integer 0-100>,

  "keyword_matches": ["keywords from JD found in resume"],

  "keyword_misses": ["important JD keywords NOT in resume"],

  "score_breakdown": {{
    "keyword_coverage": <0-40 points>,
    "skill_alignment": <0-30 points>,
    "experience_relevance": <0-30 points>
  }},

  "one_line_verdict": "e.g. Strong match — apply confidently / Partial match — customize cover note / Weak match — consider skipping"
}}

Return ONLY the JSON. No explanation, no markdown, no backticks."""

    raw = _call([{"role": "user", "content": prompt}], max_tokens=800)
    return _parse_json(raw, "ATS Score")
