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
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://ntfy.sh", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    urllib.request.urlopen(req, timeout=20).read()


def fetch():
    q = urllib.parse.urlencode({
        "year": TARGET_YEAR, "month": TARGET_MONTH, "planType": 1,
    })
    req = urllib.request.Request(f"{API}?{q}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def find_cell(data):
    """12月のカレンダーから対象日のセル(HTML文字列)を探す"""
    caption_key = f"{TARGET_MONTH}月"
    for i in range(6):
        block = data.get(str(i)) if isinstance(data, dict) else data[i]
        if not block:
            continue
        if caption_key not in block.get("calendarCaption", ""):
            continue
        for row in block["data"]:
            for cell in row.values():
                if not isinstance(cell, str):
                    continue
                text = re.sub(r"<[^>]*>", " ", cell)
                m = re.search(r"\d+", text)
                if m and int(m.group()) == TARGET_DAY:
                    return cell
    return None


def main():
    data = fetch()
    cell = find_cell(data)
    if cell is None:
        print("対象日のセルが見つかりません。サイト構造が変わった可能性があります。")
        print(json.dumps(data, ensure_ascii=False)[:2000])
        sys.exit(1)

    label = next((name for cls, name in STATUS if cls in cell), "不明")
    print(f"{TARGET_MONTH}/{TARGET_DAY}: {label}\n{cell}")

    if "fa-xmark" not in cell:
        notify(
            f"{TARGET_MONTH}/{TARGET_DAY} 空きが出ました",
            f"西村屋本館 {TARGET_MONTH}/{TARGET_DAY} の状態: {label}",
        )


if __name__ == "__main__":
    main()
