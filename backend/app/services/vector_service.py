"""ChromaDB vector service for semantic resume-job matching."""
import chromadb
import uuid
import structlog
from app.core.config import settings

log = structlog.get_logger()

_client = None


def get_chroma_client():
    global _client
    if _client is None:
        _client = chromadb.HttpClient(host=settings.CHROMA_HOST.replace("http://", ""), port=8000)
    return _client


def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="resumes",
        metadata={"hnsw:space": "cosine"},
    )


async def index_resume(resume_id: str, content: str) -> str:
    """Embed and store resume in ChromaDB. Returns document ID."""
    try:
        collection = get_collection()
        doc_id = f"resume_{resume_id}"
        collection.upsert(
            documents=[content],
            ids=[doc_id],
            metadatas=[{"resume_id": resume_id, "type": "resume"}],
        )
        log.info("Resume indexed in ChromaDB", resume_id=resume_id)
        return doc_id
    except Exception as e:
        log.error("ChromaDB indexing failed", error=str(e))
        return ""


async def semantic_match_jobs(resume_id: str, job_descriptions: list[dict]) -> list[dict]:
    """Return jobs ranked by semantic match to resume."""
    try:
        collection = get_collection()

        # First query the resume embedding
        resume_result = collection.get(ids=[f"resume_{resume_id}"])
        if not resume_result["documents"]:
            return job_descriptions

        resume_text = resume_result["documents"][0]

        # Upsert jobs temporarily for comparison
        job_ids = []
        for job in job_descriptions:
            jid = f"job_{job.get('id', uuid.uuid4())}"
            collection.upsert(
                documents=[job.get("description", "")],
                ids=[jid],
                metadatas=[{"type": "job", "job_id": job.get("id", "")}],
            )
            job_ids.append(jid)

        # Query for similar jobs
        results = collection.query(
            query_texts=[resume_text],
            n_results=min(len(job_descriptions), 50),
            where={"type": "job"},
        )

        scored = []
        for i, (jid, dist) in enumerate(zip(results["ids"][0], results["distances"][0])):
            match = next((j for j in job_descriptions if f"job_{j.get('id', '')}" == jid), None)
            if match:
                scored.append({**match, "match_score": round(1 - dist, 3)})

        return sorted(scored, key=lambda x: x["match_score"], reverse=True)

    except Exception as e:
        log.error("Semantic matching failed", error=str(e))
        return job_descriptions
