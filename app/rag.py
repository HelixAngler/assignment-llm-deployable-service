"""
Modul RAG — mengubah knowledge base menjadi embedding, menyimpannya ke FAISS,
melakukan semantic search, lalu menghasilkan jawaban menggunakan LLM.

Alur ini serupa dengan yang sudah dibangun di Assignment 3 (Semantic Search &
LLM Application) dan Sesi 11 (Building a Simple RAG System) — di assignment ini,
alur tersebut dibungkus menjadi fungsi yang dipanggil oleh router.py.
"""

import os
from pathlib import Path
import pandas as pd
import numpy as np
import faiss
from google import genai  # sesuaikan dengan library Gemini API yang digunakan


DEFAULT_KNOWLEDGE_BASE_PATH = "data/it_helpdesk_knowledge_base.csv"
DEFAULT_PREPROCESS_KNOWLEDGE_BASE_PATH = "embed/preprocess_knowledge.parquet"
DEFAULT_INDEX_BASE_PATH = "embed/embedding.bin"

_client = None
_index = None
_documents = None
_df = None

def _init_client():
    global _client
    _client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
        http_options=genai.types.HttpOptions(
            retry_options=genai.types.HttpRetryOptions(
                attempts=3,
                initial_delay=1.0,
                max_delay=8.0,
            ),
        ),
    )


def _init_index():
    global _index, _df, _documents
    embed_path = os.environ.get("EMBEDDINGS_BASE_PATH") if os.environ.get("EMBEDDINGS_BASE_PATH") is not None else DEFAULT_INDEX_BASE_PATH
    knowledge_path = os.environ.get("KNOWLEDGE_BASE_PATH") if os.environ.get("KNOWLEDGE_BASE_PATH") is not None else DEFAULT_KNOWLEDGE_BASE_PATH
    preprocess_knowledge_path = os.environ.get("PREPROCESS_KNOWLEDGE_BASE_PATH") if os.environ.get("PREPROCESS_KNOWLEDGE_BASE_PATH") is not None else DEFAULT_PREPROCESS_KNOWLEDGE_BASE_PATH
    existing_index = Path(embed_path)
    existing_preprocess_knowledge = Path(preprocess_knowledge_path)
    if existing_index.exists() and existing_preprocess_knowledge.exists():
        _index, _df, _documents = _import_embeds(embed_path, preprocess_knowledge_path)
        return
    _index, _df, _documents = _gen_embeds(knowledge_path, embed_path, preprocess_knowledge_path)


def _gen_embeds(knowledge_location, index_store_path, preprocess_knowledge_store_path):
    df, documents = _load_knowledge(knowledge_location)
    embeddings = np.array([_get_embedding(doc) for doc in documents]).astype('float32')
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    faiss.write_index(index, index_store_path)
    df.to_parquet(preprocess_knowledge_store_path)
    return index, df, documents


def _load_knowledge(knowledge_location):
    df = pd.read_csv(knowledge_location)
    df['content'] = 'Q: ' + df['question'] + ' A: ' + df['answer']
    # df['content'] = 'Category: ' + df['category'] + 'Q: ' + df['question'] + ' A: ' + df['answer']
    documents = df['content'].tolist()
    return df, documents


def _import_embeds(index_location, knowledge_location):
    index = faiss.read_index(index_location)
    df = pd.read_parquet(knowledge_location)
    documents = df['content'].tolist()
    return index, df, documents


def init_rag():
    if _client is None:
        _init_client()
    if _index is None:
        _init_index()



def _get_embedding(text: str):
    if _client is None:
        _init_client()
    result = _client.models.embed_content(
        model="gemini-embedding-001",  # sesuaikan versi model embedding
        contents=text,
    )
    return result.embeddings[0].values


def semantic_search(query: str, top_k: int = 3):
    query_embedding = np.array([_get_embedding(query)]).astype('float32')
    distances, indices = _index.search(query_embedding, top_k)

    results = []
    for rank, idx in enumerate(indices[0]):
        results.append({
            'rank': rank + 1,
            'question': _df.iloc[idx]['question'],
            'answer': _df.iloc[idx]['answer'],
            'category': _df.iloc[idx]['category'],
            'distance': distances[0][rank]
        })
    return results


async def answer_from_knowledge_base(query: str) -> str:
    """
    Fungsi yang dipanggil router.py ketika intent = 'faq'.
    Menjalankan semantic search, menyusun prompt dengan context hasil retrieval,
    lalu memanggil LLM untuk menghasilkan jawaban.

    # TODO: implementasikan alur lengkap: semantic_search -> build prompt
    # (Persona/Task/Context/Format, lihat Assignment 3 Section 6) -> panggil LLM.
    """
    if _client is None:
        _init_client()
    if _index is None:
        _init_index()

    results = semantic_search(query, top_k=3)
    context_blocks = "\n\n".join(
        f"[{r['rank']}] {r['question']}\n{r['answer']}" for r in results
    )
    prompt = (
        "Persona: Anda adalah asisten IT Helpdesk internal perusahaan yang "
        "ramah, profesional, dan membantu karyawan.\n"
        "Tugas: Jawab pertanyaan karyawan HANYA berdasarkan konteks knowledge "
        "base di bawah ini. Jika konteks tidak memuat jawabannya, katakan "
        "jujur bahwa Anda tidak menemukan informasinya dan sarankan menghubungi "
        "tim IT Helpdesk. Jangan mengarang informasi.\n"
        f"Konteks:\n{context_blocks}\n\n"
        "Format: Jawab dalam bahasa Indonesia yang ringkas, jelas, dan "
        "mudah dipahami. Gunakan poin-poin bila informasinya banyak.\n"
        f"Pertanyaan: {query}"
    )
    response = _client.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-3.6-flash"),
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=1024,
            thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
        ),
    )
    answer = response.text
    if not answer:
        return (
            "Maaf, saya tidak dapat menghasilkan jawaban saat ini. "
            "Silakan coba lagi beberapa saat lagi."
        )
    return answer
