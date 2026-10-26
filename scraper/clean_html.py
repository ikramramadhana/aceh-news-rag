"""
Membersihkan dan menggabungkan hasil scraping mentah dari fetch_posts.py.

Baca semua raw_data/posts_page_*.json + raw_data/categories.json,
strip HTML dari content, petakan id kategori -> nama, lalu simpan
sebagai satu file clean_data.json siap dipakai untuk chunking/embedding.

Cara pakai:
    pip install beautifulsoup4
    python clean_html.py

Output:
    clean_data/clean_data.json
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

RAW_DIR = Path("raw_data")
OUTPUT_DIR = Path("clean_data")
OUTPUT_FILE = OUTPUT_DIR / "clean_data.json"


def strip_html(html: str) -> str:
    """Ubah HTML jadi teks polos, rapikan spasi/baris kosong berlebih."""
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)  # rapikan baris kosong berlebih
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def load_categories() -> dict:
    path = RAW_DIR / "categories.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} tidak ditemukan. Jalankan fetch_posts.py dulu."
        )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # key di JSON otomatis jadi string, kembalikan sebagai int biar konsisten
    return {int(k): v for k, v in data.items()}


def load_all_raw_posts() -> list[dict]:
    pages = sorted(
        RAW_DIR.glob("posts_page_*.json"),
        key=lambda p: int(re.search(r"\d+", p.stem).group()),
    )
    if not pages:
        raise FileNotFoundError(
            f"Tidak ada file posts_page_*.json di {RAW_DIR}. Jalankan fetch_posts.py dulu."
        )

    all_posts = []
    for page_path in pages:
        with open(page_path, encoding="utf-8") as f:
            all_posts.extend(json.load(f))
    return all_posts


def clean_post(post: dict, categories: dict) -> dict:
    return {
        "id_wp": post["id"],
        "title": strip_html(post["title"]["rendered"]),
        "content": strip_html(post["content"]["rendered"]),
        "excerpt": strip_html(post["excerpt"]["rendered"]),
        "url": post["link"],
        "published_at": post["date"],  # sudah dalam waktu lokal (WIB)
        "published_at_gmt": post["date_gmt"],
        "categories": [
            categories.get(cid, f"unknown_{cid}") for cid in post.get("categories", [])
        ],
    }


def main():
    print("Memuat kategori...")
    categories = load_categories()

    print("Memuat semua halaman post mentah...")
    raw_posts = load_all_raw_posts()
    print(f"Total post mentah: {len(raw_posts)}")

    print("Membersihkan HTML dan memetakan kategori...")
    cleaned = [clean_post(p, categories) for p in raw_posts]

    # buang duplikat kalau ada (berdasarkan id_wp), jaga-jaga overlap antar halaman
    seen = {}
    for post in cleaned:
        seen[post["id_wp"]] = post
    deduped = list(seen.values())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)

    print(f"\nSelesai. Total artikel bersih: {len(deduped)}")
    print(f"Tersimpan di: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
