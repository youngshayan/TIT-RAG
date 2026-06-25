# app/utils_text.py
import re
import unicodedata
from app import config

_arabic_to_persian = str.maketrans("كي", "کی")


def normalize_persian(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_arabic_to_persian)
    text = "".join(
        ch for ch in text
        if (ch in ("\n", "\r", "\t") or ch == "\u200C" or ord(ch) >= 32)
    )
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s+([,،:؛\.\?!)])", r"\1", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


ARABIC_RANGES = (
    "\u0600-\u06FF"
    "\u0750-\u077F"
    "\u08A0-\u08FF"
    "\uFB50-\uFDFF"
    "\uFE70-\uFEFF"
)
LETTER_WITH_SPACES_PATTERN = re.compile(
    rf"(?:(?<=\s)|^)(?:[{ARABIC_RANGES}]\s+)(?:[{ARABIC_RANGES}]\s+)*(?:[{ARABIC_RANGES}])(?=(?:\s|$))",
    flags=re.UNICODE
)
SINGLE_ARABIC_CHAR = re.compile(rf"^[{ARABIC_RANGES}]$")


def repair_spaced_letters(text: str) -> str:
    lines = text.splitlines()
    new_lines = []
    for line in lines:
        l = re.sub(r"[ \t]+", " ", line).strip()
        tokens = l.split(" ")
        out_tokens, buffer = [], []
        for tok in tokens:
            if SINGLE_ARABIC_CHAR.match(tok):
                buffer.append(tok)
            else:
                if len(buffer) >= 2:
                    out_tokens.append("".join(buffer))
                elif len(buffer) == 1:
                    out_tokens.append(buffer[0])
                buffer = []
                out_tokens.append(tok)
        if buffer:
            out_tokens.append("".join(buffer) if len(buffer) >= 2 else buffer[0])
        reconstructed = " ".join(t for t in out_tokens if t != "")
        new_lines.append(reconstructed)
    text = "\n".join(new_lines)

    def _collapse_match(m):
        s = m.group(0)
        return re.sub(r"\s+", "", s)

    text = LETTER_WITH_SPACES_PATTERN.sub(_collapse_match, text)
    text = re.sub(r"\s+([,،:؛\.\?!)])", r"\1", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def detect_language(text: str) -> str:
    """Detect if text is primarily English or Farsi"""
    if not text:
        return config.LANGUAGE

    # Count Farsi/Arabic characters
    farsi_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))

    if farsi_chars > english_chars:
        return "fa"
    elif english_chars > farsi_chars:
        return "en"
    else:
        return config.LANGUAGE  # fallback to config


def normalize_english(text: str) -> str:
    """Normalize English text"""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def normalize_text(text: str, lang: str = None) -> str:
    """Normalize text based on language"""
    if not text:
        return ""

    if lang is None:
        lang = detect_language(text)

    if lang == "fa":
        return normalize_persian(text)
    else:
        return normalize_english(text)