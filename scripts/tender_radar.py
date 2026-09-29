import json
import re
import sys
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

MCP_URL = "https://api.tobid.tw/mcp"
OFFICIAL_URL = "https://api.tobid.tw/api/official"
USER_AGENT = "NextplusTenderRadar/1.0 (+https://nextplus-design.com)"
TAIPEI = timezone(timedelta(hours=8))
LOOKBACK_DAYS = 30

KEYWORDS = [
    "室內裝修 設計",
    "室內設計",
    "空間 設計",
    "設計 裝修",
    "統包 裝修",
    "空間改善 設計",
    "空間活化 設計",
    "展示 設計",
    "老屋 設計",
    "裝修 規劃",
    "服務中心 設計",
    "辦公室 設計",
    "室內裝修",
    "裝修工程",
    "空間改善工程",
    "整修工程 室內",
    "廁所整修工程",
    "老屋 整修",
]

EXCLUDE_TITLE = ["道路", "人行", "橋", "排水", "水利", "路燈", "網站", "系統建置", "軟體", "課程", "平面設計", "LOGO", "文宣", "影片", "活動", "屋頂", "防水", "外牆", "邊坡", "護岸", "管線", "消防", "電梯", "空調", "步道", "堤", "球場", "跑道", "國道", "車道"]

SOUTH = ["臺南", "台南", "高雄", "屏東", "嘉義", "雲林", "澎湖"]

RESTRICTED_ONLY = ["建築師", "技師", "工程技術顧問", "營造業"]


def post_json(url, payload):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def search(keyword, page):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "search_tenders", "arguments": {"q": keyword, "kind": "tender", "page": page}},
    }
    result = post_json(MCP_URL, payload)
    return json.loads(result["result"]["content"][0]["text"])


def roc_to_datetime(text):
    match = re.match(r"(\d+)/(\d+)/(\d+)\s*(\d+):(\d+)", text or "")
    if not match:
        return None
    year, month, day, hour, minute = map(int, match.groups())
    return datetime(year + 1911, month, day, hour, minute, tzinfo=TAIPEI)


def classify(qualification):
    text = qualification or ""
    flags = []
    if "工業或商業團體" in text or "公會會員" in text:
        flags.append("需公會會員證")
    if "搭配" in text and "建築師" in text:
        flags.append("需搭配建築師")
    extra = text.split("除上述外之其他資格", 1)[1] if "除上述外之其他資格" in text else ""
    if any(word in text for word in ["室內裝修", "室內裝潢", "室內設計"]):
        return "可投", "資格有列室內裝修業", flags
    if extra and any(word in extra for word in RESTRICTED_ONLY):
        hits = [word for word in RESTRICTED_ONLY if word in extra]
        return "不可投", "資格限 " + "、".join(hits), flags
    if not extra.strip():
        return "可投", "只要公司登記與納稅證明，未限定行業", flags
    return "待確認", "其他資格需看投標須知", flags


def collect():
    now = datetime.now(TAIPEI)
    cutoff = int((now - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d"))
    candidates = {}
    for keyword in KEYWORDS:
        for page in range(1, 11):
            data = search(keyword, page)
            rows = data.get("results", [])
            for row in rows:
                if row["date"] < cutoff:
                    continue
                if any(word in row["title"] for word in EXCLUDE_TITLE):
                    continue
                key = (row["unit_id"], row["job_number"])
                candidates.setdefault(key, row)
            if not rows or rows[-1]["date"] < cutoff:
                break
            time.sleep(0.3)

    def build_case(item):
        (unit_id, job_number), row = item
        query = urllib.parse.urlencode({"unit_id": unit_id, "job_number": job_number})
        try:
            official = get_json(f"{OFFICIAL_URL}?{query}").get("all", {})
        except Exception as error:
            print("official fail", unit_id, job_number, error, file=sys.stderr)
            return None
        deadline = roc_to_datetime(official.get("領投開標:截止投標", ""))
        if not deadline or deadline < now:
            return None
        qualification = official.get("其他:廠商資格摘要", "")
        verdict, reason, flags = classify(qualification)
        place = official.get("其他:履約地點", "")
        return {
            "title": row["title"],
            "unit_name": row["unit_name"],
            "unit_id": unit_id,
            "job_number": job_number,
            "announce_date": row["date"],
            "deadline": deadline.strftime("%Y-%m-%d %H:%M"),
            "days_left": (deadline.date() - now.date()).days,
            "budget": official.get("採購資料:預算金額", ""),
            "category": official.get("採購資料:標的分類", ""),
            "tender_method": official.get("招標資料:招標方式", ""),
            "award_method": official.get("招標資料:決標方式", ""),
            "design_build": official.get("招標資料:是否屬統包", ""),
            "e_bid": official.get("領投開標:是否提供電子投標", ""),
            "bid_bond": official.get("領投開標:是否須繳納押標金", ""),
            "bid_bond_amount": official.get("領投開標:是否須繳納押標金:押標金額度", ""),
            "performance_bond": official.get("領投開標:是否須繳納履約保證金", ""),
            "place": place,
            "south": any(city in place for city in SOUTH),
            "period": official.get("其他:履約期限", ""),
            "qualification": qualification,
            "capability_required": official.get("其他:是否訂有與履約能力有關之基本資格", ""),
            "capability_detail": {k: v for k, v in official.items() if k.startswith("其他:是否訂有與履約能力有關之基本資格:")},
            "extra_note": official.get("其他:附加說明", "")[:600],
            "contact": official.get("機關資料:聯絡人", "") + " " + official.get("機關資料:聯絡電話", ""),
            "verdict": verdict,
            "verdict_reason": reason,
            "flags": flags,
            "tobid_url": f"https://tobid.tw/?case={unit_id}|{job_number}",
            "official_url": official.get("url", ""),
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        cases = [case for case in pool.map(build_case, candidates.items()) if case]
    return cases


if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "cases.json"
    cases = collect()
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(cases, file, ensure_ascii=False, indent=2)
    counts = {}
    for case in cases:
        counts[case["verdict"]] = counts.get(case["verdict"], 0) + 1
    print(len(cases), counts)
