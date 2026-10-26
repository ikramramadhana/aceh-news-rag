"""
Scraper berita Humas Aceh (humas.acehprov.go.id) via WordPress REST API.

Mengambil semua post dari tanggal pelantikan Mualem (12 Feb 2025) sampai sekarang,
lengkap dengan mapping kategori, lalu disimpan sebagai file JSON mentah
(satu file per halaman) di folder output.

Cara pakai:
    python fetch_posts.py

Output:
    raw_data/posts_page_1.json, posts_page_2.json, ...
    raw_data/categories.json
"""

import json
import time
from pathlib import Path

import requests

BASE_URL = "https://humas.acehprov.go.id/wp-json/wp/v2"
START_DATE = "2025-02-12T00:00:00"  # tanggal pelantikan Mualem
OUTPUT_DIR = Path("raw_data")
PER_PAGE = 100
REQUEST_DELAY_SECONDS = 1.0  # jeda antar request, sopan ke server
TIMEOUT_SECONDS = 30


def fetch_categories() -> dict:
    """Ambil semua kategori dan buat mapping {id: name}."""
    categories = {}
    page = 1
    while True:
        resp = requests.get(
            f"{BASE_URL}/categories",
            params={"per_page": 100, "page": page},
            timeout=TIMEOUT_SECONDS,
        )
        if resp.status_code == 400:
            # WordPress balikin 400 kalau page melebihi total halaman
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


def fetch_all_posts(after: str) -> list[dict]:
    """Ambil semua post yang terbit setelah tanggal `after` (ISO 8601)."""
    all_posts = []
    page = 1

    while True:
        resp = requests.get(
            f"{BASE_URL}/posts",
            params={
                "per_page": PER_PAGE,
                "page": page,
                "after": after,
                "orderby": "date",
                "order": "asc",
            },
            timeout=TIMEOUT_SECONDS,
        )

        if resp.status_code == 400:
            # Sudah lewat total halaman yang tersedia -> berhenti
            print(f"Halaman {page}: tidak ada data lagi (400), berhenti.")
            break

        resp.raise_for_status()
        posts = resp.json()

        if not posts:
            print(f"Halaman {page}: kosong, berhenti.")
            break

        total_pages = resp.headers.get("X-WP-TotalPages")
        total_posts = resp.headers.get("X-WP-Total")
        print(
            f"Halaman {page}/{total_pages} — {len(posts)} post "
            f"(total keseluruhan: {total_posts})"
        )

        # simpan mentah per halaman, biar kalau crash di tengah nggak hilang semua
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_DIR / f"posts_page_{page}.json", "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)

        all_posts.extend(posts)

        if total_pages and page >= int(total_pages):
            break

        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    return all_posts


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Mengambil daftar kategori...")
    categories = fetch_categories()
    with open(OUTPUT_DIR / "categories.json", "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)
    print(f"Total kategori: {len(categories)}")

    print(f"\nMengambil semua post sejak {START_DATE}...")
    posts = fetch_all_posts(after=START_DATE)
    print(f"\nSelesai. Total post yang berhasil diambil: {len(posts)}")
    print(f"Data mentah tersimpan di folder: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
