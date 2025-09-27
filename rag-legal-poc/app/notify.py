# app/notify.py
from __future__ import annotations
import smtplib
import socket
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import List

from app import config

def _connect_smtp(host: str, port: int, user: str, passwd: str):
    """
    اتصال امن به SMTP روی پورت 587 با STARTTLS (سازگار با Gmail).
    """
    server = smtplib.SMTP(host, port, timeout=20)
    server.ehlo()
    server.starttls()
    server.ehlo()
    if user and passwd:
        server.login(user, passwd)
    return server

def send_email(subject: str, body: str, recipients: List[str], from_name: str = "RAG Legal Bot") -> bool:
    """
    ارسال ایمیل متنی UTF-8 با SMTP (Gmail).
    """
    recipients = [r.strip() for r in (recipients or []) if r and r.strip()]
    if not recipients:
        return False

    sender_email = config.SMTP_FROM or config.SMTP_USER or "no-reply@example.com"

    msg = MIMEText(body or "", _charset="utf-8")
    msg["Subject"] = subject or ""
    msg["From"] = formataddr((from_name, sender_email))
    msg["To"] = ", ".join(recipients)

    try:
        server = _connect_smtp(
            host=config.SMTP_HOST,
            port=config.SMTP_PORT,
            user=config.SMTP_USER,
            passwd=config.SMTP_PASS,
        )
        server.sendmail(sender_email, recipients, msg.as_string())
        try:
            server.quit()
        except Exception:
            server.close()
        return True
    except (smtplib.SMTPException, socket.error) as e:
        print(f"[EMAIL][ERROR] {e}")
        return False
