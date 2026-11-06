import json
import os
import re
import sys
import urllib.parse
import urllib.request

# ===== 監視対象（増やしたいときは1行追加）=====
# (表示名, サイトのスラッグ, 年, 月, 日)
TARGETS = [
    ("西村屋本館", "honkan", 2026, 12, 6),
    ("精進マウントホテル", "shojiko", 2026, 12, 31),
]
# ===============================================

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
BASE = "https://reserve.489ban.net/client/{slug}/0/plan/availability/"

STATUS = [
    ("fa-xmark", "満室(×)"),
    ("fa-triangle-exclamation", "残りわずか(△)"),
    ("fa-circle", "空室あり(○)"),
    ("fa-square-phone", "お電話で問い合わせ"),
    ("fa-minus", "受付できません(-)"),
]


def notify(title, message, click):
    if not NTFY_TOPIC:
        print("NTFY_TOPIC未設定のため通知スキップ:", title, message)
        return
    body = json.dumps({
        "topic": NTFY_TOPIC,
        "title": title,
        "message": message,
        "click": click,
        "priority": 4,
        "tags": ["tada"],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://ntfy.sh", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    urllib.request.urlopen(req, timeout=20).read()


def fetch(slug, year, month):
    q = urllib.parse.urlencode({"year": year, "month": month, "planType": 1})
    page = BASE.format(slug=slug) + "daily#content"
    req = urllib.request.Request(
        BASE.format(slug=slug) + "dailycalendar?" + q,
        headers={
            "User-Agent": "Mozilla/5.0 (vacancy-watch personal use)",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": page,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def find_cell(data, year, month, day):
    """対象日のセル(HTML文字列)を探す。まず日付クラス、だめなら月の表題+日番号"""
    blocks = []
    if isinstance(data, dict):
        blocks = [v for v in data.values() if isinstance(v, dict) and "data" in v]
    elif isinstance(data, list):
        blocks = [v for v in data if isinstance(v, dict) and "data" in v]

    date_class = 'class="%04d-%02d-%02d"' % (year, month, day)
    for block in blocks:
        for row in block["data"]:
            for cell in row.values():
                if isinstance(cell, str) and date_class in cell:
                    return cell

    for block in blocks:
        m = re.search(r"(\d{4})\D+(\d{1,2})月", block.get("calendarCaption", ""))
        if not m or (int(m.group(1)), int(m.group(2))) != (year, month):
            continue
        for row in block["data"]:
            for cell in row.values():
                if not isinstance(cell, str):
                    continue
                text = re.sub(r"<[^>]*>", " ", cell)
                n = re.search(r"\d+", text)
                if n and int(n.group()) == day:
                    return cell
    return None


def check(name, slug, year, month, day):
    data = fetch(slug, year, month)
    cell = find_cell(data, year, month, day)
    if cell is None:
        print(f"[{name}] 対象日のセルが見つかりません")
        print(json.dumps(data, ensure_ascii=False)[:1500])
        return False

    label = next((n for cls, n in STATUS if cls in cell), "不明")
    print(f"[{name}] {month}/{day}: {label}")

    if "fa-xmark" not in cell:
        notify(
            f"{name} {month}/{day} 空きが出ました",
            f"{name} {month}/{day} の状態: {label}",
            BASE.format(slug=slug) + "daily#content",
        )
    return True


def main():
    ok = True
    for name, slug, y, m, d in TARGETS:
        try:
            ok = check(name, slug, y, m, d) and ok
        except Exception as e:
            print(f"[{name}] エラー: {e}")
            ok = False
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
