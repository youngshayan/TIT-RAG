# RAG Legal Assistant (PoC) — فارسی

## قابلیت‌ها
- آپلود PDF/TXT، تبدیل/پاک‌سازی متن (منطق PDF شما یکپارچه شده)، ایندکس
- پرسش‌وپاسخ RAG با استناد
- خلاصه‌سازی سند
- بررسی تعارض (صریح/محتمل) بین سند جدید و اسناد قبلی

> ⚠️ خروجی‌ها جنبه‌ی اطلاع‌رسانی دارند و «مشاوره حقوقی رسمی» نیستند.

## راه‌اندازی سریع (Windows/PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
