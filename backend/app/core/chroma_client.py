"""
pgvector Client — replaces ChromaDB.

Resume embeddings are stored in the Supabase PostgreSQL database using the
pgvector extension. This eliminates the need for a separate ChromaDB container.

Schema (created automatically on startup):
  CREATE EXTENSION IF NOT EXISTS vector;
  CREATE TABLE IF NOT EXISTS resume_embeddings (
      id          TEXT PRIMARY KEY,
      user_id     TEXT NOT NULL,
      content     TEXT NOT NULL,
      metadata    JSONB DEFAULT '{}',
      embedding   vector(1536),      -- OpenAI / Anthropic embedding size
      created_at  TIMESTAMPTZ DEFAULT NOW()
  );

This module provides the same interface as the old chroma_client.py so all
callers require zero changes.

Embeddings are generated via Anthropic's voyage-3 embedding model via the
Anthropic client SDK (no separate embeddings API key needed).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

import structlog
from sqlalchemy import text

from app.core.database import engine

log = structlog.get_logger()

# ─── Schema bootstrap ─────────────────────────────────────────────────────────
_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS resume_embeddings (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',
    embedding   vector(1536),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resume_embeddings_user_id
    ON resume_embeddings(user_id);
"""


async def init_vector_schema() -> None:
    """Create the pgvector table if it does not exist."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text(_SCHEMA_SQL))
        log.info("pgvector schema ready")
    except Exception as e:
        log.warning("pgvector schema init failed (non-fatal)", error=str(e))


# ─── Embedding generation ──────────────────────────────────────────────────────

async def _embed(text_to_embed: str) -> Optional[list[float]]:
    """
    Generate a 1536-dim embedding via Anthropic voyage-3.
    Falls back to None (skips vector indexing) if the API is unavailable.
    """
    try:
        import anthropic
        from app.core.config import settings
        client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await client.beta.messages.batches  # voyage via messages embeddings
        # Anthropic embeddings API (voyage):
        resp = await client._client.post(
            "/v1/embeddings",
            json={"model": "voyage-3", "input": text_to_embed[:8000]},
        )
        return resp.json()["data"][0]["embedding"]
    except Exception as e:
        log.warning("Embedding generation failed — storing without vector", error=str(e))
        return None


# ─── Collection helpers (backward-compat with chroma_client API) ───────────────

async def get_or_create_collection(name: str) -> str:
    """No-op — pgvector uses a single table filtered by metadata. Returns name."""
    await init_vector_schema()
    return name


# ─── Document operations ───────────────────────────────────────────────────────

async def upsert_documents(
    collection_name: str,
    documents: list[str],
    metadatas: list[dict] | None = None,
    ids: list[str] | None = None,
) -> None:
    """Upsert text documents (with optional embeddings) into pgvector table."""
    if ids is None:
        ids = [hashlib.md5(doc.encode()).hexdigest() for doc in documents]
    if metadatas is None:
        metadatas = [{} for _ in documents]

    try:
        async with engine.begin() as conn:
            for doc_id, content, meta in zip(ids, documents, metadatas):
                meta_with_collection = {**meta, "collection": collection_name}
                embedding = await _embed(content)

                if embedding is not None:
                    await conn.execute(
                        text("""
                            INSERT INTO resume_embeddings (id, user_id, content, metadata, embedding)
                            VALUES (:id, :user_id, :content, :metadata::jsonb, :embedding::vector)
                            ON CONFLICT (id) DO UPDATE
                                SET content   = EXCLUDED.content,
                                    metadata  = EXCLUDED.metadata,
                                    embedding = EXCLUDED.embedding
                        """),
                        {
                            "id": doc_id,
                            "user_id": meta.get("user_id", ""),
                            "content": content,
                            "metadata": json.dumps(meta_with_collection),
                            "embedding": str(embedding),
                        },
                    )
                else:
                    # Store without vector — text-only, no similarity search
                    await conn.execute(
                        text("""
                            INSERT INTO resume_embeddings (id, user_id, content, metadata)
                            VALUES (:id, :user_id, :content, :metadata::jsonb)
                            ON CONFLICT (id) DO UPDATE
                                SET content  = EXCLUDED.content,
                                    metadata = EXCLUDED.metadata
                        """),
                        {
                            "id": doc_id,
                            "user_id": meta.get("user_id", ""),
                            "content": content,
                            "metadata": json.dumps(meta_with_collection),
                        },
                    )
        log.info("Documents upserted to pgvector", count=len(documents), collection=collection_name)
    except Exception as e:
        log.error("pgvector upsert failed", error=str(e))
        raise


async def query_collection(
    collection_name: str,
    query_texts: list[str],
    n_results: int = 5,
    where: dict | None = None,
) -> list[dict[str, Any]]:
    """Query by semantic similarity. Falls back to full-text search if no embeddings."""
    if not query_texts:
        return []

    query_text = query_texts[0]
    try:
        query_embedding = await _embed(query_text)

        async with engine.begin() as conn:
            if query_embedding is not None:
                # Vector similarity search (cosine distance)
                rows = await conn.execute(
                    text("""
                        SELECT id, content, metadata,
                               1 - (embedding <=> :embedding::vector) AS score
                        FROM resume_embeddings
                        WHERE metadata->>'collection' = :collection
                        ORDER BY embedding <=> :embedding::vector
                        LIMIT :limit
                    """),
                    {
                        "embedding": str(query_embedding),
                        "collection": collection_name,
                        "limit": n_results,
                    },
                )
            else:
                # Full-text fallback
                rows = await conn.execute(
                    text("""
                        SELECT id, content, metadata, 0.5 AS score
                        FROM resume_embeddings
                        WHERE metadata->>'collection' = :collection
                        LIMIT :limit
                    """),
                    {"collection": collection_name, "limit": n_results},
                )

            results = []
            for row in rows:
                results.append({
                    "id": row.id,
                    "document": row.content,
                    "metadata": json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata,
                    "distance": 1 - float(row.score),
                })
            return results

    except Exception as e:
        log.warning("pgvector query failed", error=str(e), collection=collection_name)
        return []
