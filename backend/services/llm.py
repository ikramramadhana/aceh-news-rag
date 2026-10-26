import json
import re

from google.genai import types

from config import CHAT_MODEL
from gemini_client import client

SYSTEM_INSTRUCTION = """\
Kamu adalah asisten tanya-jawab seputar berita pemerintahan Aceh.

Aturan:
1. Jawab HANYA berdasarkan potongan berita yang diberikan di bawah. Jangan pakai pengetahuan di luar itu.
2. Kalau potongan berita yang diberikan tidak cukup untuk menjawab pertanyaan, katakan terus terang bahwa kamu tidak menemukan informasinya di berita yang tersedia. Jangan mengarang.
3. Jawab dengan bahasa Indonesia yang natural, ringkas, dan jelas.
4. JANGAN mencantumkan link/URL di dalam jawaban teks kamu — sumber akan ditampilkan terpisah oleh sistem.
5. Kalau ada beberapa berita yang membahas topik sama dari waktu berbeda, prioritaskan informasi dari berita yang lebih baru.
6. JANGAN pakai format markdown sama sekali (tanpa **tebal**, tanpa _miring_, tanpa heading #). Tulis sebagai teks polos. Kalau perlu menyebutkan beberapa poin, gunakan format "1. ... 2. ... 3. ..." dengan baris baru biasa, bukan bullet bertanda bintang.
7. Kalau ada riwayat percakapan, fokus pada topik yang sedang dibicarakan di riwayat itu. JANGAN memasukkan berita yang tidak berkaitan dengan topik tersebut, meskipun berita itu ada di potongan berita yang diberikan.
"""

FALLBACK_ERROR_MESSAGE = (
    "Maaf, terjadi kendala saat membuat jawaban. Coba tanya ulang "
    "dengan kalimat yang sedikit berbeda."
)


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(
            f"[Berita {i}] ({c['published_at']}) {c['title']}\n{c['chunk_text']}"
        )
    return "\n\n".join(parts)


def build_history_text(history: list[dict] | None) -> str:
    if not history:
        return ""
    lines = []
    for h in history:
        speaker = "User" if h["role"] == "user" else "Asisten"
        lines.append(f"{speaker}: {h['content']}")
    return "Riwayat percakapan sebelumnya:\n" + "\n".join(lines) + "\n\n"


def build_prompt(
    question: str,
    chunks: list[dict],
    history: list[dict] | None,
    standalone_question: str | None = None,
) -> str:
    """Susun prompt akhir. Kalau pertanyaan sudah ditulis ulang jadi versi
    mandiri (misal 'gimana kelanjutannya?' -> 'Bagaimana kelanjutan Pergub JKA?'),
    versi mandirinya ikut dikirim supaya model tahu persis maksudnya."""
    question_line = f"Pertanyaan: {question}"
    if standalone_question and standalone_question.strip() != question.strip():
        question_line += f"\n(Maksud pertanyaan ini: {standalone_question})"
    return f"{build_history_text(history)}{build_context(chunks)}\n\n{question_line}"


def generate_answer(
    question: str,
    chunks: list[dict],
    history: list[dict] | None = None,
    standalone_question: str | None = None,
) -> str:
    if not chunks:
        return (
            "Maaf, saya tidak menemukan berita yang relevan dengan pertanyaan itu "
            "di data yang saya miliki."
        )

    prompt = build_prompt(question, chunks, history, standalone_question)

    try:
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
        )
        answer = (response.text or "").strip()
    except Exception:
        return FALLBACK_ERROR_MESSAGE

    if not answer:
        return FALLBACK_ERROR_MESSAGE

    # safety net: buang markdown yang mungkin masih lolos dari instruksi
    answer = re.sub(r"\*\*(.+?)\*\*", r"\1", answer)  # **bold**
    answer = re.sub(r"__(.+?)__", r"\1", answer)  # __bold__
    answer = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", answer)  # *italic*
    answer = re.sub(r"^#{1,6}\s+", "", answer, flags=re.MULTILINE)  # # heading

    return answer


