"""
LLM Integration — Claude API + Ollama
Resume tailoring, cover letter generation, cold email drafting.
"""
import anthropic
import httpx
import structlog
from app.core.config import settings

log = structlog.get_logger()

# Claude client
claude = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


async def claude_tailor_resume(
    resume_text: str,
    job_description: str,
    job_title: str,
    company: str,
    max_tokens: int = 2000,
) -> str:
    """
    Rewrite resume bullet points and summary to match the job description.
    Uses Claude for semantic alignment and ATS keyword injection.
    """
    system_prompt = """You are an expert resume writer and ATS optimization specialist.
Your task is to subtly rewrite resume bullet points to better match a job description,
injecting relevant keywords naturally while preserving the candidate's authentic voice.
Keep changes minimal but impactful. Do not fabricate experience."""

    user_prompt = f"""Job Title: {job_title}
Company: {company}

Job Description:
{job_description[:3000]}

Current Resume:
{resume_text[:4000]}

Please rewrite the resume to maximize ATS match score for this specific role.
Return ONLY the tailored resume text, no explanations."""

    try:
        response = await claude.messages.create(
            model="claude-opus-4-5",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text
    except Exception as e:
        log.error("Claude resume tailoring failed", error=str(e))
        return resume_text  # Fallback to original


async def claude_generate_cover_letter(
    resume_text: str,
    job_description: str,
    job_title: str,
    company: str,
) -> str:
    """Generate a personalized, role-specific cover letter."""
    prompt = f"""Write a compelling, concise cover letter for this job application.

Job: {job_title} at {company}
Job Description: {job_description[:2000]}
My Background: {resume_text[:2000]}

Requirements:
- 3 paragraphs maximum
- Opening: specific hook referencing the role and company
- Middle: 2-3 concrete achievements that directly address the job requirements
- Close: confident call to action
- Tone: professional but human, NOT generic AI-speak
- Length: 250-350 words maximum

Return ONLY the cover letter text."""

    try:
        response = await claude.messages.create(
            model="claude-opus-4-5",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        log.error("Cover letter generation failed", error=str(e))
        return ""


async def claude_draft_cold_email(
    my_resume: str,
    contact_name: str,
    contact_title: str,
    company: str,
    company_news: str = "",
    job_role: str = "",
) -> dict:
    """Draft a personalized cold outreach email to a recruiter/hiring manager."""
    prompt = f"""Draft a concise, personalized cold outreach email.

Recipient: {contact_name} ({contact_title}) at {company}
Target Role: {job_role or "engineering/technical roles"}
Recent Company News: {company_news or "Not available"}
My Background: {my_resume[:1500]}

Requirements:
- Subject line: intriguing, under 50 chars, no "Following Up" clichés
- Body: 150 words max
- Opening: specific reference to company/role/news — not generic
- Value: one concrete fact from my background that's relevant
- Ask: specific, low-friction (quick call or coffee chat)
- Tone: peer-to-peer, not servile

Return JSON with keys: subject, body"""

    try:
        response = await claude.messages.create(
            model="claude-opus-4-5",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        text = response.content[0].text
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        log.error("Cold email generation failed", error=str(e))
        return {"subject": "Exploring Opportunities", "body": ""}


OLLAMA_MODEL = "mistral"  # pulled via: ollama pull mistral


async def ollama_chat(prompt: str, system: str = "", timeout: int = 60) -> str:
    """
    General-purpose Ollama call for local, privacy-sensitive tasks.
    Returns empty string on failure (caller can fallback to Claude).
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
    except Exception as e:
        log.warning("Ollama unavailable", error=str(e), model=OLLAMA_MODEL)
        return ""


async def ollama_extract_keywords(text: str) -> list[str]:
    """
    Use local Ollama (privacy-first) for fast keyword extraction.
    Falls back to regex heuristic if Ollama unavailable.
    """
    result = await ollama_chat(
        prompt=f"Extract the top 20 technical skills and keywords from this job description. Return only a JSON array of strings:\n\n{text[:2000]}",
    )
    if result:
        try:
            import json
            start = result.find("[")
            end = result.rfind("]") + 1
            return json.loads(result[start:end])
        except Exception:
            pass
    # Fallback: simple regex extraction
    import re
    keywords = re.findall(r"\b[A-Z][a-zA-Z+#]{2,}\b", text)
    return list(set(keywords))[:20]


async def claude_parse_resume(raw_text: str) -> dict:
    """Parse raw resume text into structured JSON."""
    prompt = f"""Parse this resume into structured JSON.

Resume text:
{raw_text[:5000]}

Return JSON with these exact keys:
- name: string
- email: string
- phone: string
- summary: string
- experience: array of {{company, title, start, end, bullets[]}}
- education: array of {{institution, degree, year}}
- skills: array of strings
- certifications: array of strings
- links: {{linkedin, github, portfolio}}

Return only valid JSON, no explanations."""

    try:
        response = await claude.messages.create(
            model="claude-haiku-4-5",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        text = response.content[0].text
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        log.error("Resume parsing failed", error=str(e))
        return {}
