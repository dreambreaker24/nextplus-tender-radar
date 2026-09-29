import base64
import json
import os
import subprocess
import sys

REPO = "dreambreaker24/nextplus-tender-radar"
URL = f"https://api.github.com/repos/{REPO}/contents/data.json"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def curl(*args):
    command = ["curl", "-sS", "--fail-with-body", "-H", f"Authorization: Bearer {TOKEN}",
               "-H", "Accept: application/vnd.github+json", *args]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        sys.exit(f"curl failed ({result.returncode}): {result.stdout[:500]} {result.stderr[:500]}")
    return json.loads(result.stdout)


local = open(sys.argv[1], "rb").read()
current = curl(URL + "?ref=main")
body_path = sys.argv[1] + ".put.json"
json.dump({
    "message": sys.argv[2],
    "content": base64.b64encode(local).decode("ascii"),
    "sha": current["sha"],
    "branch": "main",
}, open(body_path, "w", encoding="utf-8"))
result = curl("-X", "PUT", "-H", "Content-Type: application/json", "--data-binary", f"@{body_path}", URL)
print("commit", result["commit"]["sha"])
remote = base64.b64decode(curl(URL + "?ref=main")["content"])
print("SAME" if remote == local else "DIFF")
