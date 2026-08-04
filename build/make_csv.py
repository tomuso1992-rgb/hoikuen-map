#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CSV for Google マイマップ import — Google geocodes the address column itself,
so pins land on the actual buildings instead of a chome representative point."""
import json, csv, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(HERE, "nurseries_geo.json"), encoding="utf-8"))

def band(r):
    if r is None:  return "5 データなし"
    if r < 3:      return "1 3.0倍未満(比較的入りやすい)"
    if r < 6:      return "2 3.0〜6.0倍(平均的)"
    if r < 9:      return "3 6.0〜9.0倍(激戦)"
    return "4 9.0倍以上(超激戦)"

def addr(a):
    a = re.sub(r"^〒\s*\d{3}-?\d{4}\s*", "", a).strip()
    if not a.startswith("神奈川県"):
        a = "神奈川県" + a if a.startswith("横浜市") else "神奈川県横浜市港北区" + a
    return a

def num(v):
    if v is None: return ""
    return str(int(v)) if float(v).is_integer() else str(v)

rows = []
for d in data:
    cap0, ap0 = d.get("cap0"), d.get("apply0")
    r = (ap0 / cap0) if (cap0 and ap0 is not None) else None
    rows.append({
        "園名": d["name"],
        "住所": addr(d["address"]),
        "倍率": ("%.2f" % r) if r is not None else "",
        "倍率帯": band(r),
        "種別": "不明" if d.get("capacity") is None else ("小規模保育園" if d["capacity"] <= 19 else "保育園"),
        "0歳児定員": num(cap0),
        "申込数": num(ap0),
        "総定員": num(d.get("capacity")),
        "職員数": num(d.get("staff")),
        "駐車場": d.get("parking") or "",
        "開園時間": d.get("hours") or "",
        "電話": d.get("tel") or "",
        "保育方針": d.get("policy") or "",
        "えんさがしサポート": d.get("enmikke") or "",
        "公式サイト": d.get("url") or "",
    })

rows.sort(key=lambda x: (x["倍率帯"], float(x["倍率"]) if x["倍率"] else 999))

out = os.path.join(HERE, "hoikuen-mymaps.csv")
with open(out, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

print("wrote", out, "rows:", len(rows))
for x in rows[:3]:
    print(" ", x["倍率帯"], "|", x["園名"], "|", x["住所"])
