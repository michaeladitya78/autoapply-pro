"""
Vector service — semantic resume/job matching via pgvector.

Replaces the `chromadb` Python SDK with our pgvector-backed chroma_client
module. The public API (index_resume, semantic_match_jobs) is unchanged so
callers throughout the codebase continue to work without modification.
"""
import uuid
import structlog

from app.core.config import settings
# chroma_client is now a pgvector wrapper — same interface, no SDK needed
from app.core.chroma_client import (
    upsert_documents,
    query_collection,
    get_or_create_collection,
)

log = structlog.get_logger()


async def index_resume(resume_id: str, content: str) -> str:
    """
    Embed and store a resume in pgvector.
    Returns the document ID (same as resume_id).
    """
    doc_id = f"resume_{resume_id}"
    try:
        await upsert_documents(
            collection_name="resumes",
            documents=[content],
            ids=[doc_id],
            metadatas=[{"resume_id": resume_id, "type": "resume"}],
        )
        log.info("Resume indexed in pgvector", resume_id=resume_id)
        return doc_id
    except Exception as e:
        log.error("pgvector indexing failed", error=str(e))
        return ""


async def semantic_match_jobs(resume_id: str, job_descriptions: list[dict]) -> list[dict]:
    """
    Return a list of jobs ranked by their semantic match to the given resume.
    Falls back to returning job_descriptions as-is if vector search fails.
    """
    if not job_descriptions:
        return []

    try:
        # Fetch the stored resume embedding by querying with its doc ID
        resume_results = await query_collection(
            collection_name="resumes",
            query_texts=[""],          # dummy — we'll use the resume content directly
            n_results=1,
            where={"resume_id": resume_id, "type": "resume"},
        )

        if not resume_results:
            log.warning("Resume not in pgvector, returning unranked jobs", resume_id=resume_id)
            return job_descriptions

        resume_text = resume_results[0]["document"]

        # Upsert all job descriptions for comparison
        job_docs = []
        job_ids = []
        job_metas = []
        for job in job_descriptions:
            jid = f"job_{job.get('id', str(uuid.uuid4()))}"
            job_docs.append(job.get("description", ""))
            job_ids.append(jid)
            job_metas.append({"type": "job", "job_id": str(job.get("id", ""))})

        await upsert_documents(
            collection_name="job_matches",
            documents=job_docs,
            ids=job_ids,
            metadatas=job_metas,
        )

        # Vector search: find jobs most similar to the resume
        results = await query_collection(
            collection_name="job_matches",
            query_texts=[resume_text],
            n_results=min(len(job_descriptions), 50),
        )

        # Re-attach scores to original job dicts
        id_to_score = {r["id"]: 1 - r.get("distance", 0.5) for r in results}
        scored = []
        for job in job_descriptions:
            jid = f"job_{job.get('id', '')}"
            scored.append({**job, "match_score": round(id_to_score.get(jid, 0.5), 3)})

        return sorted(scored, key=lambda x: x["match_score"], reverse=True)

    except Exception as e:
        log.error("Semantic matching failed", error=str(e))
        return job_descriptions
