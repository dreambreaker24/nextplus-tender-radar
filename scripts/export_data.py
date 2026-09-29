import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone

PREP_CODES = [
    ("信", lambda c, text: "信用" in text or "退票" in text),
    ("押", lambda c, text: c["bid_bond"].startswith("是")),
    ("保", lambda c, text: c["performance_bond"].startswith("是")),
    ("電", lambda c, text: c["e_bid"].startswith("是")),
    ("室", lambda c, text: "室內裝修" in text),
    ("技", lambda c, text: "技術人員" in text),
    ("會", lambda c, text: "需公會會員證" in c["flags"]),
    ("建", lambda c, text: "需搭配建築師" in c["flags"]),
]


def compact(case):
    text = case["qualification"] + " " + json.dumps(case["capability_detail"], ensure_ascii=False)
    budget = re.sub(r"[^0-9]", "", case["budget"])
    official = re.search(r"pkPmsMain=([^&]+)", case["official_url"] or "")
    return {
        "t": case["title"],
        "u": case["unit_name"],
        "b": int(budget) if budget else 0,
        "d": case["deadline"],
        "a": case["award_method"],
        "p": re.sub(r"\(.*?\)", "", case["place"]),
        "y": case["type"],
        "r": case["region"],
        "v": case["verdict"],
        "w": case["verdict_reason"],
        "c": "".join(code for code, test in PREP_CODES if test(case, text)),
        "k": f"{case['unit_id']}|{case['job_number']}",
        "o": official.group(1) if official else "",
    }


if __name__ == "__main__":
    cases = json.load(open(sys.argv[1], encoding="utf-8"))
    generated = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    data = {"g": generated, "c": [compact(case) for case in cases]}
    text = unicodedata.normalize("NFC", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    open(sys.argv[2], "w", encoding="utf-8").write(text)
    print(len(data["c"]), len(text))
