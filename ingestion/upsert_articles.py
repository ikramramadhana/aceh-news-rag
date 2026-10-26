"""
Upsert artikel bersih (clean_data.json) ke tabel `articles` di Supabase.

Cara pakai:
    pip install supabase python-dotenv
    python upsert_articles.py

Butuh file .env di root project dengan:
    SUPABASE_URL=...
    SUPABASE_SERVICE_ROLE_KEY=...
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

INPUT_FILE = Path("../scraper/clean_data/clean_data.json")
BATCH_SIZE = 200

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"{INPUT_FILE} tidak ditemukan. Jalankan clean_html.py dulu di folder scraper."
        )

    with open(INPUT_FILE, encoding="utf-8") as f:
        articles = json.load(f)

    print(f"Total artikel yang akan di-upsert: {len(articles)}")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    rows = [
        {
            "id_wp": a["id_wp"],
            "title": a["title"],
            "content": a["content"],
            "excerpt": a["excerpt"],
            "url": a["url"],
            "categories": a["categories"],
            "published_at": a["published_at"],
            "published_at_gmt": a["published_at_gmt"],
        }
        for a in articles
    ]

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        supabase.table("articles").upsert(batch, on_conflict="id_wp").execute()
        print(f"Upsert batch {i // BATCH_SIZE + 1}: {len(batch)} artikel")

    print("Selesai upsert artikel.")


if __name__ == "__main__":
    main()
