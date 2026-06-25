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
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

# --- Retrieval knobs ---
VEC_K = int(os.getenv("VEC_K", "15"))
BM25_K = int(os.getenv("BM25_K", "15"))

# --- Reranker ---
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
RERANKER_DEVICE = os.getenv("RERANKER_DEVICE", "cpu")
RERANKER_ENABLE = os.getenv("RERANKER_ENABLE", "true").lower() in {"1","true","yes"}

# --- Admin / Categories / Email ---
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme-admin-token")

# -------------------- Language Settings --------------------
LANGUAGE = os.getenv("LANGUAGE", "fa")  # "fa" or "en"

# Category names based on language
if LANGUAGE == "en":
    CATEGORIES = [
        "Laws and Regulations",
        "Bylaws",
        "Guidelines",
        "Circulars",
    ]
else:
    CATEGORIES = [
        "قوانین و مقررات",
        "آیین‌نامه‌ها",
        "دستورالعمل‌ها",
        "بخشنامه‌ها",
    ]

# Stopwords for each language
if LANGUAGE == "en":
    STOPWORDS = {
        "a","an","the","and","or","but","for","to","of","in","on","at","by","from","with","as",
        "is","are","was","were","be","been","being","this","that","these","those","it","its","their","there",
        "can","could","should","would","may","might","must","shall","will","do","does","did",
        "have","has","had","than","then","hence","thus","hence","accordingly","consequently",
        "so","nor","yet","also","etc","e.g","i.e","et al","etc."
    }
else:
    STOPWORDS = {
        "از","با","به","در","و","را","که","برای","یا","تا","این","آن","بین","بر","طبق","طبقِ",
        "می","های","خواهند","خواهد","کرد","شود","شده","بود","بودن","نیست","است","هست","هم","اما",
        "همچنین","بنابراین","باید","نباید","اگر","اگرچه","مثل","مانند","کلیه","کلاً","کل","هر","هیچ",
        "پس","قبل","بعد","ضمن","بدون","برابر","مطابق","موضوع","تبصره","ماده","مواد","پیوست","پیوست‌ها",
        "صرفاً","صرفا","حداکثر","حداقل","اعم","غیر","تمامی","کلیهٔ","آن‌ها","آنها","ایشان",
    }

# System prompts based on language
SYSTEM_PROMPTS = {
    "fa": {
        "classify": "شما یک دسته‌بند اسناد حقوقی بانکی هستید. فقط یکی از برچسب‌های خواسته‌شده را خروجی بده.",
        "summarize": "خلاصه‌ساز حقوقی. نکات کلیدی، دامنه اجرا، استثناها و مواد مهم را فهرست‌وار بده.",
        "conflict": "تو یک تحلیلگر تطبیق حقوقی هستی. مأموریت: تشخیص «تعارض صریح» یا «تعارض محتمل» بین متن جدید و متون موجود. صرفاً بر اساس دو متن قضاوت کن. اگر تعارضی نیست، واضح بگو نیست. خروجی را JSON برگردان.",
        "rag": "تو یک دستیار حقوقی هستی. فقط بر اساس متون ارائه‌شده پاسخ بده. اگر پاسخ قطعی نیست یا مدرک کافی نیست صادقانه بگو «اطلاعی ندارم». در پایان پاسخ، منابع را با نام فایل و متادیتا ارائه کن.",
        "conflict_judge": "قاضی تعارض متون حقوقی. فقط بر اساس دو متن، مشخص کن تعارض (مغایرت) وجود دارد یا خیر. اگر تعارض هست، بند یا ماده متعارض را دقیق نشان بده و توضیح کوتاه بده."
    },
    "en": {
        "classify": "You are a banking legal document classifier. Output only one of the requested labels.",
        "summarize": "Legal summarizer. List key points, scope, exceptions, and important articles.",
        "conflict": "You are a legal compliance analyst. Task: detect 'explicit conflict' or 'potential conflict' between new text and existing texts. Judge based only on the two texts. If no conflict, clearly say none. Output in JSON.",
        "rag": "You are a legal assistant. Answer only based on the provided texts. If the answer is not definitive or there is insufficient evidence, honestly say 'I don't know'. At the end of the response, provide sources with file names and metadata.",
        "conflict_judge": "Legal text conflict judge. Based only on the two texts, determine if there is a conflict. If there is a conflict, point to the exact conflicting sections and give a brief explanation."
    }
}

CATEGORY_RECIPIENTS = {
    "قوانین و مقررات": os.getenv("CAT_RECIP_LAW", ""),
    "آیین‌نامه‌ها": os.getenv("CAT_RECIP_BYLAW", ""),
    "دستورالعمل‌ها": os.getenv("CAT_RECIP_GUIDE", ""),
    "بخشنامه‌ها": os.getenv("CAT_RECIP_CIRCULAR", ""),
    # English categories (fallback)
    "Laws and Regulations": os.getenv("CAT_RECIP_LAW", ""),
    "Bylaws": os.getenv("CAT_RECIP_BYLAW", ""),
    "Guidelines": os.getenv("CAT_RECIP_GUIDE", ""),
    "Circulars": os.getenv("CAT_RECIP_CIRCULAR", ""),
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
BM25_CORPUS_PATH = DATA_DIR / "bm25_corpus.jsonl"
BM25_INDEX_PATH  = DATA_DIR / "bm25_index.pkl"
BM25_MIN_DF       = int(os.getenv("BM25_MIN_DF", "1"))
BM25_MAX_FEATURES = int(os.getenv("BM25_MAX_FEATURES", "250000"))
BM25_NGRAM        = (1, 2)

# ---------------- Email / SMTP (Gmail) ----------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "mindsol2025@gmail.com")
SMTP_PASS = os.getenv("SMTP_PASS", "jmnnnlgxbhqeecla")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@example.com")

# --- Admin post-actions ---
ADMIN_INLINE_INDEX = True
RUN_INGEST_FOR_NEW_FILES = False
RUN_REEMBED_AFTER_ADMIN = False

AVALAI_API_KEY = "aa-sVt6V9D4o6dloCd1I4wEk95txDJejZ81t7clBAjZrJQ5CoLL"
AVALAI_BASE_URL = "https://api.avalai.ir/v1"
AVALAI_RERANK_MODEL = "cohere.rerank-v3-5:0"
USE_AVALAI_RERANK = True
LOCAL_HYBRID_CAND_K = 60
LOCAL_HYBRID_TOP_K = 20
HYBRID_W_BM25 = 0.6
HYBRID_W_TFIDF = 0.4

CHUNK_TOKENS = 650
CHUNK_OVERLAP = 90

DOC_FAISS_INDEX_PATH = DATA_DIR / "faiss_doc.index"
DOC_FAISS_MAP_PATH   = DATA_DIR / "faiss_doc_map.json"