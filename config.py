import os
from pathlib import Path

from dotenv import load_dotenv

# .env ada di root project (satu level di atas folder backend/)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768
CHAT_MODEL = "gemini-3.1-flash-lite"

DEFAULT_MATCH_COUNT = 5

# Chunk dianggap tidak relevan kalau skor kemiripannya lebih rendah dari
# (skor teratas - margin ini). Makin kecil = makin ketat.
# Angka awal ini perkiraan; tuning lewat log "[retrieval]" di terminal uvicorn.
SOURCE_SIMILARITY_MARGIN = 0.08

# Chunk dengan skor kemiripan di bawah ini dianggap tidak relevan sama
# sekali, berapa pun skor tertinggi di hasil pencarian. Ini jaring pengaman
# khusus buat kasus filter kategori/tanggal: kalau semua hasil di dalam
# kategori/tanggal itu skornya rendah (nggak nyambung ke pertanyaan), semua
# dibuang -> chatbot jujur bilang "tidak ditemukan", bukan maksa jawab.
MIN_ABSOLUTE_SIMILARITY = 0.5