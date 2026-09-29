import base64
import json
import os
import sys
import urllib.request

REPO = "dreambreaker24/nextplus-tender-radar"
URL = f"https://api.github.com/repos/{REPO}/contents/data.json"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "User-Agent": "NextplusTenderRadar"}


def call(method, url, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


local = open(sys.argv[1], "rb").read()
current = call("GET", URL + "?ref=main")
result = call("PUT", URL, {
    "message": sys.argv[2],
    "content": base64.b64encode(local).decode("ascii"),
    "sha": current["sha"],
    "branch": "main",
})
print("commit", result["commit"]["sha"])
remote = base64.b64decode(call("GET", URL + "?ref=main")["content"])
print("SAME" if remote == local else "DIFF")
