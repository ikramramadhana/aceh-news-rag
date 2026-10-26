"""
Generate embedding untuk tiap chunk (chunks.json) pakai Gemini Embedding API,
lalu upsert ke tabel `article_chunks` (kolom `embedding` bertipe vector) di Supabase.

Cara pakai:
    pip install google-genai supabase python-dotenv
    python embed_and_upsert_chunks.py

Butuh file .env di root project dengan:
    GEMINI_API_KEY=...
    SUPABASE_URL=...
    SUPABASE_SERVICE_ROLE_KEY=...

Catatan:
    - Jalankan upsert_articles.py DULU sebelum ini, karena article_chunks
      punya foreign key ke articles.id_wp.
    - Script ini resume-safe: chunk yang sudah pernah berhasil di-upsert
      akan dilewati kalau dijalankan ulang (dicek dari progress file).
"""

import json
import os
import time
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

INPUT_FILE = Path("chunks/chunks.json")
PROGRESS_FILE = Path("chunks/embed_progress.json")

EMBEDDING_MODEL = "gemini-embedding-001"
BATCH_SIZE_UPSERT = 50
REQUEST_DELAY_SECONDS = 0.5  # jaga-jaga rate limit free tier
MAX_RETRIES = 3

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def load_progress() -> set:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_progress(done_ids: set):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(done_ids), f)


class DailyQuotaExceeded(Exception):
    """Kena limit harian free tier — tidak ada gunanya di-retry sekarang."""


def embed_text(text: str) -> list[float]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = gemini_client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=768,
                ),
            )
            return result.embeddings[0].values
        except Exception as e:
            msg = str(e)
            is_daily_quota = "PerDay" in msg or "free_tier_requests" in msg
            if is_daily_quota:
                raise DailyQuotaExceeded(
                    "Limit harian free tier Gemini embedding sudah habis."
                ) from e
            wait = 2**attempt
            print(f"  Gagal embed (percobaan {attempt}/{MAX_RETRIES}): {e}. Retry {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Gagal embed setelah {MAX_RETRIES} percobaan: {text[:50]}...")


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"{INPUT_FILE} tidak ditemukan. Jalankan chunker.py dulu.")

    with open(INPUT_FILE, encoding="utf-8") as f:
        chunks = json.load(f)

    done_ids = load_progress()
    pending = [c for c in chunks if c["chunk_id"] not in done_ids]

    print(f"Total chunk: {len(chunks)}, sudah selesai: {len(done_ids)}, sisa: {len(pending)}")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    buffer = []
    try:
        for i, chunk in enumerate(pending, start=1):
            embedding = embed_text(chunk["chunk_text"])

            buffer.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "article_id": chunk["article_id"],
                    "chunk_index": chunk["chunk_index"],
                    "chunk_text": chunk["chunk_text"],
                    "title": chunk["title"],
                    "url": chunk["url"],
                    "published_at": chunk["published_at"],
                    "categories": chunk["categories"],
                    "embedding": embedding,
                }
            )
            done_ids.add(chunk["chunk_id"])

            if len(buffer) >= BATCH_SIZE_UPSERT or i == len(pending):
                supabase.table("article_chunks").upsert(
                    buffer, on_conflict="chunk_id"
                ).execute()
                save_progress(done_ids)
                print(f"Upsert {i}/{len(pending)} chunk...")
                buffer = []

            time.sleep(REQUEST_DELAY_SECONDS)
    except DailyQuotaExceeded:
        if buffer:
            supabase.table("article_chunks").upsert(
                buffer, on_conflict="chunk_id"
            ).execute()
            save_progress(done_ids)
        sisa = len(chunks) - len(done_ids)
        print(
            f"\nBerhenti: limit harian free tier Gemini embedding habis.\n"
            f"Progress tersimpan — {len(done_ids)}/{len(chunks)} chunk selesai, sisa {sisa}.\n"
            f"Tunggu reset kuota (biasanya tengah malam Pacific Time / siang-sore WIB besok), "
            f"lalu jalankan ulang script ini — otomatis lanjut dari sini."
        )
        return

    print("Selesai. Semua chunk sudah di-embed dan di-upsert.")


if __name__ == "__main__":
    main()