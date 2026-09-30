import json
import re
import sys
from datetime import datetime, timedelta, timezone

TAIPEI = timezone(timedelta(hours=8))
MIN_DAYS_LEFT = 4
MAX_BUDGET_NON_DESIGN = 6_000_000

TYPE_ORDER = ["設計", "統包", "施工"]
REGION_ORDER = ["南部（台南）", "南部", "中部", "北部", "東部", "離島"]
REGIONS = [
    ("離島", ["澎湖", "金門", "連江", "馬祖", "蘭嶼", "綠島"]),
    ("南部（台南）", ["臺南", "台南"]),
    ("南部", ["嘉義", "高雄", "屏東", "雲林"]),
    ("中部", ["苗栗", "臺中", "台中", "彰化", "南投"]),
    ("北部", ["基隆", "臺北", "台北", "新北", "桃園", "新竹"]),
    ("東部", ["宜蘭", "花蓮", "臺東", "台東"]),
]
GUILD_NAME_PATTERN = re.compile(r"[一-鿿]{2,12}(?:商業|工業)?同業公會")


def case_type(case):
    title = case["title"]
    if "統包" in title or case["design_build"].startswith("是"):
        return "統包"
    if re.search("設計|規劃|策展", title):
        if re.search("製作|施工", title) or case["category"].startswith("工程類"):
            return "統包"
        return "設計"
    return "施工"


def region(case):
    text = case["place"] + " " + case["unit_name"]
    for name, keywords in REGIONS:
        if any(keyword in case["place"] for keyword in keywords):
            return name
    for name, keywords in REGIONS:
        if any(keyword in text for keyword in keywords):
            return name
    return "北部"


def guild_note(qualification):
    names = sorted(set(name for name in GUILD_NAME_PATTERN.findall(qualification) if "建築師" not in name))
    if names:
        return "公告提到：" + "、".join(names) + "。奈拾目前未加入，有興趣可考慮"
    return "公告未指定哪個公會。奈拾目前未加入，有興趣可考慮（室內裝修業一般是室內設計裝修商業同業公會）"


def checklist(case):
    text = case["qualification"] + " " + json.dumps(case["capability_detail"], ensure_ascii=False)
    items = [
        {"name": "公司登記證明", "status": "有", "note": "經濟部商工登記公示資料列印即可"},
        {"name": "納稅證明", "status": "有", "note": "最近一期營業稅 401 申報書收執聯"},
    ]
    if "需公會會員證" in case["flags"]:
        items.append({"name": "公會會員證", "status": "備註", "note": guild_note(case["qualification"])})
    if "室內裝修" in text:
        items.append({"name": "室內裝修業登記證", "status": "有", "note": "設計＋施工，效期至民國 120/3/12"})
    if "技術人員" in text:
        items.append({"name": "室內裝修專業技術人員登記證", "status": "有", "note": "蕭雅丰（設計）、陳映霖（施工）"})
    if "信用" in text or "退票" in text:
        items.append({"name": "廠商信用證明", "status": "要申請", "note": "向往來銀行申請，須為截止日前半年內開立"})
    if "需搭配建築師" in case["flags"]:
        items.append({"name": "建築師合作協議書", "status": "要準備", "note": "需找開業建築師簽合作協議"})
    if case["bid_bond"].startswith("是"):
        items.append({"name": "押標金", "status": "要準備", "note": case.get("bid_bond_amount") or "金額見投標須知"})
    if case["performance_bond"].startswith("是"):
        items.append({"name": "履約保證金（得標後）", "status": "要準備", "note": "得標後繳，金額見投標須知"})
    if "最有利" in case["award_method"]:
        items.append({"name": "服務建議書／企劃書＋簡報", "status": "要製作", "note": "評選案比提案，這是得分關鍵"})
    if case["e_bid"].startswith("是"):
        items.append({"name": "電子投標", "status": "有", "note": "可用工商憑證線上投標"})
    else:
        items.append({"name": "紙本投標", "status": "要準備", "note": "須郵寄或專人送達，注意送達時間"})
    items.append({"name": "投標須知全文", "status": "要下載", "note": "採購網電子領標（約 20 元），選定後我再讀完整須知補清單"})
    return items


def main(source_path, output_path):
    today = datetime.now(TAIPEI).date()
    cases = json.load(open(source_path, encoding="utf-8"))
    kept = []
    for case in cases:
        if case["verdict"] == "不可投":
            continue
        if case["verdict"] == "可投" and "監造" in case["title"] and case["verdict_reason"].startswith("只要公司登記"):
            case["verdict"] = "待確認"
            case["verdict_reason"] = "設計監造案公告未限行業，但投標須知常限建築師，需確認"
        deadline = datetime.strptime(case["deadline"], "%Y-%m-%d %H:%M").date()
        case["days_left"] = (deadline - today).days
        if case["days_left"] < MIN_DAYS_LEFT:
            continue
        case["type"] = case_type(case)
        budget = re.sub(r"[^0-9]", "", case["budget"])
        if case["type"] != "設計" and budget and int(budget) > MAX_BUDGET_NON_DESIGN:
            continue
        case["region"] = region(case)
        case["checklist"] = checklist(case)
        kept.append(case)
    kept.sort(key=lambda c: (TYPE_ORDER.index(c["type"]), REGION_ORDER.index(c["region"]), c["days_left"]))
    json.dump(kept, open(output_path, "w", encoding="utf-8"), ensure_ascii=False)
    return kept


if __name__ == "__main__":
    result = main(sys.argv[1], sys.argv[2])
    print(len(result))
