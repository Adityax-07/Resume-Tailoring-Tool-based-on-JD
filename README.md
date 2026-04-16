# Resume Tailor AI

Paste any job description and get a tailored resume, ATS score, and cover note in under 30 seconds — powered by Groq + Llama 3.3.

## What it does

Runs a 3-step LLM pipeline against your resume:

1. **Analyze JD** — extracts role type, must-have skills, ATS keywords, company tone, and emphasis
2. **Tailor Resume** — rewrites your summary, reorders projects by relevance, and adjusts bullet points to mirror JD language (no fabrication — only rephrasing)
3. **ATS Score** — simulates an ATS check, scores keyword coverage / skill alignment / experience fit, and flags missing keywords

Results include a generated cover note and download options for PDF and JSON.

## Features

- 3-step structured LLM pipeline (not a ChatGPT wrapper)
- ATS simulation with keyword match/miss breakdown and score gauge
- Tailored cover note based on company tone (startup vs enterprise)
- PDF resume download via ReportLab
- Email auth (sign up / sign in) powered by Supabase
- Per-user history — every pipeline run is saved and shown in the sidebar
- Global usage counter tracking total resumes tailored

## Stack

- [Streamlit](https://streamlit.io) — UI
- [Groq](https://groq.com) (`llama-3.3-70b-versatile`) — all three pipeline steps
- [Supabase](https://supabase.com) — auth + history storage (Postgres + RLS)
- [ReportLab](https://www.reportlab.com) — PDF generation
- Python 3.10+

## Setup

```bash
pip install streamlit groq reportlab supabase
```

Create `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY    = "your-groq-api-key"
SUPABASE_URL    = "https://your-project.supabase.co"
SUPABASE_KEY    = "your-supabase-anon-key"
```

Update `resume_data.py` with your own resume details.

## Run

```bash
streamlit run app.py
```

## Project structure

```
├── app.py               # Streamlit UI + sidebar auth + results
├── tailor.py            # 3-step Groq pipeline with error handling
├── supabase_client.py   # Per-session Supabase client
├── pdf_generator.py     # ReportLab PDF builder
├── resume_data.py       # Your resume as a structured dict
└── requirements.txt     # Dependencies
```

## Supabase schema

Two tables required — `history` (per-user run logs, RLS enabled) and `usage_counter` (global counter with atomic increment via SQL function). See setup instructions in the project wiki or run the SQL from the source comments.
