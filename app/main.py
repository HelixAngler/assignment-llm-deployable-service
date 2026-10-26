"""
Entry point aplikasi FastAPI — IT Helpdesk Assistant.

Alur endpoint utama:
  1. Menerima pertanyaan/permintaan dari user
  2. Meneruskan ke router (router.py) untuk menentukan intent
  3. Router memanggil RAG (rag.py) atau tool (tools.py) sesuai intent
  4. Mengembalikan response terstruktur ke client
"""
import logging
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import asyncio

from app.router import handle_query
import app.rag as rag

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="IT Helpdesk Assistant API")


class AskRequest(BaseModel):
    query: str


class AskResponse(BaseModel):
    status: str
    intent: str
    data: str


@app.get("/health")
async def health():
    """Endpoint sederhana untuk memastikan service berjalan."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    """
    Endpoint utama. Menerima pertanyaan bebas dari user (bisa berupa
    pertanyaan informasi/kebijakan ATAU permintaan cek status tiket),
    lalu meneruskannya ke router untuk diproses.

    # TODO: tambahkan error handling untuk kondisi LLM gagal merespons
    # atau intent tidak dapat dikenali (lihat panduan error handling di Sesi 13.4)
    """
    # result = await handle_query(request.query)
    # return AskResponse(**result)
    try:
        result = await handle_query(request.query)
        return AskResponse(**result)
    except Exception:
        logger.exception("Gagal memproses permintaan: %r", request.query)
        return AskResponse(
            status="error",
            intent="unknown",
            data=(
                "Maaf, terjadi kesalahan saat memproses permintaan Anda. "
                "Silakan coba lagi beberapa saat lagi."
            ),
        )



if __name__ == '__main__':
    load_dotenv()
    rag.init_rag()
    uvicorn.run(app, host="0.0.0.0", port=8080)
