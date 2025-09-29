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

# --- Embeddings ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")  # "cpu" یا "cuda"

# --- Retrieval knobs ---
VEC_K = int(os.getenv("VEC_K", "15"))
BM25_K = int(os.getenv("BM25_K", "15"))

# --- Reranker ---
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANKER_DEVICE = os.getenv("RERANKER_DEVICE", "cpu")
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

# -------------------- LLM Configs --------------------
# Primary: GPT-4o-mini via ArvanCloud (OpenAI-compatible /v1/chat/completions)
GPT4O_ENDPOINT = os.getenv("GPT4O_ENDPOINT", "https://arvancloudai.ir/gateway/models/GPT-4o-mini/x-s_R7OXVU9yI4tPZYHgK1hnvvNWSPkIr4MtLg_RdMwCuSW94nrpPLbI_uH9RAq1ovO6-Dut4d-H4SgFI1UXaZH5sW9N74GRVzbimYwObEXq_BssQat3OCZjY9oKTa_MnWeC2Cc87rabriKxREISUqKq_6FV-bz9lSK8gK7d-rjzc6sKknQdvpQ1CniiKk6lHEjIouuCY3dfy-23VT3ot_MnfB_tIhGtNamIeHHUafrBWGj1XX3B-fi0eHI/v1/chat/completions")
GPT4O_API_KEY = os.getenv("GPT4O_API_KEY", "apikey ab87839b-8754-577b-9b9e-de68e720dbb1")
GPT4O_MODEL   = os.getenv("GPT4O_MODEL",   "GPT-4o-mini")

# Backup: DeepSeek Chat V3 via ArvanCloud
DEEPSEEK_ENDPOINT = os.getenv("DEEPSEEK_ENDPOINT", "https://api.avalai.ir/v1")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "aa-sVt6V9D4o6dloCd1I4wEk95txDJejZ81t7clBAjZrJQ5CoLL")
DEEPSEEK_MODEL   = os.getenv("DEEPSEEK_MODEL",   "gpt-4.1")

# LLM runtime knobs
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS  = int(os.getenv("LLM_MAX_TOKENS", "1200"))
LLM_TIMEOUT_SEC = float(os.getenv("LLM_TIMEOUT_SEC", "40"))


# --- BM25 (sparse) storage + knobs ---
BM25_CORPUS_PATH = DATA_DIR / "bm25_corpus.jsonl"   # متن چانک‌ها (JSON Lines)
BM25_INDEX_PATH  = DATA_DIR / "bm25_index.pkl"      # مدل/وُکتورایزر pickled

# تنظیمات قابل‌تیون برای BM25
BM25_MIN_DF       = int(os.getenv("BM25_MIN_DF", "1"))
BM25_MAX_FEATURES = int(os.getenv("BM25_MAX_FEATURES", "250000"))
# tuple به صورت "1,2" هم قابل خواندن از .env هست؛ این دیفالت:
BM25_NGRAM        = (1, 2)


# ---------------- Email / SMTP (Gmail) ----------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "mindsol2025@gmail.com")  # yourgmail@gmail.com
SMTP_PASS = os.getenv("SMTP_PASS", "jmnnnlgxbhqeecla")  # 16-char App Password
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@example.com")

CATEGORY_RECIPIENTS = {
    "قوانین و مقررات": os.getenv("CAT_RECIP_LAW", "shayan2248@gmail.com"),
    "آیین‌نامه‌ها":    os.getenv("CAT_RECIP_BYLAW", "pofhaze@gmail.com"),
    "دستورالعمل‌ها":   os.getenv("CAT_RECIP_GUIDE", "theyoungshayan@gmail.com"),
    "بخشنامه‌ها":      os.getenv("CAT_RECIP_CIRCULAR", "team-circular@example.com"),
}


# --- Admin post-actions ---
ADMIN_INLINE_INDEX = True  # همزمان با آپلود، همان‌جا add_document_with_chunks + index_doc انجام شود
RUN_INGEST_FOR_NEW_FILES = False  # اگر True و بالایی False باشد، بعد از آپلود روی همان فایل‌های جدید ingest_file اجرا می‌شود
RUN_REEMBED_AFTER_ADMIN = False   # اگر True باشد بعد از هر آپلود ادمین، reembed_all در پس‌زمینه اجرا می‌شود (سنگین است)


AVALAI_API_KEY = "aa-sVt6V9D4o6dloCd1I4wEk95txDJejZ81t7clBAjZrJQ5CoLL"
AVALAI_BASE_URL = "https://api.avalai.ir/v1"
AVALAI_RERANK_MODEL = "cohere.rerank-v3-5:0"
USE_AVALAI_RERANK = True            # روشن/خاموش
LOCAL_HYBRID_CAND_K = 60            # چند کاندید اول از استور وارد هیبرید شوند
LOCAL_HYBRID_TOP_K = 20             # خروجی هیبرید برای ورودی رِرَنکر
HYBRID_W_BM25 = 0.6
HYBRID_W_TFIDF = 0.4


CHUNK_TOKENS = 650
CHUNK_OVERLAP = 90



DOC_FAISS_INDEX_PATH = DATA_DIR / "faiss_doc.index"
DOC_FAISS_MAP_PATH   = DATA_DIR / "faiss_doc_map.json"
