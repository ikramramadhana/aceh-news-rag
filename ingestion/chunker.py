"""
Memecah artikel bersih (clean_data.json) menjadi chunk-chunk kecil,
tiap chunk membawa metadata (judul, url, tanggal, kategori) untuk
keperluan sitasi dan filtering saat retrieval.

Cara pakai:
    python chunker.py

Input:
    ../scraper/clean_data/clean_data.json

Output:
    chunks/chunks.json
"""

import json
from pathlib import Path

INPUT_FILE = Path("../scraper/clean_data/clean_data.json")
OUTPUT_DIR = Path("chunks")
OUTPUT_FILE = OUTPUT_DIR / "chunks.json"

# Target ukuran chunk dalam jumlah kata (perkiraan kasar, bukan token pasti).
# Berita rata-rata pendek, jadi kebanyakan artikel akan jadi 1 chunk saja.
MAX_WORDS_PER_CHUNK = 350
OVERLAP_WORDS = 50


def split_into_chunks(text: str, max_words: int, overlap: int) -> list[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text.strip()]

    chunks = []
    start = 0
    while start < len(words):
        end = start + max_words
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start = end - overlap  # mundur sedikit biar ada overlap konteks
    return chunks


def build_chunks(article: dict) -> list[dict]:
    text_parts = split_into_chunks(
        article["content"], MAX_WORDS_PER_CHUNK, OVERLAP_WORDS
    )

    chunks = []
    for i, part in enumerate(text_parts):
        chunks.append(
            {
                "chunk_id": f"{article['id_wp']}_{i}",
                "article_id": article["id_wp"],
                "chunk_index": i,
                "chunk_text": part,
                "title": article["title"],
                "url": article["url"],
                "published_at": article["published_at"],
                "categories": article["categories"],
            }
        )
    return chunks


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"{INPUT_FILE} tidak ditemukan. Jalankan clean_html.py dulu di folder scraper."
        )

    with open(INPUT_FILE, encoding="utf-8") as f:
        articles = json.load(f)

    print(f"Total artikel: {len(articles)}")

    all_chunks = []
    for article in articles:
        all_chunks.extend(build_chunks(article))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    avg_chunks = len(all_chunks) / len(articles) if articles else 0
    print(f"Total chunk dihasilkan: {len(all_chunks)}")
    print(f"Rata-rata chunk per artikel: {avg_chunks:.2f}")
    print(f"Tersimpan di: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
