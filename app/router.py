"""
Router — menentukan apakah query user butuh RAG (informasi/kebijakan)
atau tool call (aksi spesifik, misal cek status tiket).

Pola ini mengikuti workflow router yang sudah dipelajari di Sesi 12.4:
  user input -> intent detection -> jika butuh data -> retrieval (RAG)
                                  -> jika butuh aksi -> tool call
"""

import os
import re

from google import genai

from app.rag import answer_from_knowledge_base
from app.tools import get_ticket_status

# 🔧 TODO: import LLM client di sini (Gemini AI API) untuk melakukan intent detection
_client = None

_HTTP_OPTIONS = genai.types.HttpOptions(
    retry_options=genai.types.HttpRetryOptions(
        attempts=3,
        initial_delay=1.0,
        max_delay=8.0,
    ),
)

_TICKET_ID_RE = re.compile(r"TICKET-\d+", re.IGNORECASE)
_TICKET_ACTION_RE = re.compile(
    r"(cek|periksa|lacak|status|update|tengok|lihat|cekkan)"
    r".{0,40}(tiket|ticket)"
    r"|(tiket|ticket).{0,20}(saya|berstatus|status)",
    re.IGNORECASE,
)


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=os.environ.get("GEMINI_API_KEY"),
            http_options=_HTTP_OPTIONS,
        )
    return _client


def _keyword_intent(query: str) -> str | None:
    """
    Heuristik berbasis keyword sebagai jalur hemat token:
    query yang secara eksplisit merujuk tiket tidak perlu memanggil LLM.
    Mengembalikan None bila tidak yakin (fallback ke LLM).
    """
    if _TICKET_ID_RE.search(query):
        return "ticket_status"
    if _TICKET_ACTION_RE.search(query):
        return "ticket_status"
    return None


async def detect_intent(query: str) -> str:
    """
    Menentukan intent dari query user. Harus mengembalikan salah satu:
      - "faq"           -> pertanyaan informasi/kebijakan, arahkan ke RAG
      - "ticket_status"  -> permintaan cek status tiket, arahkan ke tool call

    # TODO: implementasikan intent detection menggunakan LLM (structured prompt,
    # lihat Sesi 10.1) ATAU pendekatan sederhana berbasis keyword sebagai baseline
    # sebelum beralih ke pendekatan berbasis LLM.
    #
    # Contoh prompt yang bisa dipakai sebagai starting point:
    #
    #   "Klasifikasikan pertanyaan berikut ke dalam salah satu kategori:
    #    'faq' (pertanyaan informasi/kebijakan umum) atau
    #    'ticket_status' (permintaan mengecek status tiket tertentu).
    #    Jawab hanya dengan satu kata.
    #    Pertanyaan: {query}"
    """
    keyword_result = _keyword_intent(query)
    if keyword_result is not None:
        return keyword_result

    # Query ambigu — hanya di sinilah LLM dipanggil (hemat token).
    try:
        prompt = (
            "Klasifikasikan pertanyaan berikut ke dalam salah satu kategori:\n"
            "'faq' (pertanyaan informasi/kebijakan umum) atau\n"
            "'ticket_status' (permintaan mengecek status tiket tertentu).\n"
            "Jawab hanya dengan satu kata.\n"
            f"Pertanyaan: {query}"
        )
        response = _get_client().models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-3.6-flash"),
            contents=prompt,
        )
        answer = (response.text or "").strip().lower()
        if answer in ("faq", "ticket_status"):
            return answer
    except Exception:
        pass

    # Fallback terakhir: perlakukan sebagai pertanyaan informasi/kebijakan.
    return "faq"


async def handle_query(query: str) -> dict:
    """
    Fungsi utama yang dipanggil oleh endpoint /ask.
    Menjalankan intent detection, lalu merutekan ke RAG atau tool call yang sesuai.
    """
    intent = await detect_intent(query)

    if intent == "ticket_status":
        # 🔧 TODO: ekstrak ticket_id dari query (misal menggunakan regex
        # atau meminta LLM mengekstrak entitas ticket_id dari kalimat user)
        ticket_id = extract_ticket_id(query)
        data = get_ticket_status(ticket_id)
        return {"status": "success", "intent": "ticket_status", "data": data}

    elif intent == "faq":
        data = await answer_from_knowledge_base(query)
        return {"status": "success", "intent": "faq", "data": data}

    else:
        return {"status": "error", "intent": "unknown", "data": "Maaf, saya tidak memahami permintaan Anda."}


def extract_ticket_id(query: str) -> str:
    """
    # TODO: implementasikan ekstraksi ticket_id dari teks query.
    # Format ticket_id pada mock_tickets.csv adalah 'TICKET-XXXX'.
    """
    match = _TICKET_ID_RE.search(query)
    return match.group(0).upper() if match else ""
