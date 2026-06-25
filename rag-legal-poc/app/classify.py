# app/classify.py
from __future__ import annotations
from typing import Dict
from app import config


def _rule_based_guess(text: str) -> str:
    t = (text or "")[:4000].lower()

    if config.LANGUAGE == "en":
        if any(k in t for k in ["circular", "directive", "memorandum"]):
            return "Circulars"
        if any(k in t for k in ["guideline", "instruction", "procedure"]):
            return "Guidelines"
        if any(k in t for k in ["bylaw", "bye-law", "by-law", "regulation", "rule"]):
            return "Bylaws"
        if any(k in t for k in ["law", "act", "statute", "code"]):
            return "Laws and Regulations"
        return "Laws and Regulations"
    else:
        if any(k in t for k in ["بخشنامه", "ابلاغیه"]):
            return "بخشنامه‌ها"
        if "دستورالعمل" in t:
            return "دستورالعمل‌ها"
        if "آیین نامه" in t or "آیین‌نامه" in t:
            return "آیین‌نامه‌ها"
        return "قوانین و مقررات"


def classify_category(chat, text: str, meta: Dict) -> str:
    try:
        cats = " | ".join(config.CATEGORIES)

        if config.LANGUAGE == "en":
            sys = "You are a banking legal document classifier. Output only one of the requested labels."
            user = (
                f"Classify this document into one of the following categories:\n"
                f"{cats}\n\n"
                f"Metadata: {meta}\n\n"
                f"Text (excerpt):\n{text[:1600]}\n\n"
                f"Output only the category name."
            )
        else:
            sys = "شما یک دسته‌بند اسناد حقوقی بانکی هستید. فقط یکی از برچسب‌های خواسته‌شده را خروجی بده."
            user = (
                f"بر اساس متن و متادیتا، سند را در یکی از دسته‌های زیر طبقه‌بندی کن:\n"
                f"{cats}\n\n"
                f"متادیتا: {meta}\n\n"
                f"متن (گزیده):\n{text[:1600]}\n\n"
                f"فقط نام یکی از دسته‌ها را بده."
            )

        out = chat.chat(system=sys, user=user).strip()
        for c in config.CATEGORIES:
            if c in out:
                return c

        # Fallback based on language
        if config.LANGUAGE == "en":
            out_lower = out.lower()
            if any(k in out_lower for k in ["circular"]):
                return "Circulars"
            if any(k in out_lower for k in ["guideline", "instruction"]):
                return "Guidelines"
            if any(k in out_lower for k in ["bylaw", "regulation"]):
                return "Bylaws"
        else:
            if "بخشنامه" in out:
                return "بخشنامه‌ها"
            if "دستورالعمل" in out:
                return "دستورالعمل‌ها"
            if "آیین" in out:
                return "آیین‌نامه‌ها"

        return _rule_based_guess(text)
    except Exception:
        return _rule_based_guess(text)