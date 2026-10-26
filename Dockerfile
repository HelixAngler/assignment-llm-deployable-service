# 🔧 TODO: lengkapi Dockerfile berikut mengikuti pola yang sudah dipelajari
# di Sesi 14.2 (FROM python -> WORKDIR -> COPY -> RUN pip -> CMD).
#
# Multi-stage build:
#   Stage 1 (embed-builder) — "mode" khusus membangun index embedding dari
#     knowledge base, TANPA menjalankan server. CSV knowledge base hanya hidup
#     di stage ini dan TIDAK pernah masuk ke image akhir.
#     - Bila embed/ sudah berisi artifact di build context: dipakai langsung
#       (tanpa memanggil embedding API).
#     - Bila belum: stage ini membuatnya; sediakan key saat build:
#         docker build --secret id=GEMINI_API_KEY,env=GEMINI_API_KEY \
#           -t it-helpdesk-assistant .
#   Stage 2 (serving) — python:3.14-slim bersih; hanya file essential yang
#     di-copy: app/, data/mock_tickets.csv, dan index embedding hasil stage 1.

# ── Stage 1: builder embedding ──────────────────────────────────────────────
FROM python:3.14-slim AS embed-builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY data/it_helpdesk_knowledge_base.csv ./data/it_helpdesk_knowledge_base.csv
COPY embed/ ./embed/

RUN --mount=type=secret,id=GEMINI_API_KEY \
    if [ ! -f embed/embedding.bin ] || [ ! -f embed/preprocess_knowledge.parquet ]; then \
        if [ ! -f /run/secrets/GEMINI_API_KEY ]; then \
            echo "ERROR: embed artifacts tidak ada di build context, dan secret GEMINI_API_KEY tidak diberikan." >&2; \
            echo "       Build dengan: docker build --secret id=GEMINI_API_KEY,env=GEMINI_API_KEY -t it-helpdesk-assistant ." >&2; \
            exit 1; \
        fi; \
    fi && \
    GEMINI_API_KEY="$(cat /run/secrets/GEMINI_API_KEY 2>/dev/null || echo build-placeholder-key)" \
    python -c "import app.rag as rag; rag.init_rag()"

# ── Stage 2: serving ────────────────────────────────────────────────────────
FROM python:3.14-slim

WORKDIR /app

# TODO: copy requirements.txt terlebih dahulu, lalu install dependencies
# (praktik yang baik agar Docker layer caching bekerja optimal)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# TODO: copy seluruh source code aplikasi ke dalam container
# Hanya file essential — tanpa README, pyproject, uv.lock, .env, .git, .venv,
# dan tanpa data/it_helpdesk_knowledge_base.csv (digantikan index embedding).
COPY app/ ./app/
COPY data/mock_tickets.csv ./data/mock_tickets.csv
COPY --from=embed-builder /build/embed/embedding.bin ./embed/embedding.bin
COPY --from=embed-builder /build/embed/preprocess_knowledge.parquet ./embed/preprocess_knowledge.parquet

# TODO: tentukan port yang akan digunakan (misal 8000) dan expose port tersebut
EXPOSE 8000

# TODO: tentukan CMD untuk menjalankan aplikasi FastAPI menggunakan uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
