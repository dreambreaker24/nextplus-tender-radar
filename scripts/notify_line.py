import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

GROUP_ID = "Cfd7af51c178f1d119646e7032cfa352a"
PAGE_URL = "https://dreambreaker24.github.io/nextplus-tender-radar/"
TAIPEI = timezone(timedelta(hours=8))
MIN_DAYS_LEFT = 4
MAX_LISTED = 8


def budget_text(amount):
    if not amount:
        return "預算未公開"
    if amount >= 100000000:
        return f"預算 {amount / 100000000:.2f} 億"
    if amount >= 10000:
        return f"預算 {amount / 10000:,.1f} 萬".replace(".0 萬", " 萬")
    return f"預算 {amount:,} 元"


def build_message(data):
    today = datetime.now(TAIPEI).date()
    cases = []
    for case in data["c"]:
        deadline = datetime.strptime(case["d"][:10], "%Y-%m-%d").date()
        days_left = (deadline - today).days
        if days_left >= MIN_DAYS_LEFT:
            cases.append({**case, "days_left": days_left})

    count = lambda fn: sum(1 for case in cases if fn(case))
    lines = [
        f"📋 奈拾標案雷達（{data['g'][5:10].replace('-', '/')} 更新）",
        f"共 {len(cases)} 案：設計 {count(lambda c: c['y'] == '設計')}｜統包 {count(lambda c: c['y'] == '統包')}｜施工 {count(lambda c: c['y'] == '施工')}（南部 {count(lambda c: c['r'].startswith('南部'))}）",
    ]

    south_design = [case for case in cases if case["y"] in ("設計", "統包") and case["r"].startswith("南部")]
    south_design.sort(key=lambda case: (case["r"] != "南部（台南）", case["days_left"]))
    lines += ["", "【南部 設計／統包】"]
    if south_design:
        for case in south_design[:MAX_LISTED]:
            lines.append(f"・{case['t']}（{case['u']}）")
            lines.append(f"　{case['y']}｜{case['v']}｜{budget_text(case['b'])}｜截止 {case['d'][5:10].replace('-', '/')}（剩 {case['days_left']} 天）")
        if len(south_design) > MAX_LISTED:
            lines.append(f"…另有 {len(south_design) - MAX_LISTED} 案，請看網頁")
    else:
        lines.append("本期沒有")

    other_design = count(lambda c: c["y"] in ("設計", "統包") and not c["r"].startswith("南部"))
    lines += ["", f"其他地區設計／統包 {other_design} 案、施工案等完整清單與準備清單：", PAGE_URL]
    return "\n".join(lines)


data = json.load(open(sys.argv[1], encoding="utf-8"))
message = build_message(data)
if len(sys.argv) > 2 and sys.argv[2] == "--dry-run":
    print(message)
    sys.exit(0)

body = json.dumps({"to": GROUP_ID, "messages": [{"type": "text", "text": message[:4900]}]}, ensure_ascii=False)
result = subprocess.run(
    ["curl", "-sS", "-w", "\n%{http_code}", "-X", "POST", "https://api.line.me/v2/bot/message/push",
     "-H", "Content-Type: application/json", "--data-binary", "@-"],
    input=body.encode("utf-8"), capture_output=True,
)
output = result.stdout.decode("utf-8", "replace").strip()
status = output.rsplit("\n", 1)[-1]
print("LINE sent" if status == "200" else f"LINE failed: HTTP {status} {output[:300]} {result.stderr.decode('utf-8', 'replace')[:300]}")
