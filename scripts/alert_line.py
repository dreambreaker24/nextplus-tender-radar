import json
import subprocess
import sys

# 柏的 LINE userId，出問題時只私訊他
OWNER_ID = "U541ab2f5f7ff174be059cabeffe26a21"

text = "⚠️ 標案雷達異常\n" + " ".join(sys.argv[1:])
body = json.dumps({"to": OWNER_ID, "messages": [{"type": "text", "text": text[:4900]}]}, ensure_ascii=False)
result = subprocess.run(
    ["curl", "-sS", "-w", "\n%{http_code}", "-X", "POST", "https://api.line.me/v2/bot/message/push",
     "-H", "Content-Type: application/json", "--data-binary", "@-"],
    input=body.encode("utf-8"), capture_output=True,
)
output = result.stdout.decode("utf-8", "replace").strip()
status = output.rsplit("\n", 1)[-1]
print("LINE sent" if status == "200" else f"LINE failed: HTTP {status} {output[:500]} {result.stderr.decode('utf-8', 'replace')[:300]}")
