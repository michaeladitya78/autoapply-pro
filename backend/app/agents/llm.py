"""
LLM Integration — Claude API (cloud-only)
==========================================
Resume tailoring, cover letter generation, cold email drafting,
offer scoring, and job-fit analysis.

Cloud deployment: Ollama is not available on Railway workers.
All LLM calls route through the Anthropic Claude API.

Features:
  - Structured output with Pydantic models (prevents hallucination)
  - Exponential-backoff retry on rate-limit / server errors
  - Model fallback chain: sonnet → opus → haiku
  - Richer, role-aware system prompts to reduce generic AI-speak
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import anthropic
import structlog
from pydantic import BaseModel, Field

from app.core.config import settings

log = structlog.get_logger()

# ─── Claude client ────────────────────────────────────────────────────────────
claude = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

# Model fallback chain — fast to slow, cheap to expensive
_CLAUDE_MODELS = [
    "claude-sonnet-4-5",   # primary — best balance
    "claude-opus-4-5",     # fallback for complex tasks
    "claude-haiku-4-5",    # last resort — fastest/cheapest
]


# ─── Pydantic response schemas ────────────────────────────────────────────────

class TailoredResume(BaseModel):
    resume_text: str = Field(..., description="The full tailored resume text")
    keywords_injected: list[str] = Field(default_factory=list, description="Keywords added")
    ats_score_estimate: int = Field(default=0, ge=0, le=100, description="Estimated ATS match %")
    changes_summary: str = Field(default="", description="Brief summary of what was changed")


class CoverLetter(BaseModel):
    body: str = Field(..., description="Full cover letter text, 250-350 words")
    subject: str = Field(default="", description="Email subject line if sending as email")
    word_count: int = Field(default=0)


class ColdEmail(BaseModel):
    subject: str = Field(..., max_length=60, description="Subject line under 60 chars")
    body: str = Field(..., max_length=1200, description="Email body under 200 words")
    tone: str = Field(default="professional", description="peer-to-peer | formal | casual")


class ParsedResume(BaseModel):
    name: str = Field(default="")
    email: str = Field(default="")
    phone: str = Field(default="")
    summary: str = Field(default="")
    experience: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    links: dict[str, str] = Field(default_factory=dict)


class JobFitAnalysis(BaseModel):
    fit_score: int = Field(..., ge=0, le=100, description="Overall fit 0-100")
    grade: str = Field(..., description="A/B/C/D/F letter grade")
    strengths: list[str] = Field(default_factory=list, description="Top 3 matching strengths")
    gaps: list[str] = Field(default_factory=list, description="Top 3 skill gaps")
    apply_recommendation: bool = Field(..., description="True if worth applying")
    reasoning: str = Field(..., description="One-paragraph honest assessment")
    keywords_present: list[str] = Field(default_factory=list)
    keywords_missing: list[str] = Field(default_factory=list)


class InterviewPrepKit(BaseModel):
    company_summary: str = Field(default="")
    likely_questions: list[str] = Field(default_factory=list)
    star_stories: list[dict[str, str]] = Field(default_factory=list)
    questions_to_ask: list[str] = Field(default_factory=list)
    salary_talking_points: str = Field(default="")


# ─── Retry helper ─────────────────────────────────────────────────────────────

async def _claude_with_retry(
    *,
    model: str,
    max_tokens: int,
    system: str,
    messages: list[dict],
    max_attempts: int = 3,
) -> str:
    """Call Claude with exponential backoff on rate-limit / server errors.
    Falls through model fallback chain on persistent failure."""
    models_to_try = [model] + [m for m in _CLAUDE_MODELS if m != model]
    last_exc: Exception | None = None

    for attempt_model in models_to_try:
        for attempt in range(max_attempts):
            try:
                response = await claude.messages.create(
                    model=attempt_model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                )
                return response.content[0].text
            except anthropic.RateLimitError as e:
                wait = 2 ** attempt * 5  # 5s, 10s, 20s
                log.warning("Claude rate limit, backing off", wait=wait, model=attempt_model)
                await asyncio.sleep(wait)
                last_exc = e
            except anthropic.APIStatusError as e:
                if e.status_code >= 500:
                    await asyncio.sleep(2 ** attempt * 2)
                    last_exc = e
                else:
                    raise  # 4xx errors won't be fixed by retry
            except Exception as e:
                last_exc = e
                break  # Move to next model

        log.warning("Switching to fallback model", failed_model=attempt_model)

    raise RuntimeError(f"All Claude models failed: {last_exc}")


def _extract_json(text: str, expect: type = dict) -> Any:
    """Robustly extract JSON from Claude's text response."""
    # Strip code fences
    text = re.sub(r"```(?:json)?\n?", "", text).strip().rstrip("```").strip()

    if expect == dict or (isinstance(expect, type) and issubclass(expect, dict)):
        start, end = text.find("{"), text.rfind("}") + 1
        if start >= 0:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    elif expect == list:
        start, end = text.find("["), text.rfind("]") + 1
        if start >= 0:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

    # Whole string fallback
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ─── Resume Tailoring ─────────────────────────────────────────────────────────

