# Multi-stage build — mengikuti pola Sesi 14.2 (FROM -> WORKDIR -> COPY ->
# RUN pip -> CMD), dibagi menjadi dua stage:
#   Stage 1 (embed-builder) — "mode" khusus membangun index embedding dari
#     knowledge base, TANPA menjalankan server. CSV knowledge base hanya hidup
#     di stage ini dan TIDAK pernah masuk ke image akhir.
#     - Bila embed/ sudah berisi artifact di build context: dipakai langsung
#       (tanpa memanggil embedding API).
#     - Bila belum: stage ini membuatnya; sediakan key langsung dari file .env
#       saat build (docker build tidak memiliki flag --env-file;
#       --secret id=...,src= adalah mekanisme baca-file setara):
#         docker build --secret id=GEMINI_API_KEY,src=.env \
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

# Secret diberikan sebagai file .env (format KEY=value maupun raw key didukung);
# nilai tidak pernah ter-bake ke layer/history image.
RUN --mount=type=secret,id=GEMINI_API_KEY \
    set -e; \
    SECRET_CONTENT="$(cat /run/secrets/GEMINI_API_KEY 2>/dev/null || true)"; \
    GEMINI_API_KEY="$(printf '%s\n' "$SECRET_CONTENT" | sed -n 's/^GEMINI_API_KEY=//p' | tail -n 1)"; \
    if [ -z "$GEMINI_API_KEY" ]; then \
        GEMINI_API_KEY="$(printf '%s' "$SECRET_CONTENT" | tr -d '\r\n')"; \
    fi; \
    GEMINI_API_KEY="$(printf '%s' "$GEMINI_API_KEY" | sed -e 's/^"//' -e 's/"$//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"; \
    if [ ! -f embed/embedding.bin ] || [ ! -f embed/preprocess_knowledge.parquet ]; then \
        if [ -z "$GEMINI_API_KEY" ]; then \
            echo "ERROR: embed artifacts tidak ada di build context, dan GEMINI_API_KEY tidak tersedia." >&2; \
            echo "       Build dengan: docker build --secret id=GEMINI_API_KEY,src=.env -t it-helpdesk-assistant ." >&2; \
            exit 1; \
        fi; \
    fi; \
    if [ -z "$GEMINI_API_KEY" ]; then GEMINI_API_KEY="build-placeholder-key"; fi; \
    export GEMINI_API_KEY; \
    python -c "import app.rag as rag; rag.init_rag()"

# ── Stage 2: serving ────────────────────────────────────────────────────────
FROM python:3.14-slim

WORKDIR /app

# Copy requirements.txt terlebih dahulu, lalu install dependencies
# (praktik yang baik agar Docker layer caching bekerja optimal)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code + data yang dibutuhkan saat runtime.
# Hanya file essential — tanpa README, pyproject, uv.lock, .env, .git, .venv,
# dan tanpa data/it_helpdesk_knowledge_base.csv (digantikan index embedding).
COPY app/ ./app/
COPY data/mock_tickets.csv ./data/mock_tickets.csv
COPY --from=embed-builder /build/embed/embedding.bin ./embed/embedding.bin
COPY --from=embed-builder /build/embed/preprocess_knowledge.parquet ./embed/preprocess_knowledge.parquet

# Port yang digunakan: 8000 (sesuai README)
EXPOSE 8000

# Menjalankan aplikasi FastAPI menggunakan uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