def rewrite_query(question: str, history: list[dict] | None) -> str:
    """Ubah pertanyaan follow-up (misal 'terus gimana?') jadi pertanyaan
    mandiri yang mengandung konteks, supaya retrieval tetap akurat."""
    if not history:
        return question

    history_text = build_history_text(history)
    prompt = (
        f"{history_text}"
        f"Pertanyaan terbaru: {question}\n\n"
        "Tulis ulang pertanyaan terbaru itu menjadi SATU pertanyaan mandiri "
        "(standalone) dalam Bahasa Indonesia, dengan aturan:\n"
        "1. Sebutkan secara EKSPLISIT nama topik, orang, peraturan, atau lokasi "
        "konkret dari riwayat percakapan yang dimaksud. JANGAN pernah memakai "
        "frasa umum seperti 'topik yang telah dibahas', 'hal tersebut', atau "
        "'beberapa topik'.\n"
        "2. Kalau jawaban asisten sebelumnya membahas beberapa topik dan "
        "pertanyaan terbaru tidak menyebut topik tertentu, sebutkan semua topik "
        "itu satu per satu secara konkret.\n"
        "3. Jangan tambahkan informasi baru yang tidak ada di percakapan.\n"
        "4. Kalau pertanyaan terbaru sudah mandiri, kembalikan apa adanya.\n"
        "Balas HANYA dengan pertanyaan hasil tulis ulang, tanpa penjelasan atau "
        "tanda kutip."
    )

    try:
        response = client.models.generate_content(model=CHAT_MODEL, contents=prompt)
        rewritten = (response.text or "").strip()
        # kalau kosong (model nggak balikin teks), pakai pertanyaan asli
        return rewritten or question
    except Exception:
        return question


def generate_answer_stream(
    question: str,
    chunks: list[dict],
    history: list[dict] | None = None,
    standalone_question: str | None = None,
):
    """Versi streaming: yield potongan teks jawaban satu per satu."""
    if not chunks:
        yield (
            "Maaf, saya tidak menemukan berita yang relevan dengan pertanyaan itu "
            "di data yang saya miliki."
        )
        return

    prompt = build_prompt(question, chunks, history, standalone_question)

    try:
        stream = client.models.generate_content_stream(
            model=CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
        )
        got_any_text = False
        for chunk in stream:
            if chunk.text:
                got_any_text = True
                yield chunk.text
        if not got_any_text:
            yield FALLBACK_ERROR_MESSAGE
    except Exception:
        yield FALLBACK_ERROR_MESSAGE


def generate_suggestions(question: str, answer: str, chunks: list[dict]) -> list[str]:
    """Buat 2-3 pertanyaan lanjutan yang relevan, berdasarkan jawaban & berita yang dipakai."""
    if not chunks:
        return []

    context = build_context(chunks)
    prompt = (
        f"{context}\n\n"
        f"Pertanyaan sebelumnya: {question}\n"
        f"Jawaban yang sudah diberikan: {answer}\n\n"
        "Berdasarkan berita di atas, buat 3 pertanyaan lanjutan singkat yang "
        "relevan dan menarik untuk ditanyakan selanjutnya (Bahasa Indonesia, "
        "masing-masing maksimal 12 kata). Balas HANYA dalam format JSON array "
        'of strings, tanpa penjelasan tambahan. Contoh: '
        '["Pertanyaan 1?", "Pertanyaan 2?", "Pertanyaan 3?"]'
    )

    try:
        response = client.models.generate_content(model=CHAT_MODEL, contents=prompt)
        text = (response.text or "").strip()
    except Exception:
        return []  # gagal generate suggestions bukan hal kritis, skip aja

    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)

    try:
        suggestions = json.loads(text)
        if isinstance(suggestions, list):
            return [str(s) for s in suggestions][:3]
    except (json.JSONDecodeError, TypeError):
        pass
    return []