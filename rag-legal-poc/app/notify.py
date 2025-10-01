# app/notify.py
from __future__ import annotations
import smtplib
import socket
import ssl
import logging
from typing import List, Optional
from email.utils import formataddr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app import config

logger = logging.getLogger("rag.email")

# -------------------------
# SMTP Connection Helpers
# -------------------------
def _connect_smtp(host: str, port: int, user: str, passwd: str, timeout: float = 20.0):
    """
    اتصال امن به SMTP:
      - اگر پورت 465 باشد: SMTPS (SSL) مستقیم
      - در غیر این صورت (مثل 587): STARTTLS
    """
    ctx = ssl.create_default_context()

    if int(port) == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=ctx)
        server.ehlo()
    else:
        server = smtplib.SMTP(host, port, timeout=timeout)
        server.ehlo()
        server.starttls(context=ctx)
        server.ehlo()

    if user and passwd:
        server.login(user, passwd)
    return server


# -------------------------
# HTML Templating
# -------------------------
_BRAND_BG = "#0b3a6a"  # سرمه‌ای
_ACCENT    = "#1e88e5"  # آبی
_BORDER    = "#e2e8f0"
_TEXT      = "#0f172a"
_MUTED     = "#475569"

def _escape_html(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def _to_html(body: str) -> str:
    """متن ساده را به HTML امن و خوانا تبدیل می‌کند (تبدیل \n به <br>)."""
    safe = _escape_html(body or "").replace("\n", "<br>")
    return safe

def _build_html_email(subject: str, body_text: str, from_name: str) -> str:
    """
    یک قالب HTML تمیز و واکنش‌گرا برای ایمیل می‌سازد.
    """
    body_html = _to_html(body_text)

    return f"""\
<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_escape_html(subject or "")}</title>
<style>
  body {{
    margin: 0; padding: 0; background: #f8fafc; font-family: -apple-system, BlinkMacSystemFont,
    'Segoe UI', Roboto, Helvetica, Arial, 'Noto Sans', 'IranYekan', 'IRANSans', sans-serif;
    color: {_TEXT}; direction: rtl;
  }}
  .wrapper {{ width: 100%; padding: 24px 12px; box-sizing: border-box; }}
  .container {{
    max-width: 720px; margin: 0 auto; background: #ffffff; border: 1px solid {_BORDER};
    border-radius: 16px; overflow: hidden; box-shadow: 0 8px 30px rgba(2,6,23,0.06);
  }}
  .header {{
    background: linear-gradient(135deg, {_BRAND_BG}, {_ACCENT});
    color: #fff; padding: 20px 24px;
  }}
  .header h1 {{
    font-size: 18px; margin: 0; font-weight: 700;
  }}
  .meta {{
    font-size: 12px; opacity: 0.9; margin-top: 6px;
  }}
  .content {{
    padding: 20px 24px; font-size: 14px; line-height: 1.9; color: {_TEXT};
  }}
  .content p {{ margin: 0 0 10px 0; }}
  .note {{
    margin-top: 16px; background: #f1f5f9; border: 1px solid {_BORDER}; border-radius: 12px; padding: 12px 14px;
    color: {_MUTED}; font-size: 12px;
  }}
  .footer {{
    padding: 16px 24px; background: #f8fafc; color: {_MUTED}; font-size: 12px; border-top: 1px solid {_BORDER};
  }}
  .brand-chip {{
    display: inline-block; padding: 4px 10px; background: #e3f2fd; border: 1px solid #cfe3fb;
    color: #0b3a6a; border-radius: 999px; font-size: 12px; font-weight: 600;
  }}
  @media (max-width: 520px) {{
    .content {{ padding: 16px; font-size: 13px; }}
    .header {{ padding: 16px; }}
    .footer {{ padding: 12px 16px; }}
  }}
</style>
</head>
<body>
  <div class="wrapper">
    <div class="container">
      <div class="header">
        <h1>{_escape_html(subject or "اطلاع‌رسانی")}</h1>
        <div class="meta">
          از طرف: {_escape_html(from_name or "RAG Legal Bot")}
        </div>
      </div>
      <div class="content">
        <p>{body_html}</p>

        <div class="note">
          این پیام به‌صورت خودکار توسط سامانهٔ RAG ارسال شده است. لطفاً در صورت نیاز به پاسخ، به این ایمیل ریپلای کنید.
        </div>
      </div>
      <div class="footer">
        <span class="brand-chip">RAG Legal</span>
        <div style="margin-top:8px">© {from_name or "RAG Legal Bot"} — تمامی حقوق محفوظ است.</div>
      </div>
    </div>
  </div>
</body>
</html>
"""


# -------------------------
# Public API (backward compatible)
# -------------------------
def send_email(subject: str, body: str, recipients: List[str], from_name: str = "RAG Legal Bot") -> bool:
    """
    ارسال ایمیل حرفه‌ای:
      - Multipart/Alternative: هم متن ساده، هم HTML
      - اتصال امن (SMTPS/STARTTLS)
      - لاگ استاندارد و یکبار retry در خطاهای موقتی
    امضای تابع بدون تغییر مانده تا جاهای دیگر پروژه نشکند.
    """
    recipients = [r.strip() for r in (recipients or []) if r and r.strip()]
    if not recipients:
        logger.warning("[EMAIL] no recipients provided")
        return False

    sender_email = config.SMTP_FROM or config.SMTP_USER or "no-reply@example.com"

    # پیام چندبخشی: متن ساده + HTML
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject or ""
    msg["From"] = formataddr((from_name, sender_email))
    msg["To"] = ", ".join(recipients)

    # نسخهٔ متن ساده (fallback برای کلاینت‌های قدیمی)
    text_part = MIMEText(body or "", "plain", _charset="utf-8")

    # نسخهٔ HTML شیک
    html_str = _build_html_email(subject=subject or "", body_text=body or "", from_name=from_name or "")
    html_part = MIMEText(html_str, "html", _charset="utf-8")

    msg.attach(text_part)
    msg.attach(html_part)

    # تلاش برای ارسال با یک بار retry در خطاهای موقتی
    def _try_send() -> bool:
        try:
            server = _connect_smtp(
                host=config.SMTP_HOST,
                port=int(config.SMTP_PORT),
                user=config.SMTP_USER,
                passwd=config.SMTP_PASS,
                timeout=25.0
            )
            server.sendmail(sender_email, recipients, msg.as_string())
            try:
                server.quit()
            except Exception:
                server.close()
            return True
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPDataError, smtplib.SMTPConnectError, socket.timeout) as e:
            logger.warning(f"[EMAIL][RETRYABLE] {e}")
            return False
        except (smtplib.SMTPException, socket.error) as e:
            logger.error(f"[EMAIL][ERROR] {e}")
            return False

    ok = _try_send()
    if not ok:
        # یک بار تلاش مجدد
        logger.info("[EMAIL] retrying once...")
        ok = _try_send()

    if ok:
        logger.info(f"[EMAIL] sent to {len(recipients)} recipient(s)")
    else:
        logger.error("[EMAIL] failed to send")

    return ok
