"""
Pipeline harian: scrape HANYA berita baru sejak run terakhir, bersihkan,
chunk, embed, dan upsert langsung ke Supabase. Dirancang untuk dijalankan
otomatis tiap hari (lihat run_daily.bat untuk Windows Task Scheduler).

Beda dengan fetch_posts.py (yang scrape semua histori dari awal), script ini
cuma proses artikel yang published SETELAH tanggal terakhir kali dijalankan
-- jadi cepat dan hemat kuota embedding harian.

Cara pakai manual:
    python daily_pipeline.py

State disimpan di:
    state.json -> {"last_published_at": "..."}
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from google import genai
from google.genai import types
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

BASE_URL = "https://humas.acehprov.go.id/wp-json/wp/v2"
STATE_FILE = Path(__file__).resolve().parent / "state.json"
LOG_FILE = Path(__file__).resolve().parent / "run_log.txt"

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768
MAX_WORDS_PER_CHUNK = 350
OVERLAP_WORDS = 50
REQUEST_DELAY_SECONDS = 0.5

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    # Kalau belum pernah jalan, default ke tanggal pelantikan Mualem.
    # Harusnya nggak kepakai kalau kamu udah scrape manual sebelumnya --
    # ganti last_published_at di state.json ke tanggal artikel terbaru
    # yang udah kamu punya di database.
    return {"last_published_at": "2025-02-12T00:00:00"}


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def strip_html(html: str) -> str:
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def fetch_categories() -> dict:
    categories = {}
    page = 1
    while True:
        resp = requests.get(
            f"{BASE_URL}/categories", params={"per_page": 100, "page": page}, timeout=30
        )
        if resp.status_code == 400:
            break
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        for cat in data:
            categories[cat["id"]] = cat["name"]
        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)
    return categories


def fetch_new_posts(after: str) -> list[dict]:
    all_posts = []
    page = 1
    while True:
        resp = requests.get(
            f"{BASE_URL}/posts",
            params={
                "per_page": 100,
                "page": page,
                "after": after,
                "orderby": "date",
                "order": "asc",
            },
            timeout=30,
        )
        if resp.status_code == 400:
            break
        resp.raise_for_status()
        posts = resp.json()
        if not posts:
            break
        all_posts.extend(posts)
        total_pages = resp.headers.get("X-WP-TotalPages")
        if total_pages and page >= int(total_pages):
            break
        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)
    return all_posts


def split_into_chunks(text: str) -> list[str]:
    words = text.split()
    if len(words) <= MAX_WORDS_PER_CHUNK:
        return [text.strip()]
    chunks = []
    start = 0
    while start < len(words):
        end = start + MAX_WORDS_PER_CHUNK
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = end - OVERLAP_WORDS
    return chunks


def embed_text(text: str) -> list[float]:
    result = gemini_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    return result.embeddings[0].values


def main():
    state = load_state()
    after = state["last_published_at"]

    log(f"Mulai pipeline harian. Cek berita baru sejak {after}...")

    categories_map = fetch_categories()
    raw_posts = fetch_new_posts(after)

    if not raw_posts:
        log("Tidak ada berita baru. Selesai.")
        return

    log(f"Ditemukan {len(raw_posts)} berita baru.")

    latest_published = after

    for post in raw_posts:
        article = {
            "id_wp": post["id"],
            "title": strip_html(post["title"]["rendered"]),
            "content": strip_html(post["content"]["rendered"]),
            "excerpt": strip_html(post["excerpt"]["rendered"]),
            "url": post["link"],
            "published_at": post["date"],
            "published_at_gmt": post["date_gmt"],
            "categories": [
                categories_map.get(cid, f"unknown_{cid}")
                for cid in post.get("categories", [])
            ],
        }

        # upsert artikel
        supabase.table("articles").upsert(
            {
                "id_wp": article["id_wp"],
                "title": article["title"],
                "content": article["content"],
                "excerpt": article["excerpt"],
                "url": article["url"],
                "categories": article["categories"],
                "published_at": article["published_at"],
                "published_at_gmt": article["published_at_gmt"],
            },
            on_conflict="id_wp",
        ).execute()

        # chunk + embed + upsert chunk
        text_parts = split_into_chunks(article["content"])
        chunk_rows = []
        for i, part in enumerate(text_parts):
            embedding = embed_text(part)
            chunk_rows.append(
                {
                    "chunk_id": f"{article['id_wp']}_{i}",
                    "article_id": article["id_wp"],
                    "chunk_index": i,
                    "chunk_text": part,
                    "title": article["title"],
                    "url": article["url"],
                    "published_at": article["published_at"],
                    "categories": article["categories"],
                    "embedding": embedding,
                }
            )
            time.sleep(REQUEST_DELAY_SECONDS)

        supabase.table("article_chunks").upsert(
            chunk_rows, on_conflict="chunk_id"
        ).execute()

        log(f"  Selesai: [{article['id_wp']}] {article['title'][:60]}")

        if article["published_at"] > latest_published:
            latest_published = article["published_at"]

    save_state({"last_published_at": latest_published})
    log(f"Pipeline selesai. State diupdate ke {latest_published}.")


if __name__ == "__main__":
    main()