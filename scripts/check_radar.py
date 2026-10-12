import base64
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

REPO = "dreambreaker24/nextplus-tender-radar"
URL = f"https://api.github.com/repos/{REPO}/contents/data.json?ref=main"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
TAIPEI = timezone(timedelta(hours=8))
ALERT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_line.py")

today = datetime.now(TAIPEI).strftime("%Y-%m-%d")
command = ["curl", "-sS", "--fail-with-body", "-H", f"Authorization: Bearer {TOKEN}",
           "-H", "Accept: application/vnd.github+json", URL]
result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
if result.returncode != 0:
    problem = f"巡邏檢查讀不到網頁資料（GitHub 回應異常），無法確認今天 {today} 有沒有更新，請找 Claude 查。"
else:
    data = json.loads(base64.b64decode(json.loads(result.stdout)["content"]).decode("utf-8"))
    updated = data.get("g", "")
    if not updated.startswith(today):
        problem = f"今天 {today} 早上的標案雷達沒有跑完：網頁資料停在 {updated or '未知'}，LINE 群組也不會收到通知。請找 Claude 查排程紀錄。"
    elif not data.get("c"):
        problem = f"今天 {today} 標案雷達有更新，但一案都沒有，可能是資料來源出問題，請找 Claude 查。"
    else:
        problem = ""

if problem:
    print("PROBLEM", problem)
    subprocess.run([sys.executable, ALERT, problem])
else:
    print("OK", updated, len(data["c"]))
