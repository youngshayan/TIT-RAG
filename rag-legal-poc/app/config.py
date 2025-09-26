# app/config.py
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
FILES_DIR = DATA_DIR / "files"
TMP_DIR = DATA_DIR / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

FAISS_INDEX_PATH = DATA_DIR / "faiss.index"
FAISS_MAP_PATH = DATA_DIR / "faiss_map.json"
SQLITE_PATH = DATA_DIR / "rag.sqlite"

# --- Chunking ---
CHUNK_TOKENS = 500
CHUNK_OVERLAP = 50

DISCLAIMER = "این پاسخ صرفاً برای کمک اولیه است و جایگزین نظر قطعی مشاور حقوقی نیست."

# --- load .env (optional) ---
load_dotenv(override=True)

# --- Embeddings (برای Persian مناسب) ---
# یکی از این‌ها:
#   "intfloat/multilingual-e5-base"
#   "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")  # "cpu" یا "cuda"

# --- Retrieval knobs ---
VEC_K = int(os.getenv("VEC_K", "15"))
BM25_K = int(os.getenv("BM25_K", "15"))

# --- Reranker (برای app/retrieval.py) ---
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANKER_DEVICE = os.getenv("RERANKER_DEVICE", "cpu")  # "cpu" یا "cuda"
RERANKER_ENABLE = os.getenv("RERANKER_ENABLE", "true").lower() in {"1","true","yes"}

# --- Admin / Categories / Email ---
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme-admin-token")

CATEGORIES = [
    "قوانین و مقررات",
    "آیین‌نامه‌ها",
    "دستورالعمل‌ها",
    "بخشنامه‌ها",
]

CATEGORY_RECIPIENTS = {
    "قوانین و مقررات": os.getenv("CAT_RECIP_LAW", ""),
    "آیین‌نامه‌ها": os.getenv("CAT_RECIP_BYLAW", ""),
    "دستورالعمل‌ها": os.getenv("CAT_RECIP_GUIDE", ""),
    "بخشنامه‌ها": os.getenv("CAT_RECIP_CIRCULAR", ""),
}

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@example.com")
