import base64
import json
import os
import subprocess
import sys

REPO = "dreambreaker24/nextplus-tender-radar"
URL = f"https://api.github.com/repos/{REPO}/contents/data.json?ref=main"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

command = ["curl", "-sS", "--fail-with-body", "-H", f"Authorization: Bearer {TOKEN}",
           "-H", "Accept: application/vnd.github+json", URL]
result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
if result.returncode != 0:
    sys.exit(f"curl failed ({result.returncode}): {result.stdout[:500]} {result.stderr[:500]}")
remote = base64.b64decode(json.loads(result.stdout)["content"]).decode("utf-8").strip()
local = open(sys.argv[1], encoding="utf-8").read().strip()
if remote == local:
    print("SAME")
else:
    mismatch = next((i for i, (a, b) in enumerate(zip(local, remote)) if a != b), min(len(local), len(remote)))
    print(f"DIFF at char {mismatch}: local={local[mismatch:mismatch + 20]!r} remote={remote[mismatch:mismatch + 20]!r}")
