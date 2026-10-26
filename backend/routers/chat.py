from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from supabase import create_client
import json

from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DEFAULT_MATCH_COUNT
from services.retriever import retrieve_chunks
from services.llm import generate_answer, generate_answer_stream, rewrite_query, generate_suggestions

router = APIRouter()

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


class HistoryItem(BaseModel):
    role: str  # "user" atau "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    match_count: int = DEFAULT_MATCH_COUNT
    filter_after: str | None = None  # contoh: "2026-01-01T00:00:00"
    filter_before: str | None = None  # contoh: "2026-01-02T00:00:00" (eksklusif)
    filter_category: str | None = None  # contoh: "Pemerintahan"
    history: list[HistoryItem] = []


class SourceItem(BaseModel):
    title: str
    url: str
    published_at: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    history = [h.model_dump() for h in req.history[-6:]]  # batasi 3 pasang terakhir
    search_query = rewrite_query(req.question, history)

    chunks = retrieve_chunks(
        supabase,
        query=search_query,
        match_count=req.match_count,
        filter_after=req.filter_after,
        filter_category=req.filter_category,
        filter_before=req.filter_before,
    )

    answer = generate_answer(
        req.question, chunks, history=history, standalone_question=search_query
    )

    # dedup sumber berdasarkan article_id, biar 1 artikel nggak muncul dobel
    # kalau kebetulan 2 chunk-nya sama-sama kepilih
    seen_articles = set()
    sources = []
    for c in chunks:
        if c["article_id"] in seen_articles:
            continue
        seen_articles.add(c["article_id"])
        sources.append(
            SourceItem(title=c["title"], url=c["url"], published_at=c["published_at"])
        )

    return ChatResponse(answer=answer, sources=sources)


def _dedup_sources(chunks: list[dict]) -> list[dict]:
    seen_articles = set()
    sources = []
    for c in chunks:
        if c["article_id"] in seen_articles:
            continue
        seen_articles.add(c["article_id"])
        sources.append(
            {"title": c["title"], "url": c["url"], "published_at": c["published_at"]}
        )
    return sources


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    history = [h.model_dump() for h in req.history[-6:]]  # batasi 3 pasang terakhir
    search_query = rewrite_query(req.question, history)

    chunks = retrieve_chunks(
        supabase,
        query=search_query,
        match_count=req.match_count,
        filter_after=req.filter_after,
        filter_category=req.filter_category,
        filter_before=req.filter_before,
    )
    sources = _dedup_sources(chunks)

    def event_generator():
        full_answer = ""
        for text_piece in generate_answer_stream(
            req.question, chunks, history=history, standalone_question=search_query
        ):
            full_answer += text_piece
            yield f"event: answer\ndata: {json.dumps({'text': text_piece})}\n\n"

        # sumber dikirim setelah jawaban selesai di-stream, biar urutannya
        # kerasa natural: teks muncul dulu, baru sumbernya di bawah
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

        suggestions = generate_suggestions(req.question, full_answer, chunks)
        if suggestions:
            yield f"event: suggestions\ndata: {json.dumps(suggestions)}\n\n"

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/categories")
def get_categories():
    """Daftar kategori berita yang tersedia, diurutkan dari yang paling banyak artikelnya."""
    response = supabase.rpc("list_categories").execute()
    return response.data


@router.get("/articles/latest")
def get_latest_articles(limit: int = 6):
    """Daftar berita terbaru, langsung dari tabel articles (tanpa perlu nanya ke chatbot)."""
    response = (
        supabase.table("articles")
        .select("id_wp, title, url, published_at")
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data


@router.get("/admin/stats")
def get_admin_stats():
    """Statistik ringkas: total artikel/chunk, waktu scraping terakhir, kategori
    terbanyak, dan rasio like/dislike dari feedback -- buat dashboard /admin."""

    total_articles = (
        supabase.table("articles").select("id_wp", count="exact").execute().count
    )
    total_chunks = (
        supabase.table("article_chunks").select("id", count="exact").execute().count
    )

    last_scrape_resp = (
        supabase.table("articles")
        .select("scraped_at")
        .order("scraped_at", desc=True)
        .limit(1)
        .execute()
    )
    last_scrape_at = last_scrape_resp.data[0]["scraped_at"] if last_scrape_resp.data else None

    latest_pub_resp = (
        supabase.table("articles")
        .select("published_at")
        .order("published_at", desc=True)
        .limit(1)
        .execute()
    )
    latest_published_at = (
        latest_pub_resp.data[0]["published_at"] if latest_pub_resp.data else None
    )

    categories_resp = supabase.rpc("list_categories").execute()
    top_categories = (categories_resp.data or [])[:5]

    feedback_resp = supabase.table("feedback").select("rating").execute()
    feedback_rows = feedback_resp.data or []
    likes = sum(1 for r in feedback_rows if r["rating"] == "like")
    dislikes = sum(1 for r in feedback_rows if r["rating"] == "dislike")
    total_feedback = likes + dislikes
    like_ratio = round(likes / total_feedback * 100, 1) if total_feedback else None

    return {
        "total_articles": total_articles,
        "total_chunks": total_chunks,
        "last_scrape_at": last_scrape_at,
        "latest_article_published_at": latest_published_at,
        "top_categories": top_categories,
        "feedback": {
            "likes": likes,
            "dislikes": dislikes,
            "total": total_feedback,
            "like_ratio_percent": like_ratio,
        },
    }


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: str  # "like" atau "dislike"


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    if req.rating not in ("like", "dislike"):
        return {"ok": False, "error": "rating harus 'like' atau 'dislike'"}

    supabase.table("feedback").insert(
        {"question": req.question, "answer": req.answer, "rating": req.rating}
    ).execute()
    return {"ok": True}