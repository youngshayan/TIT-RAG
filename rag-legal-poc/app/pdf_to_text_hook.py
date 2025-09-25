"""
یکپارچه‌سازی کامل اسکریپت‌های شما داخل پروژه:
- منطق استخراج pdfplumber (چند روش پله‌ای) + اصلاح bidi/reshape دقیقاً حفظ شده
- سپس همان «after-clean» روی متن نهایی اعمال می‌شود
- در نهایت نرمال‌سازی تکمیلی پروژه نیز اجرامی‌شود

اگر استخراج شکست بخورد، از pypdf به‌عنوان fallback استفاده می‌کنیم.
"""

from pathlib import Path
import pdfplumber
from pypdf import PdfReader
import arabic_reshaper
from bidi.algorithm import get_display

from app.utils_text import normalize_persian, repair_spaced_letters

# ---------- همان منطق "کد اول": استخراج چندمرحله‌ای ----------
def _extract_page_text(page):
    # روش 1: معمولی
    text = page.extract_text()
    # روش 2: با پارامترها
    if not text or len(text.strip()) < 10:
        try:
            text = page.extract_text(
                x_tolerance=2,
                y_tolerance=2,
                keep_blank_chars=False,
                use_text_flow=False,
                layout=False
            )
        except Exception:
            text = None
    # روش 3: characters
    if not text or len(text.strip()) < 10:
        try:
            chars = page.chars
            if chars:
                chars_sorted = sorted(chars, key=lambda c: (c['top'], c['x0']))
                text = ''.join(char['text'] for char in chars_sorted)
        except Exception:
            text = None
    # روش 4: words
    if not text or len(text.strip()) < 10:
        try:
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=False,
                extra_attrs=["fontname", "size"]
            )
            if words:
                text = ' '.join(w['text'] for w in words)
        except Exception:
            text = None
    return text or ""

def _extract_farsi_pdf(pdf_path: Path) -> str:
    all_text_parts = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                text = _extract_page_text(page)
                if text and len(text.strip()) > 0:
                    text = text.strip()
                    # جایگزینی کاراکترهای مشکل‌دار
                    text = text.replace('ـ', '').replace('‌', ' ').replace('​', ' ')
                    # حذف خطوط بسیار خالی
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    text = '\n'.join(lines)
                    # reshape + bidi (مطابق کد شما)
                    try:
                        reshaped = arabic_reshaper.reshape(text)
                        bidi_text = get_display(reshaped)
                        all_text_parts.append(f"--- صفحه {idx} ---\n{bidi_text}\n")
                    except Exception:
                        all_text_parts.append(f"--- صفحه {idx} ---\n{text}\n")
                else:
                    all_text_parts.append(f"--- صفحه {idx} ---\n[متن قابل استخراج نبود]\n")
    except Exception:
        # اگر pdfplumber شکست خورد، متن خالی برگردان تا fallback اجرا شود
        return ""
    return "\n".join(all_text_parts).strip()

def _fallback_pypdf(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                pass
        return "\n".join(texts)
    except Exception:
        return ""

# ---------- همان منطق "کد دوم": پاکسازی/نرمال‌سازی سطح-متن ----------
def _after_clean_pipeline(text: str) -> str:
    # همان normalize + تعمیر فاصله‌گذاری حروف
    text = normalize_persian(text)
    text = repair_spaced_letters(text)
    # جمع‌بندی نهایی
    text = normalize_persian(text)
    return text

# ---------- API اصلی استفاده‌شونده در ingest ----------
def pdf_to_text(pdf_path: Path) -> str:
    # مرحله 1: استخراج چندحالته
    txt = _extract_farsi_pdf(pdf_path)
    if not txt or len(txt.strip()) < 10:
        # fallback
        txt = _fallback_pypdf(pdf_path)
    # مرحله 2: اجرای "after pdf reader.py" یکپارچه
    txt = _after_clean_pipeline(txt)
    return txt.strip()
