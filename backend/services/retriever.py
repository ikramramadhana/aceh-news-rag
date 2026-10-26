from google.genai import types
from supabase import Client

from config import (
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
    DEFAULT_MATCH_COUNT,
    SOURCE_SIMILARITY_MARGIN,
    MIN_ABSOLUTE_SIMILARITY,
)
from gemini_client import client


def embed_query(text: str) -> list[float]:
    """Generate embedding untuk query user (task_type beda dari saat indexing)."""
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return result.embeddings[0].values


def filter_by_similarity(chunks: list[dict], query: str = "") -> list[dict]:
    """Buang chunk yang skornya jauh di bawah hasil teratas, supaya berita yang
    nggak nyambung nggak ikut masuk ke jawaban maupun daftar sumber."""
    if not chunks:
        return chunks

    top = max(c.get("similarity") or 0 for c in chunks)
    relative_cutoff = top - SOURCE_SIMILARITY_MARGIN
    cutoff = max(relative_cutoff, MIN_ABSOLUTE_SIMILARITY)
    kept = [c for c in chunks if (c.get("similarity") or 0) >= cutoff]

    scores = ", ".join(f"{(c.get('similarity') or 0):.3f}" for c in chunks)
    print(f"[retrieval] q={query[:60]!r} skor=[{scores}] dipakai={len(kept)}/{len(chunks)}")
    return kept


def retrieve_chunks(
    supabase: Client,
    query: str,
    match_count: int = DEFAULT_MATCH_COUNT,
    filter_after: str | None = None,
    filter_category: str | None = None,
    filter_before: str | None = None,
) -> list[dict]:
    """Cari chunk paling relevan dengan query lewat vector similarity search."""
    query_embedding = embed_query(query)

    response = supabase.rpc(
        "match_chunks",
        {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "filter_after": filter_after,
            "filter_category": filter_category,
            "filter_before": filter_before,
        },
    ).execute()

    return filter_by_similarity(response.data or [], query)