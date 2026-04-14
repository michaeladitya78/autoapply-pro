"""
Resume service — parse, store, and retrieve resumes.
Supports PDF and DOCX. Parsed text stored in DB + vectorized via pgvector.

Changes from local version:
  - `ollama_extract_keywords` replaced with `extract_keywords` (Claude-backed)
  - ChromaDB upsert replaced with pgvector via the same `upsert_documents` call
  - File URL now uses S3 key when AWS is configured, else 'upload://<filename>'
"""
from __future__ import annotations
import io
import uuid
from datetime import datetime
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import Resume
# extract_keywords now uses Claude as primary (Ollama removed)
from app.agents.llm import claude_parse_resume, extract_keywords
from app.core.chroma_client import upsert_documents

log = structlog.get_logger()


def _extract_text_pdf(data: bytes) -> str:
    """Extract text from PDF bytes using PyPDF2."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        log.error("PDF parse failed", error=str(e))
        return ""


def _extract_text_docx(data: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        log.error("DOCX parse failed", error=str(e))
        return ""


async def process_resume_upload(
    user_id: str,
    filename: str,
    file_data: bytes,
    content_type: str,
    db: AsyncSession,
) -> Resume:
    """
    Parse uploaded resume file → extract text → Claude structured parse
    → store in DB → vectorize in pgvector.
    """
    # Extract raw text
    if "pdf" in content_type or filename.lower().endswith(".pdf"):
        raw_text = _extract_text_pdf(file_data)
    elif "word" in content_type or filename.lower().endswith(".docx"):
        raw_text = _extract_text_docx(file_data)
    else:
        raw_text = file_data.decode("utf-8", errors="ignore")

    if not raw_text.strip():
        raise ValueError("Could not extract text from resume — unsupported format or empty file")

    # Claude: structured parse
    structured = await claude_parse_resume(raw_text)

    # Deactivate previous active resumes for user
    prev = (await db.scalars(
        select(Resume).where(Resume.user_id == user_id, Resume.is_active == True)
    )).all()
    for r in prev:
        r.is_active = False

    # Build file URL — use S3 key if configured, else simple identifier
    from app.core.config import settings
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        file_url = f"s3://{settings.AWS_BUCKET_NAME}/resumes/{user_id}/{filename}"
    else:
        file_url = f"upload://{filename}"

    # Create new resume record
    resume_id = str(uuid.uuid4())
    resume = Resume(
        id=resume_id,
        user_id=user_id,
        file_url=file_url,
        filename=filename,
        parsed_content=raw_text,
        structured_data=structured,
        chroma_doc_id=resume_id,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(resume)
    await db.flush()

    # Vectorize in pgvector for similarity search (fire-and-forget — non-fatal)
    try:
        keywords = await extract_keywords(raw_text)
        combined = raw_text + "\nKeywords: " + ", ".join(keywords)
        await upsert_documents(
            collection_name=f"resumes_{user_id}",
            documents=[combined],
            metadatas=[{"resume_id": resume_id, "user_id": user_id, "filename": filename}],
            ids=[resume_id],
        )
    except Exception as e:
        log.warning("pgvector vectorization failed (non-fatal)", error=str(e))

    log.info(
        "Resume processed",
        user_id=user_id,
        resume_id=resume_id,
        chars=len(raw_text),
        has_structured=bool(structured),
    )
    return resume
