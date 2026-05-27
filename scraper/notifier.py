import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .scrapers.base import Property

logger = logging.getLogger(__name__)

PAGES_BASE_URL = os.environ.get("PAGES_URL", "https://example.github.io/realestate-monitor")

SITE_LABELS = {
    "suumo": "SUUMO",
    "homes": "LIFULL HOME'S",
    "athome": "アットホーム",
}


def send_notification(to_email: str, properties: list[Property], condition_name: str):
    """Send Gmail notification for new properties."""
    if not properties:
        return

    gmail_addr = os.environ["GMAIL_ADDRESS"]
    gmail_pass = os.environ["GMAIL_APP_PASSWORD"]

    subject = f"【新着物件】{len(properties)}件 — {condition_name}"
    html_body = _build_html(properties, condition_name)
    text_body = _build_text(properties, condition_name)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_addr
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_addr, gmail_pass)
        smtp.sendmail(gmail_addr, to_email, msg.as_string())

    logger.info(f"Notification sent to {to_email} ({len(properties)} properties)")


def _build_html(properties: list[Property], condition_name: str) -> str:
    cards = ""
    for p in properties:
        site_label = SITE_LABELS.get(p.site, p.site)
        detail_url = f"{PAGES_BASE_URL}/property.html?id={p.unique_id}"
        cards += f"""
<div style="border:1px solid #ddd;border-radius:8px;padding:16px;margin:12px 0;background:#fff;">
  <div style="font-size:11px;color:#888;margin-bottom:4px;">{site_label}</div>
  <h3 style="margin:0 0 8px;font-size:16px;color:#1a1a1a;">{p.name}</h3>
  <table style="border-collapse:collapse;width:100%;font-size:14px;">
    <tr><td style="color:#666;padding:3px 8px 3px 0;">住所</td><td>{p.address}</td></tr>
    <tr><td style="color:#666;padding:3px 8px 3px 0;">家賃</td><td style="color:#e53935;font-weight:bold;">{p.rent}</td></tr>
    <tr><td style="color:#666;padding:3px 8px 3px 0;">間取り</td><td>{p.layout}</td></tr>
    <tr><td style="color:#666;padding:3px 8px 3px 0;">面積</td><td>{p.area}</td></tr>
    <tr><td style="color:#666;padding:3px 8px 3px 0;">築年数</td><td>{p.age}</td></tr>
    <tr><td style="color:#666;padding:3px 8px 3px 0;">アクセス</td><td>{p.station_access}</td></tr>
  </table>
  <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;">
    <a href="{p.url}" style="background:#1976d2;color:#fff;padding:8px 16px;border-radius:4px;text-decoration:none;font-size:13px;">元サイトを見る</a>
    <a href="{detail_url}" style="background:#388e3c;color:#fff;padding:8px 16px;border-radius:4px;text-decoration:none;font-size:13px;">詳細・業者検索</a>
  </div>
</div>
"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:-apple-system,sans-serif;background:#f5f5f5;padding:16px;max-width:600px;margin:0 auto;">
  <h2 style="color:#1976d2;">🏠 新着物件 {len(properties)}件 — {condition_name}</h2>
  {cards}
  <p style="font-size:11px;color:#aaa;margin-top:24px;">このメールは自動送信されました。</p>
</body>
</html>"""


def _build_text(properties: list[Property], condition_name: str) -> str:
    lines = [f"【新着物件 {len(properties)}件】{condition_name}\n"]
    for i, p in enumerate(properties, 1):
        detail_url = f"{PAGES_BASE_URL}/property.html?id={p.unique_id}"
        lines += [
            f"\n■ {i}. {p.name}",
            f"  住所: {p.address}",
            f"  家賃: {p.rent}　間取り: {p.layout}　面積: {p.area}",
            f"  築年数: {p.age}　アクセス: {p.station_access}",
            f"  元サイト: {p.url}",
            f"  詳細・業者検索: {detail_url}",
        ]
    return "\n".join(lines)
