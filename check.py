import json
import os
import re
import sys
import urllib.parse
import urllib.request

# ===== 設定 =====
TARGET_YEAR = 2026
TARGET_MONTH = 12
TARGET_DAY = 6
API = "https://reserve.489ban.net/client/honkan/0/plan/availability/dailycalendar"
PAGE = "https://reserve.489ban.net/client/honkan/0/plan/availability/daily#content"
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
# =================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (vacancy-watch personal use)",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": PAGE,
}

STATUS = [
    ("fa-xmark", "満室(×)"),
    ("fa-triangle-exclamation", "残りわずか(△)"),
    ("fa-circle", "空室あり(○)"),
    ("fa-square-phone", "お電話で問い合わせ"),
    ("fa-minus", "受付できません(-)"),
]


def notify(title, message):
    if not NTFY_TOPIC:
        print("NTFY_TOPIC未設定のため通知スキップ:", title, message)
        return
    body = json.dumps({
        "topic": NTFY_TOPIC,
        "title": title,
        "message": message,
        "click": PAGE,
        "priority": 4,
        "tags": ["tada"],
