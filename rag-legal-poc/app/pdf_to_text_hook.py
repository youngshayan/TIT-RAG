# app/pdf_to_text_hook.py


from pathlib import Path
import pdfplumber
from pypdf import PdfReader
import arabic_reshaper
from bidi.algorithm import get_display

from app.utils_text import normalize_persian, repair_spaced_letters

def _extract_page_text(page):
    text = page.extract_text()
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
    if not text or len(text.strip()) < 10:
        try:
            chars = page.chars
            if chars:
                chars_sorted = sorted(chars, key=lambda c: (c['top'], c['x0']))
                text = ''.join(char['text'] for char in chars_sorted)
        except Exception:
            text = None
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
                    text = text.replace('ـ', '').replace('‌', ' ').replace('​', ' ')
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    text = '\n'.join(lines)
                    try:
                        reshaped = arabic_reshaper.reshape(text)
                        bidi_text = get_display(reshaped)
                        all_text_parts.append(f"--- صفحه {idx} ---\n{bidi_text}\n")
                    except Exception:
                        all_text_parts.append(f"--- صفحه {idx} ---\n{text}\n")
                else:
                    all_text_parts.append(f"--- صفحه {idx} ---\n[متن قابل استخراج نبود]\n")
    except Exception:
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

def _after_clean_pipeline(text: str) -> str:
    text = normalize_persian(text)
    text = repair_spaced_letters(text)
    text = normalize_persian(text)
    return text

def pdf_to_text(pdf_path: Path) -> str:
    txt = _extract_farsi_pdf(pdf_path)
    if not txt or len(txt.strip()) < 10:
        txt = _fallback_pypdf(pdf_path)
    txt = _after_clean_pipeline(txt)
    return txt.strip()
