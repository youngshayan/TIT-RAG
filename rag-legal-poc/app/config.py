import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FILES_DIR = DATA_DIR / "files"
TMP_DIR = DATA_DIR / "tmp"
for p in (DATA_DIR, FILES_DIR, TMP_DIR):
    p.mkdir(parents=True, exist_ok=True)

load_dotenv()

# -------- Chat Models via ArvanCloud (اولویت: GPT-4o-mini ، بکاپ: DeepSeek) --------
GPT4O_API_KEY = "apikey ab87839b-8754-577b-9b9e-de68e720dbb1"
GPT4O_ENDPOINT = "https://arvancloudai.ir/gateway/models/GPT-4o-mini/x-s_R7OXVU9yI4tPZYHgK1hnvvNWSPkIr4MtLg_RdMwCuSW94nrpPLbI_uH9RAq1ovO6-Dut4d-H4SgFI1UXaZH5sW9N74GRVzbimYwObEXq_BssQat3OCZjY9oKTa_MnWeC2Cc87rabriKxREISUqKq_6FV-bz9lSK8gK7d-rjzc6sKknQdvpQ1CniiKk6lHEjIouuCY3dfy-23VT3ot_MnfB_tIhGtNamIeHHUafrBWGj1XX3B-fi0eHI/v1/chat/completions"
GPT4O_MODEL = "GPT-4o-mini"

DEEPSEEK_API_KEY = "apikey ab87839b-8754-577b-9b9e-de68e720dbb1"
DEEPSEEK_ENDPOINT = "https://arvancloudai.ir/gateway/models/DeepSeek-Chat-V3-0324/S-1V3ANHYEKNsdstvNRRkXauUl9hGCf-Cv57g9W0PmbI2NUGYPoJN4FCpjXLzR8MKQ4VCSII4Phloe2F5bHR1fQYdeZT4nWN3-Rh5aotSrKibMZAyvIYxHvqkWP8GhUrfCPvsDUohYpBz90lUuhRaKZALpvrtTpCNT6teuOQ6y3n2tPE1V7fuZ6QbMcRhs8-uutzvE9ibH1zr8iKSDWf65QxeOEKDVvJoN3wRToRsOG2Ulu21NJ1eIKabD-nSMehEdCG6XLN6XQKs8tpjs5b3g/v1/chat/completions"
DEEPSEEK_MODEL = "DeepSeek-Chat-V3-0324"

# -------- Embeddings / Reranker --------
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # سبک. (برای فارسی بد نیست، اگر خواستی multilingual قوی‌تر بگم)

# -------- FAISS / BM25 cache paths --------
FAISS_INDEX_PATH = DATA_DIR / "faiss.index"
FAISS_MAP_PATH = DATA_DIR / "faiss_map.json"
BM25_CORPUS_PATH = DATA_DIR / "bm25_corpus.json"   # توکن‌های هر چانک برای بازسازی BM25
SQLITE_PATH = DATA_DIR / "rag.sqlite"

# -------- Chunking --------
CHUNK_TOKENS = 500
CHUNK_OVERLAP = 50
RAG_TOP_K = 5
BM25_K = 30
VEC_K = 30
MERGED_K = 12   # بعد از ادغام و ریرنک

DISCLAIMER = (
    "⚠️ این پاسخ صرفاً بر مبنای متن‌های موجود در مخزن است و "
    "ماهیت «مشاوره حقوقی رسمی» ندارد."
)
