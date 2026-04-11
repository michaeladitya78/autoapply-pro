"""Resume upload, parsing, and vectorization."""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import io
import uuid
import PyPDF2
import docx
import structlog

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import Resume
from app.agents.llm import claude_parse_resume

log = structlog.get_logger()
router = APIRouter()

ALLOWED_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_SIZE_MB = 5


async def extract_text_from_file(file: UploadFile) -> str:
    """Extract raw text from PDF or DOCX."""
    content = await file.read()

    if file.content_type == "application/pdf":
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif "wordprocessingml" in file.content_type:
        doc = docx.Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    else:
        raise HTTPException(415, "Only PDF and DOCX files are supported")

    return text.strip()


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload and parse a resume file."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Only PDF and DOCX are supported")

    # Check file size
    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"File must be under {MAX_SIZE_MB}MB")

    # Reset file pointer after reading
    await file.seek(0)

    # Extract text
    raw_text = await extract_text_from_file(file)
    if not raw_text or len(raw_text) < 100:
        raise HTTPException(422, "Could not extract text from resume")

    # Parse with Claude
    structured = await claude_parse_resume(raw_text)

    # Deactivate old resumes
    old_resumes = (await db.scalars(
        select(Resume).where(Resume.user_id == user_id, Resume.is_active == True)
    )).all()
    for old in old_resumes:
        old.is_active = False

    # Store resume
    resume = Resume(
        id=str(uuid.uuid4()),
        user_id=user_id,
        file_url=f"/resumes/{user_id}/{file.filename}",
        filename=file.filename,
        parsed_content=raw_text,
        structured_data=structured,
        is_active=True,
    )
    db.add(resume)
    await db.flush()

    # Vectorize for semantic matching
    try:
        from app.services.vector_service import index_resume
        chroma_id = await index_resume(resume.id, raw_text)
        resume.chroma_doc_id = chroma_id
    except Exception as e:
        log.warning("Resume vectorization failed", error=str(e))

    log.info("Resume uploaded and parsed", user_id=user_id, resume_id=resume.id)

    return {
        "resume_id": resume.id,
        "parsed": structured,
        "text_length": len(raw_text),
    }


@router.get("/active")
async def get_active_resume(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the currently active resume."""
    resume = await db.scalar(
        select(Resume).where(Resume.user_id == user_id, Resume.is_active == True)
    )
    if not resume:
        raise HTTPException(404, "No active resume found")

    return {
        "id": resume.id,
        "filename": resume.filename,
        "structured_data": resume.structured_data,
        "created_at": resume.created_at,
    }
