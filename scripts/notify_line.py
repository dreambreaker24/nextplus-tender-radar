import json
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

GROUP_ID = "Cfd7af51c178f1d119646e7032cfa352a"
PAGE_URL = "https://dreambreaker24.github.io/nextplus-tender-radar/"
TAIPEI = timezone(timedelta(hours=8))
MIN_DAYS_LEFT = 4
MAX_CASE_CARDS = 11
INK = "#1f2328"
MUTED = "#6b6a66"
GOLD = "#9c7a3c"
REGION_ORDER = ["南部（台南）", "南部", "中部", "北部", "東部", "離島"]
VERDICT_COLOR = {"可投": "#2f7d4f", "待確認": "#a4660d"}


def budget_text(amount):
    if not amount:
        return "預算未公開"
    if amount >= 100000000:
        return f"預算 {amount / 100000000:.2f} 億"
    if amount >= 10000:
        return f"預算 {amount / 10000:,.1f} 萬".replace(".0 萬", " 萬")
    return f"預算 {amount:,} 元"


def open_cases(data):
    today = datetime.now(TAIPEI).date()
    cases = []
    for case in data["c"]:
        days_left = (datetime.strptime(case["d"][:10], "%Y-%m-%d").date() - today).days
        if days_left >= MIN_DAYS_LEFT:
            cases.append({**case, "days_left": days_left})
    return cases


def tag(text, color):
    return {"type": "text", "text": text, "size": "xs", "color": color, "weight": "bold", "flex": 0}


def summary_bubble(data, cases):
    count = lambda fn: sum(1 for case in cases if fn(case))
    row = lambda label, value: {
        "type": "box", "layout": "horizontal", "contents": [
            {"type": "text", "text": label, "size": "sm", "color": MUTED},
            {"type": "text", "text": value, "size": "sm", "color": INK, "align": "end", "weight": "bold"},
        ],
    }
    return {
        "type": "bubble", "size": "kilo",
        "header": {"type": "box", "layout": "vertical", "backgroundColor": INK, "paddingAll": "16px", "contents": [
            {"type": "text", "text": "奈拾室內裝修設計 · 政府標案", "size": "xxs", "color": "#d2b27a"},
            {"type": "text", "text": "標案雷達", "size": "xl", "weight": "bold", "color": "#ffffff"},
            {"type": "text", "text": f"{data['g'][5:10].replace('-', '/')} 更新", "size": "xs", "color": "#c9c7c1"},
        ]},
        "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
            {"type": "text", "text": f"共 {len(cases)} 案", "size": "xxl", "weight": "bold", "color": INK},
            row("設計", f"{count(lambda c: c['y'] == '設計')} 案"),
            row("統包", f"{count(lambda c: c['y'] == '統包')} 案"),
            row("施工", f"{count(lambda c: c['y'] == '施工')} 案"),
            {"type": "separator", "margin": "md"},
            row("在南部", f"{count(lambda c: c['r'].startswith('南部'))} 案"),
            {"type": "text", "text": "往右滑看設計／統包案 →", "size": "xs", "color": GOLD, "margin": "md"},
        ]},
        "footer": {"type": "box", "layout": "vertical", "contents": [
            {"type": "button", "style": "primary", "color": GOLD, "height": "sm",
             "action": {"type": "uri", "label": "打開完整網頁", "uri": PAGE_URL}},
        ]},
    }


def case_bubble(case):
    tobid = "https://tobid.tw/?case=" + urllib.parse.quote(case["k"], safe=".")
    return {
        "type": "bubble", "size": "kilo",
        "body": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
            {"type": "box", "layout": "horizontal", "spacing": "sm", "contents": [
                tag(case["v"], VERDICT_COLOR.get(case["v"], "#a4660d")),
                tag(case["y"], GOLD),
                tag(case["r"], GOLD),
            ]},
            {"type": "text", "text": case["t"], "weight": "bold", "size": "md", "color": INK, "wrap": True, "maxLines": 4},
            {"type": "text", "text": case["u"], "size": "xs", "color": MUTED, "wrap": True},
            {"type": "separator", "margin": "md"},
            {"type": "text", "text": budget_text(case["b"]), "size": "sm", "color": INK, "margin": "md"},
            {"type": "text", "text": f"截止 {case['d'][5:16].replace('-', '/')}（剩 {case['days_left']} 天）", "size": "sm",
             "color": "#b3372f" if case["days_left"] <= 7 else INK},
            {"type": "text", "text": case["a"], "size": "xs", "color": MUTED, "wrap": True},
        ]},
        "footer": {"type": "box", "layout": "vertical", "contents": [
            {"type": "button", "style": "secondary", "height": "sm",
             "action": {"type": "uri", "label": "看詳細資料", "uri": tobid}},
        ]},
    }


def build_message(data):
    cases = open_cases(data)
    design = [case for case in cases if case["y"] in ("設計", "統包")]
    design.sort(key=lambda case: (REGION_ORDER.index(case["r"]) if case["r"] in REGION_ORDER else 9, case["days_left"]))
    bubbles = [summary_bubble(data, cases)] + [case_bubble(case) for case in design[:MAX_CASE_CARDS]]
    alt = f"奈拾標案雷達 {data['g'][5:10].replace('-', '/')}：共 {len(cases)} 案，設計／統包 {len(design)} 案"
    count = lambda fn: sum(1 for case in cases if fn(case))
    share_text = "\n".join([
        f"📋 奈拾標案雷達（{data['g'][5:10].replace('-', '/')} 更新）",
        f"共 {len(cases)} 案：設計 {count(lambda c: c['y'] == '設計')}｜統包 {count(lambda c: c['y'] == '統包')}｜施工 {count(lambda c: c['y'] == '施工')}（南部 {count(lambda c: c['r'].startswith('南部'))}）",
        "完整清單、分類與準備清單請點：",
        PAGE_URL,
    ])
    return [
        {"type": "flex", "altText": alt, "contents": {"type": "carousel", "contents": bubbles}},
        {"type": "text", "text": share_text},
    ]


args = sys.argv[1:]
data = json.load(open(args[0], encoding="utf-8"))
message = build_message(data)
if "--dry-run" in args:
    print(json.dumps(message, ensure_ascii=False, indent=1))
    sys.exit(0)

target = args[args.index("--to") + 1] if "--to" in args else GROUP_ID
body = json.dumps({"to": target, "messages": message}, ensure_ascii=False)
result = subprocess.run(
    ["curl", "-sS", "-w", "\n%{http_code}", "-X", "POST", "https://api.line.me/v2/bot/message/push",
     "-H", "Content-Type: application/json", "--data-binary", "@-"],
    input=body.encode("utf-8"), capture_output=True,
)
output = result.stdout.decode("utf-8", "replace").strip()
status = output.rsplit("\n", 1)[-1]
print("LINE sent" if status == "200" else f"LINE failed: HTTP {status} {output[:500]} {result.stderr.decode('utf-8', 'replace')[:300]}")
