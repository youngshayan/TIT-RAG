# app/classify.py
from __future__ import annotations
from typing import Dict
from app import config

def _rule_based_guess(text: str) -> str:
    t = (text or "")[:4000]
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
        if "بخشنامه" in out: return "بخشنامه‌ها"
        if "دستورالعمل" in out: return "دستورالعمل‌ها"
        if "آیین" in out: return "آیین‌نامه‌ها"
        return _rule_based_guess(text)
    except Exception:
        return _rule_based_guess(text)