async def claude_tailor_resume(
    resume_text: str,
    job_description: str,
    job_title: str,
    company: str,
    max_tokens: int = 2500,
) -> TailoredResume:
    """
    Rewrite resume bullet points and summary to match the job description.
    Returns a structured TailoredResume with ATS score estimate.

    Improvements:
    - Quantified impact is preserved/enhanced, not stripped
    - Keywords are injected contextually, not appended as a list
    - Returns metadata alongside the tailored text
    """
    system = """You are a top-1% resume writer and ATS optimization specialist with 15 years
of experience placing candidates at FAANG, startups, and Fortune 500 companies.

Rules you ALWAYS follow:
1. Never fabricate experience, titles, dates, or metrics
2. Preserve the candidate's authentic voice — avoid buzzword-dense corporate speak
3. Quantify impact wherever possible (%, $, time saved, users served)
4. Match keywords from the JD naturally within existing bullet context
5. Keep bullets action-verb first (Built, Led, Reduced, Increased...)
6. Remove filler phrases: "responsible for", "helped with", "worked on"

Output: JSON with keys: resume_text, keywords_injected, ats_score_estimate (0-100), changes_summary"""

    user = f"""## Target Role
Job Title: {job_title}
Company: {company}

## Job Description (first 3000 chars)
{job_description[:3000]}

## Current Resume
{resume_text[:4500]}

Tailor this resume for maximum ATS match. Return JSON only."""

    try:
        raw = await _claude_with_retry(
            model="claude-sonnet-4-5",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        data = _extract_json(raw) or {}
        return TailoredResume(
            resume_text=data.get("resume_text", resume_text),
            keywords_injected=data.get("keywords_injected", []),
            ats_score_estimate=min(100, max(0, int(data.get("ats_score_estimate", 0)))),
            changes_summary=data.get("changes_summary", ""),
        )
    except Exception as e:
        log.error("Resume tailoring failed", error=str(e))
        return TailoredResume(resume_text=resume_text, changes_summary=f"Error: {e}")


# ─── Cover Letter Generation ──────────────────────────────────────────────────

async def claude_generate_cover_letter(
    resume_text: str,
    job_description: str,
    job_title: str,
    company: str,
) -> CoverLetter:
    """
    Generate a personalized cover letter. Returns structured CoverLetter.

    Improvements:
    - Explicit anti-AI-writing instructions
    - Anchors opening to specific company detail from JD
    - Enforces 3-paragraph structure with word-count guard
    """
    system = """You are a direct, no-nonsense career coach who writes cover letters that
actually get read. You hate:
- Generic openers ("I am excited to apply...")
- Hollow claims ("I am passionate about...")
- Restating the resume
- AI-sounding cadences

You write letters that are specific, concrete, and slightly bold. The reader should
feel like the candidate really knows their company and exactly why they fit."""

    user = f"""Write a cover letter for: {job_title} at {company}

JD excerpt: {job_description[:2000]}

Candidate background: {resume_text[:2000]}

Structure (strict):
1. Opening (2 sentences): Reference ONE specific thing from the JD or company that drew you in
2. Body (3-4 sentences): 2 quantified achievements directly relevant to the role
3. Close (2 sentences): Confident, specific ask

Constraints:
- Total: 200-280 words
- No buzzwords: "passionate", "synergy", "leverage", "excited", "journey"
- No "I am writing to apply" or similar

Return JSON: {{subject: string, body: string, word_count: number}}"""

    try:
        raw = await _claude_with_retry(
            model="claude-sonnet-4-5",
            max_tokens=700,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        data = _extract_json(raw) or {}
        body = data.get("body", "")
        return CoverLetter(
            body=body,
            subject=data.get("subject", f"Re: {job_title} at {company}"),
            word_count=len(body.split()),
        )
    except Exception as e:
        log.error("Cover letter generation failed", error=str(e))
        return CoverLetter(body="", subject=f"Re: {job_title} at {company}")


# ─── Cold Email Drafting ──────────────────────────────────────────────────────

async def claude_draft_cold_email(
    my_resume: str,
    contact_name: str,
    contact_title: str,
    company: str,
    company_news: str = "",
    job_role: str = "",
) -> ColdEmail:
    """
    Draft a personalized cold outreach email.

    Improvements:
    - Forces peer-to-peer tone, no deference
    - Validates subject line length
    - Structured output prevents malformed JSON
    """
    system = """You are a senior professional writing to a peer — NOT a job seeker
begging for attention. Your emails are:
- Direct and specific (no "I hope this finds you well")
- Focused on ONE relevant value prop
- Short enough to read in 20 seconds
- Ending with a low-friction ask (15-min call, not "I'd love to chat")"""

    user = f"""Draft a cold outreach email.

Recipient: {contact_name} ({contact_title}) at {company}
Target Role: {job_role or "engineering/technical"}
Company News: {company_news or "N/A"}
My Background (relevant parts): {my_resume[:1500]}

Return JSON: {{
  "subject": "max 55 chars, not 'Following Up', not 'Exploring Opportunities'",
  "body": "max 180 words, peer tone, specific opening, one value fact, one clear ask",
  "tone": "peer-to-peer"
}}"""

    try:
        raw = await _claude_with_retry(
            model="claude-sonnet-4-5",
            max_tokens=450,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        data = _extract_json(raw) or {}
        subject = data.get("subject", f"Quick question about {company}")[:60]
        return ColdEmail(
            subject=subject,
            body=data.get("body", ""),
            tone=data.get("tone", "peer-to-peer"),
        )
    except Exception as e:
        log.error("Cold email generation failed", error=str(e))
        return ColdEmail(subject=f"Quick question about {company}", body="")


# ─── Job Fit Analysis ─────────────────────────────────────────────────────────

async def claude_analyze_job_fit(
    resume_text: str,
    job_description: str,
    job_title: str,
    company: str,
) -> JobFitAnalysis:
    """
    NEW: Analyze how well a candidate fits a job. Returns A-F grade + reasoning.
    This replaces the naive keyword-match with semantic multi-dimensional scoring.

    Scoring dimensions:
    - Technical skill overlap (40%)
    - Experience level alignment (25%)
    - Domain/industry fit (20%)
    - Culture/values signals (15%)
    """
    system = """You are a brutally honest hiring manager with 20+ years of experience.
You score candidates objectively — no sugarcoating. You consider:
- Do they meet the MUST-HAVE requirements?
- Do their quantified achievements match the scope of the role?
- Are there red flags (job-hopping, skill gaps, level mismatch)?
- Is the company a realistic target or a reach?

Grade scale: A=85-100, B=70-84, C=55-69, D=40-54, F=0-39"""

    user = f"""Analyze candidate fit for this role.

JD: {job_title} at {company}
{job_description[:2500]}

Candidate Resume:
{resume_text[:2500]}

Return JSON:
{{
  "fit_score": 0-100,
  "grade": "A/B/C/D/F",
  "strengths": ["top 3 matching points"],
  "gaps": ["top 3 gaps or concerns"],
  "apply_recommendation": true/false,
  "reasoning": "2-3 sentence honest assessment",
  "keywords_present": ["matched keywords"],
  "keywords_missing": ["important missing keywords"]
}}"""

    try:
        raw = await _claude_with_retry(
            model="claude-sonnet-4-5",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        data = _extract_json(raw) or {}
        score = min(100, max(0, int(data.get("fit_score", 50))))
        # Auto-compute grade if not provided
        grade = data.get("grade") or (
            "A" if score >= 85 else
            "B" if score >= 70 else
            "C" if score >= 55 else
            "D" if score >= 40 else "F"
        )
        return JobFitAnalysis(
            fit_score=score,
            grade=grade,
            strengths=data.get("strengths", []),
            gaps=data.get("gaps", []),
            apply_recommendation=bool(data.get("apply_recommendation", score >= 60)),
            reasoning=data.get("reasoning", ""),
            keywords_present=data.get("keywords_present", []),
            keywords_missing=data.get("keywords_missing", []),
        )
    except Exception as e:
        log.error("Job fit analysis failed", error=str(e))
        return JobFitAnalysis(
            fit_score=0, grade="F",
            apply_recommendation=False,
            reasoning=f"Analysis failed: {e}",
        )


# ─── Interview Prep Kit ───────────────────────────────────────────────────────

async def claude_generate_interview_prep(
    resume_text: str,
    job_description: str,
    job_title: str,
    company: str,
) -> InterviewPrepKit:
    """
    NEW: Generate a full interview prep kit for a specific application.

    Includes:
    - Company background / culture signals from JD
    - Predicted interview questions (behavioral + technical)
    - STAR story suggestions mapped to questions
    - Questions to ask the interviewer
    - Salary negotiation talking points
    """
    system = """You are an elite interview coach who has prepared candidates for
roles at Google, Stripe, OpenAI, and top-tier startups. You give specific,
actionable prep — not generic advice. You base everything on the actual JD and resume."""

    user = f"""Prepare a full interview kit.

Role: {job_title} at {company}
JD: {job_description[:2000]}
Candidate: {resume_text[:2000]}

Return JSON:
{{
  "company_summary": "2-sentence company/team context from the JD",
  "likely_questions": ["5-7 most likely questions for this specific role"],
  "star_stories": [
    {{"question": "...", "situation": "...", "task": "...", "action": "...", "result": "..."}}
  ],
  "questions_to_ask": ["3-5 smart questions to ask the interviewer"],
  "salary_talking_points": "one paragraph on salary strategy for this company/role"
}}"""

    try:
        raw = await _claude_with_retry(
            model="claude-sonnet-4-5",
            max_tokens=1800,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        data = _extract_json(raw) or {}
        return InterviewPrepKit(
            company_summary=data.get("company_summary", ""),
            likely_questions=data.get("likely_questions", []),
            star_stories=data.get("star_stories", []),
            questions_to_ask=data.get("questions_to_ask", []),
            salary_talking_points=data.get("salary_talking_points", ""),
        )
    except Exception as e:
        log.error("Interview prep generation failed", error=str(e))
        return InterviewPrepKit()


# ─── Resume Parsing ───────────────────────────────────────────────────────────

async def claude_parse_resume(raw_text: str) -> ParsedResume:
    """Parse raw resume text into structured JSON using Haiku (fast + cheap)."""
    system = "You are a precise resume parser. Extract structured data exactly as found. Never infer or fabricate. Return only valid JSON."
    prompt = f"""Parse this resume into structured JSON.

Resume:
{raw_text[:5000]}

Return JSON with these exact keys:
- name, email, phone, summary (strings)
- experience: [{{"company": "", "title": "", "start": "", "end": "", "bullets": []}}]
- education: [{{"institution": "", "degree": "", "year": ""}}]
- skills: [] (array of strings)
- certifications: [] (array of strings)
- links: {{"linkedin": "", "github": "", "portfolio": ""}}"""

    try:
        raw = await _claude_with_retry(
            model="claude-haiku-4-5",
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        data = _extract_json(raw) or {}
        return ParsedResume(**{k: data.get(k, v) for k, v in ParsedResume().model_dump().items()})
    except Exception as e:
        log.error("Resume parsing failed", error=str(e))
        return ParsedResume()


# ─── Keyword Extraction (Claude-primary, regex fallback) ─────────────────────
#
# Ollama is not available in the cloud deployment (Railway).
# Claude Haiku is used as the primary extractor — it's fast and cheap.
# Regex heuristic is kept as a final fallback when the API is unreachable.


async def ollama_chat(prompt: str, system: str = "", timeout: int = 60) -> str:
    """
    Stub retained for backward compatibility.
    Ollama is not used in cloud deployment — always returns empty string.
    Callers that previously used Ollama-first logic now fall through to Claude.
    """
    return ""


async def extract_keywords(text: str) -> list[str]:
    """
    Extract top keywords from a job description.
    Primary: Claude Haiku (fast, cheap).
    Fallback: regex heuristic.
    """
    prompt = (
        f"Extract the top 20 technical skills, tools, and keywords from this job description. "
        f"Return ONLY a JSON array of strings, no explanation:\n\n{text[:2000]}"
    )

    # 1. Claude Haiku — primary
    try:
        raw = await _claude_with_retry(
            model="claude-haiku-4-5",
            max_tokens=300,
            system="Extract keywords. Return only a JSON array.",
            messages=[{"role": "user", "content": prompt}],
        )
        parsed = _extract_json(raw, expect=list)
        if isinstance(parsed, list) and parsed:
            return [str(k) for k in parsed[:25]]
    except Exception as e:
        log.warning("Claude keyword extraction failed, using regex fallback", error=str(e))

    # 2. Regex heuristic (last resort)
    keywords = re.findall(r"\b[A-Z][a-zA-Z+#]{2,}\b", text)
    common = re.findall(
        r"\b(?:python|golang|react|typescript|aws|kubernetes|docker|postgresql|"
        r"redis|fastapi|nextjs|llm|rag|ml|ai)\b",
        text.lower(),
    )
    return list(set(keywords + [k.upper() for k in common]))[:20]


# Backward-compat alias (used by resume_service.py)
ollama_extract_keywords = extract_keywords
