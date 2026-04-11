"""
Lightweight ChromaDB HTTP client.
Replaces the native `chromadb` Python package — calls ChromaDB's REST API
directly via httpx so we avoid the C++ build dependency (chroma-hnswlib).
ChromaDB v0.5+ exposes a full REST API at http://host:8000.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger()

# ChromaDB REST base URL (resolves to Docker service in compose, localhost in dev)
_BASE = settings.CHROMA_HOST.rstrip("/")


# ─── Collection helpers ────────────────────────────────────────────────────────


async def get_or_create_collection(name: str) -> str:
    """Return the collection UUID, creating it if absent. Returns collection id."""
    async with httpx.AsyncClient(timeout=10) as c:
        # Try to get existing
        r = await c.get(f"{_BASE}/api/v1/collections/{name}")
        if r.status_code == 200:
            return r.json()["id"]
        # Create
        r = await c.post(
            f"{_BASE}/api/v1/collections",
            json={"name": name, "get_or_create": True},
        )
        r.raise_for_status()
        return r.json()["id"]


# ─── Document operations ───────────────────────────────────────────────────────


async def upsert_documents(
    collection_name: str,
    documents: list[str],
    metadatas: list[dict] | None = None,
    ids: list[str] | None = None,
) -> None:
    """Upsert text documents into a ChromaDB collection (uses add with upsert=True)."""
    col_id = await get_or_create_collection(collection_name)
    if ids is None:
        ids = [hashlib.md5(doc.encode()).hexdigest() for doc in documents]
    if metadatas is None:
        metadatas = [{} for _ in documents]

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{_BASE}/api/v1/collections/{col_id}/upsert",
            json={"documents": documents, "metadatas": metadatas, "ids": ids},
        )
        if r.status_code not in (200, 201):
            log.error("ChromaDB upsert failed", status=r.status_code, body=r.text[:200])
            r.raise_for_status()


async def query_collection(
    collection_name: str,
    query_texts: list[str],
    n_results: int = 5,
    where: dict | None = None,
) -> list[dict[str, Any]]:
    """Query a collection and return list of result dicts with document + metadata."""
    try:
        col_id = await get_or_create_collection(collection_name)
        payload: dict[str, Any] = {
            "query_texts": query_texts,
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            payload["where"] = where

        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"{_BASE}/api/v1/collections/{col_id}/query",
                json=payload,
            )
            r.raise_for_status()
            data = r.json()

        results = []
        for i, doc in enumerate(data.get("documents", [[]])[0]):
            results.append({
                "document": doc,
                "metadata": data.get("metadatas", [[]])[0][i] if data.get("metadatas") else {},
                "distance": data.get("distances", [[]])[0][i] if data.get("distances") else None,
                "id": data.get("ids", [[]])[0][i] if data.get("ids") else None,
            })
        return results
    except Exception as e:
        log.warning("ChromaDB query failed", error=str(e), collection=collection_name)
        return []
