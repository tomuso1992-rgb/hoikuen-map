#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild the dataset from the Kohoku-ku CSV.

Two columns in the CSV cannot be trusted as-is:

  保育・教育方針 — every row is either blank or the scraped string
    "N /M 園内の様子" (gallery pagination), never an actual policy. Dropped
    wholesale; the real prose kept for the original 44 is carried over.

  定員数 — for 21 rows it equals 0歳児の利用定員数, i.e. the total was never
    captured and the 0-year-old figure leaked into the column. Believing it
    would label 60-child nurseries as 小規模保育園, so those are set to
    unknown instead.
"""
import csv, json, os, re, sys, unicodedata
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) < 2:
    sys.exit("usage: python3 import_csv.py <園一覧のCSV>")
SRC = sys.argv[1]
OLD = os.path.join(HERE, "nurseries_geo.json")
CHOME = os.path.join(HERE, "kohoku_chome.json")

C_NAME, C_TEL, C_ADDR = "園名", "電話番号", "住所"
C_URL, C_HOURS, C_PARK = "ホームページURL", "開園時間", "駐車場"
C_CAP, C_STAFF = "定員数", "職員数"
C_CAP0, C_APP0 = "0歳児の利用定員数", "0歳児の申込数"
C_POLICY, C_ENM = "保育・教育方針（60字以内に要約）", "えんさがしサポートURL"

JUNK_POLICY = re.compile(r"^\s*\d+\s*/\s*\d+\s*園内の様子\s*$")
KAN = "〇一二三四五六七八九"

# ---------------------------------------------------------------- town lookup
def kan(n):
    n = int(n)
    if n < 1 or n > 99: return None
    if n < 10: return KAN[n]
    if n < 20: return "十" + (KAN[n % 10] if n % 10 else "")
    return KAN[n // 10] + "十" + (KAN[n % 10] if n % 10 else "")

chome = json.load(open(CHOME, encoding="utf-8"))
COORD = {c["town"]: (c["lat"], c["lng"]) for c in chome}

ALIASES = []           # (alias, town, precision) — longest alias wins
for town in COORD:
    m = re.match(r"^(.*?)([〇一二三四五六七八九十]+)丁目$", town)
    if m:
        base, k = m.group(1), m.group(2)
        num = next((i for i in range(1, 100) if kan(i) == k), None)
        forms = {town, base + k + "丁目"}
        if num:
            forms |= {"%s%d丁目" % (base, num), "%s%d" % (base, num)}
        for f in forms:
            ALIASES.append((f, town, "chome"))
    else:
        ALIASES.append((town, town, "town"))
ALIASES.sort(key=lambda x: -len(x[0]))

def norm_addr(a):
    s = unicodedata.normalize("NFKC", a or "")
    s = s.replace("−", "-").replace("－", "-").replace("―", "-").replace("ー", "-")
    s = re.sub(r"〒?\s*\d{3}-?\d{4}", "", s)
    s = re.sub(r"^\s*神奈川県", "", s.strip())
    s = re.sub(r"^\s*横浜市", "", s.strip())
    while s.strip().startswith("港北区"):          # one row says 港北区港北区
        s = s.strip()[3:]
    return s.strip()

def find_town(addr):
    s = norm_addr(addr)
    if not s: return None, None
    for alias, town, prec in ALIASES:
        if s.startswith(alias):
            return town, prec
    return None, None

# ---------------------------------------------------------------- old records
old = {r["name"]: r for r in json.load(open(OLD, encoding="utf-8"))}

def key(name):
    s = unicodedata.normalize("NFKC", name or "")
    s = re.sub(r"[≪≫《》«»\s　]", "", s)
    s = re.sub(r"^横浜市", "", s)
    s = re.sub(r"本園$", "", s)
    return s

old_by_key = {key(k): v for k, v in old.items()}

# ---------------------------------------------------------------- convert
def num(v):
    v = (v or "").strip()
    if not v: return None
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except ValueError:
        return None

def clean_url(u):
    u = (u or "").strip()
    if not u: return None
    if not u.startswith("http"): u = "https://" + u
    return u

def clean_parking(p):
    s = (p or "").strip()
    if not s: return None, None
    head = "あり" if s.startswith("あり") else "なし" if s.startswith("なし") else None
    detail = s[2:].strip() if head else s
    detail = re.sub(r"令和\d+年度に横浜市が把握した情報を掲載しています。?", "", detail).strip()
    detail = re.sub(r"^※.*$", "", detail).strip()
    return head, (detail or None)

rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8-sig")) if (r.get(C_NAME) or "").strip()]
out, stats = [], Counter()
no_town, cap_dropped, policy_kept = [], [], []

for i, r in enumerate(rows):
    name = r[C_NAME].strip()
    cap0, app0 = num(r[C_CAP0]), num(r[C_APP0])
    cap = num(r[C_CAP])

    # total capacity that merely echoes the 0-year-old figure is not a total
    if cap is not None and cap0 is not None and cap == cap0:
        cap = None
        cap_dropped.append(name)

    prev = old_by_key.get(key(name))
    if cap is None and prev and prev.get("capacity"):
        cap = prev["capacity"]
        stats["capacity recovered from previous data"] += 1

    policy = (r[C_POLICY] or "").strip()
    if not policy or JUNK_POLICY.match(policy):
        policy = None
    if policy is None and prev and prev.get("policy"):
        policy = prev["policy"]
        policy_kept.append(name)

    town, prec = find_town(r[C_ADDR])
    if town is None:
        no_town.append((name, r[C_ADDR]))

    park, park_note = clean_parking(r[C_PARK])

    rec = {
        "id": "hk_%d" % i,
        "name": name,
        "address": (r[C_ADDR] or "").strip(),
        "tel": (r[C_TEL] or "").strip() or None,
        "url": clean_url(r[C_URL]),
        "enmikke": (r[C_ENM] or "").strip() or None,
        "hours": (r[C_HOURS] or "").strip() or None,
        "parking": park,
        "parkingNote": park_note,
        "capacity": cap,
        "staff": num(r[C_STAFF]),
        "cap0": cap0,
        "apply0": app0,
        "policy": policy,
        "town": town,
        "prec": prec,
    }
    if town:
        rec["lat"], rec["lng"] = COORD[town]
    out.append({k: v for k, v in rec.items() if v is not None})

json.dump(out, open(OLD, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- report
print("取り込み: %d 園  (以前は %d 園)" % (len(out), len(old)))
print("総定員を不明にした（0歳児定員と同値）: %d 件" % len(cap_dropped))
print("以前のデータから方針の実文を引き継いだ: %d 件" % len(policy_kept))
for k, v in stats.items(): print("  %s: %d" % (k, v))
print("\n位置を特定できなかった:", no_town or "なし")
prec = Counter(r.get("prec") for r in out)
print("位置の精度: 丁目まで=%d  町のみ=%d  不明=%d" % (prec["chome"], prec["town"], prec[None]))
print("えんさがしURLあり: %d / %d" % (sum(1 for r in out if r.get("enmikke")), len(out)))
print("倍率算出可: %d" % sum(1 for r in out if r.get("cap0") and r.get("apply0") is not None))
print("種別 不明（総定員なし）: %d" % sum(1 for r in out if not r.get("capacity")))
ratios = sorted((r["apply0"] / r["cap0"]) for r in out if r.get("cap0") and r.get("apply0") is not None)
import statistics as st
print("倍率: min %.2f / 中央値 %.2f / max %.2f" % (ratios[0], st.median(ratios), ratios[-1]))
for lo, hi, lab in [(0,3,"3.0倍未満"),(3,6,"3.0〜6.0"),(6,9,"6.0〜9.0"),(9,1e9,"9.0以上")]:
    print("   %-10s %d" % (lab, sum(1 for x in ratios if lo <= x < hi)))
