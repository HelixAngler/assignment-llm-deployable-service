# IT Helpdesk Assistant — Starter Repository

Starter repository untuk Assignment 4: End-to-End RAG & AI Agent Development.

## Struktur Project

```
app/
├── main.py       # Entry point FastAPI, berisi endpoint /ask
├── router.py     # Intent detection + routing ke RAG atau tool call
├── rag.py        # Modul RAG: embedding, FAISS, semantic search, LLM answer
└── tools.py      # Modul tool call: pengecekan status tiket

data/
├── it_helpdesk_knowledge_base.csv   # Knowledge base untuk RAG
└── mock_tickets.csv                 # Data mock untuk tool call
```

## TODO Peserta

Seluruh bagian yang perlu diimplementasikan ditandai dengan komentar `# TODO`
atau `# 🔧 TODO` di dalam masing-masing file. Ikuti urutan berikut:

1. `app/rag.py` — implementasikan `build_index()`, `semantic_search()`, `answer_from_knowledge_base()`
2. `app/tools.py` — implementasikan `get_ticket_status()`
3. `app/router.py` — implementasikan `detect_intent()` dan `extract_ticket_id()`
4. `Dockerfile` — lengkapi konfigurasi container

## Menjalankan Secara Lokal (tanpa Docker)

```bash
pip install -r requirements.txt
cp .env.example .env   # lalu isi GEMINI_API_KEY di dalam .env
uvicorn app.main:app --reload
```

## Menjalankan dengan Docker

Build memakai multi-stage: stage builder (`embed-builder`) membangun index
embedding dari knowledge base **tanpa menjalankan server** — CSV knowledge base
hanya hidup di stage itu dan tidak pernah masuk ke image akhir. Stage serving
(`python:3.14-slim`) hanya menerima file essential: `app/`, `data/mock_tickets.csv`,
dan index embedding hasil stage builder.

```bash
# Mode 1 — embed/ sudah berisi artifact (hasil run lokal atau build sebelumnya):
docker build -t it-helpdesk-assistant .

# Mode 2 — embed/ masih kosong (mis. fresh clone): stage builder membaca
# GEMINI_API_KEY langsung dari file .env (tanpa mengekspor apa pun ke shell):
docker build --secret id=GEMINI_API_KEY,src=.env -t it-helpdesk-assistant .

# Build dengan seluruh parameter build terisi (key + model embedding):
docker build \
  --secret id=GEMINI_API_KEY,src=.env \
  --build-arg GEMINI_EMBEDDING_MODEL=gemini-embedding-001 \
  -t it-helpdesk-assistant .

docker run -p 8000:8000 --env-file .env it-helpdesk-assistant
```

Tanpa artifact maupun secret, build gagal cepat dengan pesan yang menjelaskan
kedua opsi di atas. API key tidak pernah ter-bake ke dalam image
(hanya masuk lewat `--env-file` saat runtime).

### Konfigurasi Model

Model Gemini dapat di-override lewat environment variable (default ada di
`app/rag.py`):

| Variable | Default | Kapan dipakai |
|---|---|---|
| `GEMINI_MODEL` | `gemini-3.6-flash` | Runtime — generasi jawaban & intent detection |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Runtime (query embedding) & build time (`--build-arg`) |

Isi di `.env` untuk `docker run --env-file .env` / `uvicorn`, atau gunakan
`-e`/`--build-arg` sesuai kebutuhan.

## Menguji Endpoint

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "berapa jatah cuti tahunan saya?"}'
```

_Lengkapi bagian dokumentasi ini sesuai instruksi pada Assignment Brief (Langkah 10 — Membuat Dokumentasi)._
