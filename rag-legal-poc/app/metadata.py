# app/metadata.py
import re
import json
from typing import Dict, Optional
from app import config

# English patterns
EN_DATE_PAT = r"(?:\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})"
EN_NUMBER_PAT = r"(?:No\.|Number|#)\s*[:\-]*\s*([0-9\-/]+)"
EN_ISSUER_PAT = r"(?:Central Bank|Board of Directors|Executive Committee|Department|Office|Ministry|Authority)\s+[^\n]{0,40}"

# Farsi patterns (existing)
FA_DATE_PAT = r"(?:\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}|\d{1,2}\s+(?:فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند)\s+\d{4})"


def extract_doc_meta(full_text: str) -> Dict:
    meta = {}

    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    if lines:
        meta["title"] = lines[0][:200]

    if config.LANGUAGE == "en":
        # English patterns
        m = re.search(EN_NUMBER_PAT, full_text)
        if m:
            meta["number"] = m.group(1)

        m = re.search(r"(?:Date|Issued on)\s*[:\-]*\s*(" + EN_DATE_PAT + ")", full_text, re.IGNORECASE)
        if m:
            meta["issue_date"] = m.group(1)

        m = re.search(EN_ISSUER_PAT, full_text, re.IGNORECASE)
        if m:
            meta["issuer"] = m.group(0)

        m = re.search(r"(?:Effective from|Effective date)\s*[:\-]*\s*(" + EN_DATE_PAT + ")", full_text, re.IGNORECASE)
        if m:
            meta["effective_date"] = m.group(1)

        # Additional English metadata patterns
        m = re.search(r"(?:Title|Document title)\s*[:\-]*\s*([^\n]{0,100})", full_text, re.IGNORECASE)
        if m:
            meta["title"] = m.group(1).strip()
    else:
        # Farsi patterns (existing code)
        m = re.search(r"(شماره|شماره نامه)\s*[:\-]*\s*([0-9\-\/]+)", full_text)
        if m:
            meta["number"] = m.group(2)

        m = re.search(r"(تاریخ|تاريخ)\s*[:\-]*\s*(" + FA_DATE_PAT + ")", full_text)
        if m:
            meta["issue_date"] = m.group(2)

        m = re.search(r"(بانک مرکزی|هیئت مدیره|هیأت مدیره|اداره کل|معاونت|مدیریت)\s+[^\n]{0,40}", full_text)
        if m:
            meta["issuer"] = m.group(0)

        m = re.search(r"(تاریخ اجرا|لازم‌الاجرا از)\s*[:\-]*\s*(" + FA_DATE_PAT + ")", full_text)
        if m:
            meta["effective_date"] = m.group(2)

    return meta


def extract_chunk_meta(text: str) -> Dict:
    meta = {}

    if config.LANGUAGE == "en":
        # English patterns
        m = re.match(r"^\s*(?:Article|Section)\s+(\d+)", text, re.IGNORECASE)
        if m:
            meta["section"] = "Article"
            meta["article_no"] = m.group(1)

        m = re.match(r"^\s*(?:Clause|Paragraph)\s+([a-zA-Z0-9]+)", text, re.IGNORECASE)
        if m:
            meta["section"] = "Clause"
            meta["clause_no"] = m.group(1)

        m = re.match(r"^\s*(?:Subsection|Sub-paragraph)\s+([a-zA-Z0-9]+)", text, re.IGNORECASE)
        if m:
            meta["section"] = "Subsection"
            meta["subsection_no"] = m.group(1)

        m = re.match(r"^\s*(?:Part|Chapter)\s+([a-zA-Z0-9]+)", text, re.IGNORECASE)
        if m:
            meta["section"] = "Part"
            meta["part_no"] = m.group(1)
    else:
        # Farsi patterns (existing code)
        m = re.match(r"^\s*(ماده)\s+(\d+)", text)
        if m:
            meta["section"] = "ماده"
            meta["article_no"] = m.group(2)

        m = re.match(r"^\s*(تبصره)\s+(\d+)", text)
        if m:
            meta["section"] = "تبصره"
            meta["clause_no"] = m.group(2)

        m = re.match(r"^\s*(بند)\s+([الف-ی])", text)
        if m:
            meta["section"] = "بند"
            meta["clause_no"] = m.group(2)

    return meta