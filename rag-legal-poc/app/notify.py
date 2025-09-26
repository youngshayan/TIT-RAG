# app/notify.py
from __future__ import annotations
import smtplib
from email.mime.text import MIMEText
from typing import List
from app import config

def send_email(subject: str, body: str, to_emails: List[str]) -> bool:
    if not config.SMTP_HOST or not to_emails:
        return False
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = config.SMTP_FROM
    msg["To"] = ", ".join(to_emails)
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            if config.SMTP_USER:
                server.login(config.SMTP_USER, config.SMTP_PASS)
            server.sendmail(config.SMTP_FROM, to_emails, msg.as_string())
        return True
    except Exception:
        return False
