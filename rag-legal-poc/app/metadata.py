import re
import json
from typing import Dict, Optional

date_pat = r"(?:\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}|\d{1,2}\s+(?:فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند)\s+\d{4})"

def extract_doc_meta(full_text: str) -> Dict:
    meta = {}
    # عنوان (اولین خط معنی‌دار)
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    if lines:
        meta["title"] = lines[0][:200]
    # شماره
    m = re.search(r"(شماره|شماره نامه)\s*[:\-]*\s*([0-9\-\/]+)", full_text)
    if m: meta["number"] = m.group(2)
    # تاریخ
    m = re.search(r"(تاریخ|تاريخ)\s*[:\-]*\s*(" + date_pat + ")", full_text)
    if m: meta["issue_date"] = m.group(2)
    # مرجع صادرکننده
    m = re.search(r"(بانک مرکزی|هیئت مدیره|هیأت مدیره|اداره کل|معاونت|مدیریت)\s+[^\n]{0,40}", full_text)
    if m: meta["issuer"] = m.group(0)
    # تاریخ اجرا
    m = re.search(r"(تاریخ اجرا|لازم‌الاجرا از)\s*[:\-]*\s*(" + date_pat + ")", full_text)
    if m: meta["effective_date"] = m.group(2)
    return meta

def extract_chunk_meta(text: str) -> Dict:
    meta = {}
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
